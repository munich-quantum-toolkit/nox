# Using the shared sessions

The helpers use uv and the consuming repository's `pyproject.toml`. Keep Nox
decorators, Python versions, default sessions, and environment settings in the
repository's `noxfile.py`. Importing `mqt.nox` does not register sessions or
change global Nox options.

## Available functions

| Function                                                       | Purpose                                                                          |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `lint(session)`                                                | Run all prek hooks, forwarding session arguments.                                |
| `python.tests(session)`                                        | Install the project and `test` group, then run pytest.                           |
| `python.minimums(session)`                                     | Run tests with the lowest direct dependency versions.                            |
| `python.docs(session)`                                         | Install the `docs` group and build or serve Sphinx docs.                         |
| `cpp.tests(session, package=...)`                              | Prepare the `build` and `test` groups, build without isolation, then run pytest. |
| `cpp.minimums(session, package=...)`                           | Run the CMake test setup with the lowest direct dependency versions.             |
| `cpp.docs(session, package=...)`                               | Prepare the native package and `docs` group, then run Sphinx.                    |
| `cpp.stubs(session, package=..., modules=..., output_dir=...)` | Build a nanobind package, generate stubs, and format them.                       |
| `python.install(session, groups=...)`                          | Prepare a Python environment for a custom session.                               |
| `cpp.install(session, package=..., groups=...)`                | Prepare a CMake environment for a custom session.                                |
| `sphinx(session)`                                              | Build or serve docs in an already prepared environment.                          |
| `format_stubs(session, files)`                                 | Apply the MQT stub hooks to explicitly selected files.                           |

`package` is the distribution name, such as `mqt-qmap`. Stub `modules` are
Python import names, such as `mqt.qmap.sc`. Paths are relative to the consuming
repository, not to the helper package.

The `test` group must include pytest and pytest-cov. The `docs` group must
include Sphinx and the project's documentation dependencies. CMake projects must
declare their Python build dependencies in `build`; missing CMake and Ninja
executables are installed into the session. The CMake helpers are not intended
for Maturin projects such as NAViz.

The helpers require a Nox virtual environment. Use the uv backend and
`reuse_venv=True`, as in the README. Environment values set on `session.env`
apply to the build, tests, and documentation commands.

Ordinary installation uses `uv sync --locked`. Generate or update `uv.lock` with
`uv lock` before running sessions. A stale lock fails without changing the file.
CMake builds use a `build` directory inside each session's virtual environment,
overriding the project's scikit-build-core build directory.

## Customize a session

Pass pytest arguments separately from uv installation arguments:

```python
@nox.session(python="3.14", reuse_venv=True)
def evaluation(session: nox.Session) -> None:
    """Run the photonic evaluation tests."""
    cpp.tests(
        session,
        package="mqt-qmap",
        install_args=("--group", "evaluation"),
        pytest_args=("eval/ph/tests",),
    )
```

Session arguments after `--` are forwarded to pytest. Repository-specific setup,
such as QECC's Numba coverage setting or QCEC's profile checks, stays before the
helper call:

```python
if "--cov" in session.posargs:
    session.env["NUMBA_DISABLE_JIT"] = "1"
python.tests(session)
```

Use `extra_deps` to test an upstream dependency after synchronizing the locked
baseline. For example, keep Qiskit's session in the consuming repository:

```python
@nox.session(python="3.14", reuse_venv=True, venv_backend="uv")
def qiskit(session: nox.Session) -> None:
    """Test against Qiskit's main branch."""
    python.tests(
        session,
        install_args=("--locked",),
        extra_deps=("qiskit[qasm3-import] @ git+https://github.com/Qiskit/qiskit.git",),
        # MQT Core warns when Qiskit is newer than its latest tested release.
        pytest_args=("-Wdefault:Qiskit:mqt.core.UntestedVersionWarning",),
    )
```

This example follows MQT Bench. Native projects use `cpp.tests` and pass their
distribution name, such as `package="mqt-ddsim"`. Add the warning filter only
where MQT Core exposes `UntestedVersionWarning` and emits the Qiskit advisory;
older versions such as MQT Core 3.11 do not define it. The filter applies only
to this session and warning; other warnings retain their configured treatment.

Overrides are installed into the Nox environment after project synchronization,
including with `--no-install`. The helper prints `uv pip freeze`, including Git
commit IDs, then runs pytest directly in that environment. There is no later
synchronization or overlay environment. The lockfile remains unchanged, and a
later ordinary test run synchronizes the declared dependencies again.

When adopting the session, run it on the supported platforms, especially Windows
for native packages. Check Qiskit's `direct_url.json` through
`importlib.metadata.distribution("qiskit")` inside the pytest process to confirm
the Git source and commit ID. Keep that check specific to the upstream session;
ordinary package tests intentionally use released Qiskit. Also repeat the
session with `--no-install` to verify environment reuse.

The minimums helpers use `uv pip install --upgrade --resolution=lowest-direct`,
run pytest with `-Wdefault`, and print the installed dependency tree. They never
read, move, or rewrite `uv.lock`. `--upgrade` also replaces higher versions left
in a reused environment. Their `install_args` go to `uv pip install`, whereas
ordinary test and documentation sessions pass them to `uv sync`.

For documentation, `uvx nox --non-interactive -s docs` builds HTML and
`uvx nox -s docs -- -b linkcheck` checks links. Interactive HTML builds use
sphinx-autobuild. Pass additional fixed Sphinx flags through `sphinx_args`. Use
`install_args=("--frozen",)` if a session intentionally needs frozen
synchronization.

Custom Doxygen or MLIR generation remains ordinary local code. Such sessions can
call `cpp.install`, perform their own generation, and then call `sphinx`. SCPD
can retain its schema-owned stub selection and call `format_stubs` with only the
files it owns.

## Run sessions in parallel

Nox 2026.10.20 or later supports parallel sessions. Keep the opt-in in the
consuming Nox file:

```python
@nox.session(python=["3.13", "3.14"], reuse_venv=True, allow_parallel=True)
def tests(session: nox.Session) -> None:
    python.tests(session)


@nox.session(python=["3.13", "3.14"], reuse_venv=True, allow_parallel=True)
def minimums(session: nox.Session) -> None:
    python.minimums(session)
```

```console
uvx nox -j auto -s tests minimums -- --cov --cov-report=xml:coverage.xml
```

The CMake helpers support the same pattern. Under Nox's parallel scheduler:

- Coverage data and pytest caches go into each session's environment.
- CMake builds default to one build job per session. An explicit
  `CMAKE_BUILD_PARALLEL_LEVEL` in the environment or `session.env` takes
  precedence.
- File coverage reports passed through `pytest_args` or session arguments get
  the environment name appended, such as `coverage-tests-3-14.xml`. Both
  `--cov-report=xml:coverage.xml` and `--cov-report xml:coverage.xml` work, as
  do default paths such as `--cov-report=xml`. Use these arguments for file
  reports; report options hidden in pytest's `addopts` cannot be rewritten by
  the helper.
- pytest-xdist's `-n auto` and `-n logical` use no additional workers. An
  explicit worker count still takes precedence. Sequential Nox runs retain
  normal xdist behavior, and projects without xdist need no additional
  dependency.

Which sessions collect coverage is repository policy. Keep decisions based on
GitHub events or the Python matrix in the local wrapper or workflow; the shared
helpers do not disable requested coverage.

Leave lint, documentation, and stub-generation sessions without
`allow_parallel=True`: they modify source files or shared output directories.
Nox runs these sessions alone even when `-j` is enabled. Custom tests must also
use temporary or session-specific paths for files they create in the checkout.
Do not use Nox's global `--allow-parallel` switch to bypass these boundaries.

## Try the package before publication

Build a wheel from this checkout:

```console
uv build --wheel
```

In a consuming Nox file, replace the example `mqt-nox==0.1.0` requirement with a
direct reference to that wheel, using its absolute path:

```python
# /// script
# dependencies = [
#   "nox>=2026.10.20",
#   "mqt-nox @ file:///absolute/path/to/mqt_nox-0.1.0-py3-none-any.whl",
# ]
# ///
```

`uvx nox -s tests` then loads the local package through Nox's built-in
[inline dependency support](https://nox.thea.codes/en/stable/tutorial.html#running-without-the-nox-command-or-adding-dependencies).
Replace the local reference with a pinned published version when adopting the
package.

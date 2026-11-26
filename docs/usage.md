# Using the shared sessions

The helpers use uv and the consuming repository's `pyproject.toml`. Keep Nox
decorators, Python versions, default sessions, and environment settings in the
repository's `noxfile.py`. Importing `mqt.nox` does not register sessions or
change global Nox options.

## Getting Started

Declare `mqt-nox` alongside `nox` in the inline dependencies of `noxfile.py`,
then call a shared function from a regular Nox session. For a CMake-based Python
package:

```python
# /// script
# dependencies = ["nox>=2026.10.20", "mqt-nox==0.1.0"]
# ///

import nox
from mqt.nox import cpp

nox.options.default_venv_backend = "uv"


@nox.session(python=["3.11", "3.12", "3.13", "3.14"], reuse_venv=True)
def tests(session: nox.Session) -> None:
    """Run the test suite."""
    cpp.tests(session)


if __name__ == "__main__":
    nox.main()
```

For a Python-only project, use `from mqt.nox import python` and
`python.tests(session)`. Run sessions with the usual command:

```console
uvx nox -s tests
```

Nox installs missing inline dependencies before loading the sessions. The
example uses the planned initial version; this package has not been published
yet. See [local installation](#try-the-package-before-publication) to try the
package before publication.

The project's development dependencies only need `mqt-nox`; it already depends
on Nox. Nox also fails on missing interpreters by default when the `CI`
environment variable is set, so no additional configuration is needed.

## Available functions

| Function                              | Purpose                                                                          |
| ------------------------------------- | -------------------------------------------------------------------------------- |
| `common.lint(session)`                | Run all prek hooks, forwarding session arguments.                                |
| `python.tests(session)`               | Install the project and `test` group, then run pytest.                           |
| `python.qiskit(session)`              | Run tests against Qiskit's main branch.                                          |
| `python.minimums(session)`            | Run tests with the lowest direct dependency versions.                            |
| `python.docs(session)`                | Install the `docs` group and build or serve Sphinx docs.                         |
| `cpp.tests(session)`                  | Prepare the `build` and `test` groups, build without isolation, then run pytest. |
| `cpp.qiskit(session)`                 | Build the native package and test against Qiskit's main branch.                  |
| `cpp.minimums(session)`               | Run the CMake test setup with the lowest direct dependency versions.             |
| `cpp.docs(session)`                   | Prepare the native package and `docs` group, then run Sphinx.                    |
| `cpp.stubs(session, modules=...)`     | Build a nanobind package, generate stubs, and format them.                       |
| `python.install(session, groups=...)` | Prepare a Python environment for a custom session.                               |
| `cpp.install(session, groups=...)`    | Prepare a CMake environment for a custom session.                                |
| `common.run_sphinx(session)`          | Build or serve docs in an already prepared environment.                          |
| `common.format_stubs(session, files)` | Apply the MQT stub hooks to explicitly selected files.                           |

Import the public modules with `from mqt.nox import common, cpp, python`. Custom
sessions can call `common.run_pytest` after preparing their environment and use
`common.get_session_env` to direct uv to the Nox environment.

The CMake helpers read the distribution name from `project.name` in the
consuming repository's `pyproject.toml`. Keep that file alongside `noxfile.py`
and call the helpers from that directory. Pass `package` to override the name.

Stub generation follows MQT conventions: `mqt-qmap` maps to the output directory
`python/mqt/qmap`. Provide fully qualified Python module names:

```python
@nox.session(reuse_venv=True)
def stubs(session: nox.Session) -> None:
    """Generate type stubs for Python bindings."""
    cpp.stubs(
        session,
        modules=["mqt.qmap.na", "mqt.qmap.clifford_synthesis", "mqt.qmap.hybrid_mapper", "mqt.qmap.sc"],
    )
```

Keep the module list explicit because importing the root package does not
necessarily load its native modules. Pass `output_dir` to override the stub
directory. Paths are relative to the consuming repository.

The `test` group must include pytest and pytest-cov. The `docs` group must
include Sphinx and the project's documentation dependencies. CMake projects must
declare their Python build dependencies in `build`; missing CMake and Ninja
executables are installed into the session. The CMake helpers are not intended
for Maturin projects.

The helpers require a Nox virtual environment. Use the uv backend and
`reuse_venv=True`, as in the example above. Environment values set on
`session.env` apply to the build, tests, and documentation commands.

Ordinary installation uses `uv sync --locked`. Generate or update `uv.lock` with
`uv lock` before running sessions. A stale lock fails without changing the file.
CMake builds use a `build` directory inside each session's virtual environment,
overriding the project's scikit-build-core build directory.

## Customize a session

Sequence arguments accept lists or tuples. Use `pytest_args` for pytest
command-line arguments, including test paths. For a session with additional
dependency groups, prepare the environment before running pytest:

```python
from mqt.nox import common


@nox.session(python="3.14", reuse_venv=True)
def evaluation(session: nox.Session) -> None:
    """Run the photonic evaluation tests."""
    cpp.install(session, groups=["test", "evaluation"])
    common.run_pytest(session, pytest_args=["eval/ph/tests"])
```

Session arguments after `--` are forwarded to pytest. Repository-specific setup,
such as environment settings for coverage, stays before the helper call:

```python
if "--cov" in session.posargs:
    session.env["NUMBA_DISABLE_JIT"] = "1"
python.tests(session)
```

Use `python.qiskit` or `cpp.qiskit` to test Qiskit's main branch after
synchronizing the locked baseline. Keep the session definition in the consuming
repository:

```python
@nox.session(python="3.14", reuse_venv=True, venv_backend="uv")
def qiskit(session: nox.Session) -> None:
    """Test against Qiskit's main branch."""
    python.qiskit(
        session,
        # MQT Core warns when Qiskit is newer than its latest tested release.
        pytest_args=["-Wdefault:Qiskit:mqt.core.UntestedVersionWarning"],
    )
```

Native projects use `cpp.qiskit`. Add the warning filter only where MQT Core
exposes `UntestedVersionWarning` and emits the Qiskit advisory. The filter
applies only to this session and warning; other warnings retain their configured
treatment.

Both helpers install `qiskit[qasm3-import]` from Git. To override other
dependencies, pass `extra_deps` to `python.tests` or `cpp.tests`.

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
`install_args=["--frozen"]` if a session intentionally needs frozen
synchronization.

Custom documentation generation remains ordinary local code. Such sessions can
call `cpp.install`, perform their own generation, and then call
`common.run_sphinx`. Custom stub generation can use `common.format_stubs` to
format the generated files.

## Run sessions in parallel

Parallel execution is a repository choice. Nox runs sessions sequentially by
default. To opt in, mark suitable sessions in the consuming Nox file:

```python
@nox.session(python=["3.13", "3.14"], reuse_venv=True, allow_parallel=True)
def tests(session: nox.Session) -> None:
    python.tests(session)


@nox.session(python=["3.13", "3.14"], reuse_venv=True, allow_parallel=True)
def minimums(session: nox.Session) -> None:
    python.minimums(session)
```

```console
uvx nox --parallel auto -s tests minimums -- --cov --cov-report=xml:coverage.xml
```

The CMake helpers support the same pattern. Under Nox's parallel scheduler:

- Coverage data and pytest caches go into each session's environment.
- XML coverage reports use a separate filename per environment. Pass
  `--cov-report=xml:coverage.xml`, as in the shared CI workflow, to produce
  files such as `coverage-tests-3-14.xml`. For other report formats or argument
  forms, supply distinct output paths in the consuming session.

The helpers leave pytest-xdist worker counts and CMake build parallelism
unchanged. Configure these in the consuming repository or environment. Combining
concurrent Nox sessions with automatic pytest or build worker counts can
multiply CPU and memory use. A repository can set `nox.options.parallel` to
choose its default session concurrency.

Which sessions collect coverage is repository policy. Keep decisions based on
GitHub events or the Python matrix in the local wrapper or workflow; the shared
helpers do not disable requested coverage.

Leave lint, documentation, and stub-generation sessions without
`allow_parallel=True`: they modify source files or shared output directories.
Nox runs these sessions alone even when `--parallel` is enabled. Custom tests
must also use temporary or session-specific paths for files they create in the
checkout. Do not use Nox's global `--allow-parallel` switch to bypass these
boundaries.

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

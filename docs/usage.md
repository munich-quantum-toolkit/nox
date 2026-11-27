# Using the shared sessions

Keep session names, Python versions, and repository-specific setup in your
`noxfile.py`. The shared functions handle installation and common tasks.

## Getting started

Declare the dependencies in `noxfile.py` and call a helper from a regular Nox
session:

```python
# /// script
# dependencies = ["nox>=2026.10.20", "mqt-nox==0.1.0"]
# ///

import nox
from mqt.nox import cpp

nox.options.default_venv_backend = "uv"


@nox.session(python="3.14", reuse_venv=True)
def tests(session: nox.Session) -> None:
    """Run the test suite."""
    cpp.tests(session)
```

Until the first release, replace `mqt-nox==0.1.0` with a pinned Git or local
wheel reference. Add the same dependency to your project's development group.
For Python-only projects, import `python` and call `python.tests(session)`. Run
sessions as usual:

```console
uvx nox -s tests
uvx nox -s tests -- -k some_test
```

Keep `pyproject.toml` alongside `noxfile.py` and update `uv.lock` when
dependencies change. Define a `test` dependency group containing pytest and
pytest-cov, a `docs` group containing Sphinx, sphinx-autobuild, and
documentation dependencies, and a `build` group for CMake projects. The CMake
helpers read the package name from `project.name`.

## Available helpers

| Task                 | Python-only project                     | CMake project                        |
| -------------------- | --------------------------------------- | ------------------------------------ |
| Tests                | `python.tests(session)`                 | `cpp.tests(session)`                 |
| Minimum dependencies | `python.minimums(session)`              | `cpp.minimums(session)`              |
| Upstream Qiskit      | `python.qiskit(session)`                | `cpp.qiskit(session)`                |
| Documentation        | `python.docs(session)`                  | `cpp.docs(session)`                  |
| Custom installation  | `python.install(session, groups=[...])` | `cpp.install(session, groups=[...])` |

Use `common.lint(session)` for linting and `cpp.stubs(session, modules=[...])`
for nanobind stubs. Pass full module names such as `mqt.qmap.sc`; the default
output directory follows the MQT layout, e.g. `python/mqt/qmap`. Override it
with `output_dir` if needed.

Installation uses `uv sync --locked`, which fails if `uv.lock` is out of date
instead of updating it. The minimum-dependency helpers resolve independently of
`uv.lock`. The Qiskit helpers install the upstream version after project
synchronization so pytest uses that version. Documentation sessions use the
locked dependencies for both builds and interactive HTML previews. Pass
`--non-interactive` to build only, or `-- -b linkcheck` to check links.

## Customizing a session

Use `pytest_args` for fixed pytest flags or test paths, `install_args` for uv
options such as `--all-extras` or `--reinstall-package`, and `sphinx_args` for
Sphinx options. Arguments after `--` are forwarded to the session's command.
Test helpers also accept `extra_deps` for dependency overrides installed after
synchronization.

For additional dependency groups or custom setup, install first and then call a
common helper:

```python
from mqt.nox import common


@nox.session(python="3.14", reuse_venv=True)
def evaluation(session: nox.Session) -> None:
    """Run the evaluation tests."""
    cpp.install(session, groups=["test", "evaluation"])
    common.run_pytest(session, pytest_args=["eval/ph/tests"])
```

Repository-specific build steps and warning filters stay in the local session.
Use `session.env` for environment settings. Maturin and other specialized build
setups should keep their own installation code.

Run Nox sessions sequentially. Configure pytest-xdist and CMake worker counts in
the consuming repository.

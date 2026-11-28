# Using the shared sessions

Keep session names, Python versions, and repository-specific setup in your
`noxfile.py`. The shared functions handle installation and common tasks.
Importing `mqt.nox` sets uv as the default Nox environment backend. The
installation helpers use this backend to select the session environment.

## Getting started

Declare the dependencies in `noxfile.py` and call a helper from a regular Nox
session:

```python
# /// script
# dependencies = ["nox>=2026.10.20", "mqt-nox~=0.1.0"]
# ///

import nox
from mqt.nox import python


@nox.session(python="3.14", reuse_venv=True)
def tests(session: nox.Session) -> None:
    """Run the test suite."""
    python.tests(session)
```

Add `mqt-nox~=0.1.0` to your project's development group as well. Run sessions
as usual:

```console
uvx nox -s tests
uvx nox -s tests -- -k some_test
```

Keep `pyproject.toml` alongside `noxfile.py` and update `uv.lock` when
dependencies change. Define a `test` dependency group containing `pytest` and
`pytest-cov` and a `docs` group containing Sphinx and documentation
dependencies.

Build isolation is enabled by default, which suits Python-only projects. For
Python-C++ projects that build against dependencies in the session environment,
pass `build_isolation=False`, e.g.,
`python.tests(session, build_isolation=False)`. This adds the `build` group and
disables isolation for the project package, whose name is read from
`project.name`. Define that group with the project's Python build dependencies.
With isolation disabled, the helpers also check for CMake and Ninja on `PATH`
and install either tool in the session if it is missing.

If you use repo-review, ignore `NOX102` in `[tool.repo-review.ignore]`. That
check looks for a backend assignment in `noxfile.py`, while `mqt.nox` sets it on
import.

## Available helpers

| Helper                     | Description                            |
| -------------------------- | -------------------------------------- |
| `python.lint(session)`     | Run all prek hooks                     |
| `python.tests(session)`    | Run tests                              |
| `python.minimums(session)` | Run tests with minimum dependencies    |
| `python.qiskit(session)`   | Run tests against Qiskit's main branch |
| `python.docs(session)`     | Build or serve documentation           |

The test and documentation helpers accept `build_isolation`.

Installation uses a single `uv sync --locked`, which fails if `uv.lock` is out
of date instead of updating it. With build isolation disabled, uv installs the
build dependencies before building the project in the same environment. The
minimum-dependency helper resolves independently of `uv.lock` and installs the
build and test groups first when isolation is disabled. The Qiskit helper
installs the upstream version after project synchronization so `pytest` uses
that version.

Documentation sessions install the locked docs dependencies and additionally
install sphinx-autobuild for interactive HTML previews. The preview tool is not
part of the project lockfile. Pass `--non-interactive` to build only, or
`-- -b linkcheck` to check links.

Use `python.stubs(session, modules=[...])` to generate nanobind stubs. Stub
generation installs the `build` group, which must include nanobind, and builds
without isolation. Pass full module names such as `mqt.qmap.sc`. The default
output directory follows the MQT layout, e.g., `python/mqt/qmap`. Override it
with `output_dir` if needed.

## Customizing a session

Use `pytest_args` for fixed `pytest` flags or test paths, `install_args` for uv
options such as `--all-extras` or `--reinstall-package`, and `sphinx_args` for
Sphinx options. Arguments after `--` are forwarded to the session's command.
`python.tests` also accepts `extra_deps` for dependency overrides installed
after synchronization.

Use `utils` to compose custom sessions with additional dependency groups:

```python
from mqt.nox import utils


@nox.session(python="3.14", reuse_venv=True)
def evaluation(session: nox.Session) -> None:
    """Run the evaluation tests."""
    utils.install(session, build_isolation=False, groups=["test", "evaluation"])
    utils.run_pytest(session, pytest_args=["eval/ph/tests"])
```

Repository-specific build steps and warning filters stay in the local session.
Use `session.env` for environment settings. Maturin and other specialized build
setups should keep their own installation code.

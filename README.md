[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)

<p align="center">
  <a href="https://mqt.readthedocs.io">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/munich-quantum-toolkit/.github/refs/heads/main/docs/_static/logo-mqt-dark.svg" width="60%">
      <img src="https://raw.githubusercontent.com/munich-quantum-toolkit/.github/refs/heads/main/docs/_static/logo-mqt-light.svg" width="60%" alt="MQT Logo">
    </picture>
  </a>
</p>

# Nox Sessions for the Munich Quantum Toolkit (MQT)

This repository contains a collection of common Nox session functions for the
repositories of the
[_Munich Quantum Toolkit (MQT)_](https://mqt.readthedocs.io). The functions
handle recurring test, documentation, lint, and stub-generation tasks. Each
repository defines its own sessions and can customize them with ordinary Python
code.

## Contributors and Supporters

The _[Munich Quantum Toolkit (MQT)](https://mqt.readthedocs.io)_ is developed by
the [Chair for Design Automation](https://www.cda.cit.tum.de/) at the
[Technical University of Munich](https://www.tum.de/) and supported by
[MQSC](https://mq.sc). Among others, it is part of the
[Munich Quantum Software Stack (MQSS)](https://www.munich-quantum-valley.de/research/research-areas/mqss)
ecosystem, which is being developed as part of the
[Munich Quantum Valley (MQV)](https://www.munich-quantum-valley.de) initiative.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/munich-quantum-toolkit/.github/refs/heads/main/docs/_static/mqt-logo-banner-dark.svg" width="90%">
    <img src="https://raw.githubusercontent.com/munich-quantum-toolkit/.github/refs/heads/main/docs/_static/mqt-logo-banner-light.svg" width="90%" alt="MQT Partner Logos">
  </picture>
</p>

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


@nox.session(python=["3.11", "3.12", "3.13", "3.14"], reuse_venv=True, allow_parallel=True)
def tests(session: nox.Session) -> None:
    """Run the test suite."""
    cpp.tests(session, package="mqt-qmap")


if __name__ == "__main__":
    nox.main()
```

For a Python-only project, use `from mqt.nox import python` and
`python.tests(session)`. Run sessions with the usual command:

```console
uvx nox -s tests
```

Use `uvx nox -j auto -s tests` to run the Python matrix in parallel. Test and
minimum-version sessions keep their environments, native builds, and coverage
outputs separate. See the
[parallel usage notes](docs/usage.md#run-sessions-in-parallel) before enabling
parallel execution for custom sessions.

Nox installs missing inline dependencies before loading the sessions. The
example uses the planned initial version; this package has not been published
yet. See the [usage guide](docs/usage.md) for local installation, available
functions, and customization examples.

> [!WARNING]
> When rolling this out, enable Renovate's
> [PEP 723 manager](https://docs.renovatebot.com/modules/manager/pep723/) for
> `noxfile.py` so it updates the pinned inline dependencies. The manager does
> not match any files by default. Add
> `"pep723": { "managerFilePatterns": ["/(^|/)noxfile\\.py$/"] }` to the
> Renovate configuration. If `enabledManagers` is restricted, include `"pep723"`
> there as well.

## Development

```console
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```

The integration tests run real Nox sessions with temporary Python and CMake
projects. They require uv, a C++ compiler, CMake, and Ninja. The first run
downloads the test projects' Python dependencies.

---

## Acknowledgements

The Munich Quantum Toolkit has been supported by the European Research Council
(ERC) under the European Union's Horizon 2020 research and innovation program
(grant agreement No. 101001318), the Bavarian State Ministry for Science and
Arts through the Distinguished Professorship Program, as well as the Munich
Quantum Valley, which is supported by the Bavarian state government with funds
from the Hightech Agenda Bayern Plus.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/munich-quantum-toolkit/.github/refs/heads/main/docs/_static/mqt-funding-footer-dark.svg" width="90%">
    <img src="https://raw.githubusercontent.com/munich-quantum-toolkit/.github/refs/heads/main/docs/_static/mqt-funding-footer-light.svg" width="90%" alt="MQT Funding Footer">
  </picture>
</p>

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg?style=flat-square)](LICENSE)

# Reusable Nox Sessions for Python and C++-Python Projects

`mqt-nox` provides reusable Nox session functions for Python-only projects and
C++-Python projects built with CMake. The functions handle recurring test,
documentation, lint, and stub-generation tasks. Each repository defines its own
sessions and can customize them with ordinary Python code.

## Contributors

This project is created and maintained by [MQSC](https://mq.sc), with
contributions from the community.

<p align="center">
  <a href="https://github.com/munich-quantum-toolkit/nox/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=munich-quantum-toolkit/nox" alt="Contributors to munich-quantum-toolkit/nox" />
  </a>
</p>

## Use Across Projects

These sessions are designed for use across the
[Munich Quantum Toolkit (MQT)](https://mqt.readthedocs.io), projects maintained
by [MQSC](https://mq.sc), and the
[Quantum Device Management Interface (QDMI)](https://github.com/Munich-Quantum-Software-Stack/QDMI)
ecosystem. Other Python and C++-Python projects can use them by following the
conventions in the usage guide.

## Getting Started

See the [usage guide](docs/usage.md) for installation, available functions, and
examples for Python-only and C++-Python projects.

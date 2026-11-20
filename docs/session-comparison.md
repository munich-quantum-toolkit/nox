# Shared session behavior

The initial collection was compared against the upstream `main` Nox files of
Bench, MQT Core, DDSIM, Debugger, IONShuttler, Predictor, ProblemSolver, QCEC,
QECC, QMAP, Qudits, QUSAT, SCPD, SQR, SyReC, YAQS, NAViz, and DDVis on November
14, 2026. Existing repositories have not been migrated.

## Common behavior

All 18 repositories have the same lint implementation. Sixteen have the same
lockfile-preservation implementation. Bench, IONShuttler, Predictor,
ProblemSolver, and SQR also have identical test helpers. The remaining test
helpers mostly add native build setup, environment settings, or dependency
overrides.

The collection makes the following choices explicit:

| Existing variation                                                        | Shared behavior                                                                                 |
| ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| One `uv run` versus separate setup and execution                          | Finish synchronization first, then run pytest or Sphinx directly.                               |
| Upstream packages installed before or after synchronization               | Install `extra_deps` last, targeting the session interpreter explicitly, as DDSIM already does. |
| `run_args` versus `pytest_run_args`                                       | Use `pytest_args`; reserve `install_args` for uv sync.                                          |
| Hard-coded package names                                                  | Require the distribution name in CMake helpers.                                                 |
| Frozen documentation in some Python projects                              | Use ordinary uv synchronization by default; existing frozen behavior can be passed explicitly.  |
| Moving or refreshing `uv.lock` for minimums                               | Resolve with `uv pip install`; leave the lockfile alone, including during concurrent sessions.  |
| Isolated builds for most stub sessions versus prepared builds in MQT Core | Reuse the same explicit CMake build preparation for tests, docs, and stubs.                     |
| `str(Path(...))` versus passing a Path                                    | Pass paths directly to Nox.                                                                     |

Parallel execution follows the approach in
[MQT Bench #986](https://github.com/munich-quantum-toolkit/bench/pull/986): keep
minimum-version resolution independent of the project lock, isolate coverage,
and avoid nested automatic pytest worker pools. Native builds also use a
separate directory per Nox environment. Ordinary installation uses `--locked` so
all sessions can read the same unchanged lockfile. Coverage selection based on
GitHub events stays in the consuming repository.

The shared functions do not enable all extras implicitly. Dependencies needed
for ordinary tests or docs belong in their corresponding dependency groups.
Session-specific extras and groups can be passed through `install_args`.

## Behavior that stays local

| Repository or session                                                           | Reason                                                                          |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| NAViz's native setup and stubs                                                  | Uses Maturin/PyO3, not the CMake/nanobind workflow.                             |
| MQT Core's documentation and C++ linting                                        | Owns MLIR generation, QDMI isolation, README execution, and toolchain settings. |
| DDSIM, Debugger, and SCPD Doxygen steps                                         | These need explicit documentation preparation beyond Sphinx.                    |
| SCPD schemas and generated stub selection                                       | Schema tools own a separate set of generated files.                             |
| YAQS release, JIT, and executable documentation sessions                        | Test selection, numerical settings, and artifact checks belong to YAQS.         |
| QECC and YAQS Numba coverage handling                                           | Applies to their execution model, not every Python project.                     |
| QCEC profile checks                                                             | Depend on the repository's platform and interpreter policy.                     |
| QMAP evaluation, Predictor training, Catalyst and Qiskit compatibility matrices | Their session definitions and dependency choices remain repository-owned.       |

The Python-version matrix, default sessions, CI interpreter checks, and global
environment policy also remain in each repository. These are not inferred from
the presence of a CMake file or a particular build backend.

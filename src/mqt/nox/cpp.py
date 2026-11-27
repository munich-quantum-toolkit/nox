# Copyright (c) 2026 Chair for Design Automation, TUM
# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: MIT
#
# Licensed under the MIT License

"""Sessions for CMake-based Python packages with a build dependency group."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import nox
from mqt.nox import common

if TYPE_CHECKING:
    from collections.abc import Sequence


def prepare_build_env(session: nox.Session) -> dict[str, str]:
    """Ensure CMake and Ninja are available.

    Returns:
        Environment variables for uv and the native build.
    """
    if shutil.which("cmake") is None:
        session.install("cmake")
    if shutil.which("ninja") is None:
        session.install("ninja")
    return common.get_session_env(session)


def install(
    session: nox.Session,
    *,
    package: str | None = None,
    groups: Sequence[str] = (),
    install_args: Sequence[str] = (),
) -> None:
    """Prepare locked build dependencies, then install the package without isolation.

    ``package`` defaults to ``project.name`` in the consuming pyproject.toml.
    The project must declare its Python build dependencies in the ``build``
    group. Additional ``install_args`` are passed to both uv sync calls.
    """
    package = package or nox.project.load_toml()["project"]["name"]
    env = prepare_build_env(session)
    session.run(
        "uv",
        "sync",
        "--locked",
        "--inexact",
        "--only-group",
        "build",
        *(arg for group in groups for arg in ["--only-group", group]),
        *install_args,
        env=env,
    )
    session.run(
        "uv",
        "sync",
        "--locked",
        "--inexact",
        "--no-dev",
        "--no-build-isolation-package",
        package,
        *install_args,
        env=env,
    )


def tests(
    session: nox.Session,
    *,
    package: str | None = None,
    install_args: Sequence[str] = (),
    pytest_args: Sequence[str] = (),
    extra_deps: Sequence[str] = (),
) -> None:
    """Build the package and run pytest with optional dependency overrides.

    ``install_args`` go to uv sync; ``pytest_args`` precede session.posargs.
    ``extra_deps`` are installed after synchronization, e.g. an upstream SDK.
    The test group must include pytest-cov for the shared coverage configuration.
    """
    install(session, package=package, groups=["test"], install_args=install_args)
    common.run_pytest(session, pytest_args=pytest_args, extra_deps=extra_deps)


def qiskit(
    session: nox.Session,
    *,
    package: str | None = None,
    install_args: Sequence[str] = (),
    pytest_args: Sequence[str] = (),
) -> None:
    """Build the package and test against Qiskit's main branch."""
    tests(
        session,
        package=package,
        install_args=install_args,
        pytest_args=pytest_args,
        extra_deps=["qiskit[qasm3-import] @ git+https://github.com/Qiskit/qiskit.git"],
    )


def minimums(
    session: nox.Session,
    *,
    package: str | None = None,
    install_args: Sequence[str] = (),
    pytest_args: Sequence[str] = (),
) -> None:
    """Test lowest direct dependencies without reading or changing uv.lock.

    ``install_args`` are passed to uv pip install.
    """
    package = package or nox.project.load_toml()["project"]["name"]
    env = prepare_build_env(session)
    install_command = [
        "uv",
        "pip",
        "install",
        "--python",
        session.virtualenv.location,
        "--upgrade",
        "--resolution=lowest-direct",
        "--group",
        "build",
        "--group",
        "test",
    ]
    session.run(*install_command, *install_args, env=env)
    session.run(
        *install_command,
        "--no-build-isolation-package",
        package,
        "--editable",
        ".",
        *install_args,
        env=env,
    )
    common.run_pytest(session, pytest_args=["-Wdefault", *pytest_args])
    session.run("uv", "pip", "tree", "--python", session.virtualenv.location)


def docs(
    session: nox.Session,
    *,
    package: str | None = None,
    install_args: Sequence[str] = (),
    sphinx_args: Sequence[str] = (),
) -> None:
    """Build the package and run Sphinx; any Doxygen setup remains in the caller."""
    install(session, package=package, groups=["docs"], install_args=install_args)
    common.run_sphinx(session, sphinx_args=sphinx_args)


def stubs(
    session: nox.Session,
    *,
    modules: Sequence[str],
    package: str | None = None,
    output_dir: str | Path | None = None,
    stubgen_args: Sequence[str] = (),
) -> None:
    """Build a nanobind package, generate its stubs, and run the MQT stub hooks.

    ``modules`` contains Python import names, e.g. ``mqt.qmap.sc``. MQT
    distribution names such as ``mqt-qmap`` determine the default output
    directory, e.g. ``python/mqt/qmap``. Extra arguments go to nanobind.stubgen.
    """
    if not modules:
        session.error("At least one nanobind module is required")
    package = package or nox.project.load_toml()["project"]["name"]
    module_prefix = package.replace("-", ".")
    install(session, package=package)
    output_dir = Path(output_dir) if output_dir is not None else Path("python", *module_prefix.split("."))
    session.run(
        "python",
        "-m",
        "nanobind.stubgen",
        "--recursive",
        "--include-private",
        "--output-dir",
        output_dir,
        *(arg for module in modules for arg in ["--module", module]),
        *stubgen_args,
        *session.posargs,
    )
    common.format_stubs(session, sorted(output_dir.rglob("*.pyi")))

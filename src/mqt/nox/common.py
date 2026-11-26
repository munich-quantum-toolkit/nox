# Copyright (c) 2026 Chair for Design Automation, TUM
# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: MIT
#
# Licensed under the MIT License

"""Operations shared by the Python and CMake session functions."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    import nox


QISKIT_UPSTREAM = "qiskit[qasm3-import] @ git+https://github.com/Qiskit/qiskit.git"


def lint(session: nox.Session) -> None:
    """Run all prek hooks, forwarding the session arguments."""
    if shutil.which("prek") is None:
        session.install("prek")
    session.run("prek", "run", "--all-files", *session.posargs, external=True)


def get_session_env(session: nox.Session) -> dict[str, str]:
    """Direct uv to the environment selected by Nox.

    Returns:
        Environment variables selecting the Nox virtual environment.
    """
    return {"UV_PROJECT_ENVIRONMENT": session.virtualenv.location}


def run_pytest(session: nox.Session, *, pytest_args: Sequence[str] = (), extra_deps: Sequence[str] = ()) -> None:
    """Apply dependency overrides after synchronization, then run pytest directly.

    ``pytest_args`` contains pytest command-line arguments, including test paths.
    These precede session.posargs.
    """
    if extra_deps:
        # Sync can restore locked versions even when Nox runs with --no-install.
        session.run(
            "uv",
            "pip",
            "install",
            "--python",
            session.virtualenv.location,
            *extra_deps,
            env=get_session_env(session),
        )
        session.run("uv", "pip", "freeze", "--python", session.virtualenv.location, env=get_session_env(session))
    args = [*pytest_args, *session.posargs]
    env = get_session_env(session)
    if session.parallel:
        directory = Path(session.virtualenv.location).resolve()
        env["COVERAGE_FILE"] = str(directory / ".coverage")
        args.extend(["-o", f"cache_dir={directory / 'pytest_cache'}"])
        # The shared CI workflow passes the same XML filename to every session.
        args = [
            f"{arg.removesuffix('.xml')}-{directory.name}.xml"
            if arg.startswith("--cov-report=xml:") and arg.endswith(".xml")
            else arg
            for arg in args
        ]
    session.run("pytest", *args, "--cov-config=pyproject.toml", env=env)


def run_sphinx(session: nox.Session, *, sphinx_args: Sequence[str] = ()) -> None:
    """Build docs from an already prepared environment.

    Accept ``-b <builder>`` in session arguments and forward the remaining
    arguments to Sphinx. Serve HTML builds only in interactive sessions.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", dest="builder", default="html", help="Build target (default: html)")
    args, posargs = parser.parse_known_args(session.posargs)
    serve = args.builder == "html" and session.interactive
    if serve:
        session.install("sphinx-autobuild")
    session.run(
        "sphinx-autobuild" if serve else "sphinx-build",
        "-n",
        "-T",
        f"-b={args.builder}",
        "docs",
        f"docs/_build/{args.builder}",
        *sphinx_args,
        *posargs,
        env=get_session_env(session),
    )


def format_stubs(session: nox.Session, files: Sequence[Path]) -> None:
    """Apply the MQT stub hooks and verify the final Ruff result."""
    if not files:
        session.warn("No .pyi files found")
        return
    if shutil.which("prek") is None:
        session.install("prek")
    for hook in ["license-tools", "ruff-check", "ruff-format"]:
        session.run("prek", "run", hook, "--files", *files, external=True, success_codes=[0, 1])
    session.run("prek", "run", "ruff-check", "--files", *files, external=True)

# Copyright (c) 2023 - 2026 Chair for Design Automation, TUM
# Copyright (c) 2025 - 2026 Munich Quantum Software Company GmbH
# SPDX-License-Identifier: MIT

"""Operations shared by the Python and CMake session functions."""

from __future__ import annotations

import argparse
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import nox


def lint(session: nox.Session) -> None:
    """Run all prek hooks, forwarding the session arguments."""
    if shutil.which("prek") is None:
        session.install("prek")
    session.run("prek", "run", "--all-files", *session.posargs, external=True)


def environment(session: nox.Session) -> dict[str, str]:
    """Direct uv to the environment selected by Nox."""
    return {"UV_PROJECT_ENVIRONMENT": session.virtualenv.location}


def pytest(session: nox.Session, *, pytest_args: Sequence[str], extra_deps: Sequence[str]) -> None:
    """Apply dependency overrides after synchronization, then run pytest directly."""
    if extra_deps:
        # Sync can restore locked versions even when Nox runs with --no-install.
        session.run(
            "uv", "pip", "install", "--python", session.virtualenv.location, *extra_deps, env=environment(session)
        )
        session.run("uv", "pip", "freeze", "--python", session.virtualenv.location, env=environment(session))
    args = [*pytest_args, *session.posargs]
    env = environment(session)
    if session.parallel:
        directory = Path(session.virtualenv.location).resolve()
        env["COVERAGE_FILE"] = str(directory / ".coverage")
        env["PYTEST_XDIST_AUTO_NUM_WORKERS"] = "0"
        args.extend(("-o", f"cache_dir={directory / 'pytest_cache'}"))
        parser = argparse.ArgumentParser(allow_abbrev=False, add_help=False)
        parser.add_argument("--cov-report", action="append", default=[])
        reports, args = parser.parse_known_args(args)
        defaults = {
            "xml": "coverage.xml",
            "json": "coverage.json",
            "lcov": "coverage.lcov",
            "html": "htmlcov",
            "annotate": "cover",
            "markdown": "coverage.md",
            "markdown-append": "coverage.md",
        }
        for report in reports.cov_report:
            kind, _, path = report.partition(":")
            if kind in defaults and path != "-":
                output = Path(path or defaults[kind])
                output = output.with_name(f"{output.stem}-{directory.name}{output.suffix}")
                report = f"{kind}:{output}"
            args.append(f"--cov-report={report}")
    session.run("pytest", *args, "--cov-config=pyproject.toml", env=env)


def sphinx(session: nox.Session, *, sphinx_args: Sequence[str] = ()) -> None:
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
        env=environment(session),
    )


def format_stubs(session: nox.Session, files: Sequence[Path]) -> None:
    """Apply the MQT stub hooks and verify the final Ruff result."""
    if not files:
        session.warn("No .pyi files found")
        return
    if shutil.which("prek") is None:
        session.install("prek")
    for hook in ("license-tools", "ruff-check", "ruff-format"):
        session.run("prek", "run", hook, "--files", *files, external=True, success_codes=[0, 1])
    session.run("prek", "run", "ruff-check", "--files", *files, external=True)

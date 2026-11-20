# Copyright (c) 2023 - 2026 Chair for Design Automation, TUM
# Copyright (c) 2025 - 2026 Munich Quantum Software Company GmbH
# SPDX-License-Identifier: MIT

"""Sessions for Python projects using uv dependency groups."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from . import _common

if TYPE_CHECKING:
    import nox


def install(
    session: nox.Session, *, groups: Sequence[str], install_args: Sequence[str] = (), minimum: bool = False
) -> None:
    """Install locked dependencies, or resolve minimum versions without using the lock."""
    lock_args = () if {"--locked", "--frozen"}.intersection(install_args) else ("--locked",)
    command = (
        (
            "pip",
            "install",
            "--python",
            session.virtualenv.location,
            "--upgrade",
            "--resolution=lowest-direct",
            "--editable",
            ".",
        )
        if minimum
        else ("sync", *lock_args, "--inexact", "--no-dev")
    )
    session.run(
        "uv",
        *command,
        *(arg for group in groups for arg in ("--group", group)),
        *install_args,
        env=_common.environment(session),
    )


def tests(
    session: nox.Session,
    *,
    install_args: Sequence[str] = (),
    pytest_args: Sequence[str] = (),
    extra_deps: Sequence[str] = (),
) -> None:
    """Install the test group and run pytest with optional dependency overrides.

    ``install_args`` go to uv sync; ``pytest_args`` precede session.posargs.
    ``extra_deps`` are installed after synchronization, e.g. an upstream SDK.
    The test group must include pytest-cov for the shared coverage configuration.
    """
    install(session, groups=("test",), install_args=install_args)
    _common.pytest(session, pytest_args=pytest_args, extra_deps=extra_deps)


def minimums(
    session: nox.Session,
    *,
    install_args: Sequence[str] = (),
    pytest_args: Sequence[str] = (),
) -> None:
    """Test lowest direct dependencies without reading or changing uv.lock.

    ``install_args`` are passed to uv pip install.
    """
    install(session, groups=("test",), install_args=install_args, minimum=True)
    _common.pytest(session, pytest_args=("-Wdefault", *pytest_args), extra_deps=())
    session.run("uv", "pip", "tree", "--python", session.virtualenv.location)


def docs(
    session: nox.Session,
    *,
    install_args: Sequence[str] = (),
    sphinx_args: Sequence[str] = (),
) -> None:
    """Install the docs group and build or serve Sphinx documentation."""
    install(session, groups=("docs",), install_args=install_args)
    _common.sphinx(session, sphinx_args=sphinx_args)

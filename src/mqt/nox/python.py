# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Sessions for Python projects using uv dependency groups."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mqt.nox import common

if TYPE_CHECKING:
    from collections.abc import Sequence

    import nox


def install(session: nox.Session, *, groups: Sequence[str], install_args: Sequence[str] = ()) -> None:
    """Install the project and selected groups from the lockfile."""
    session.run(
        "uv",
        "sync",
        "--locked",
        "--inexact",
        "--no-dev",
        *(arg for group in groups for arg in ["--group", group]),
        *install_args,
        env=common.get_session_env(session),
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
    install(session, groups=["test"], install_args=install_args)
    common.run_pytest(session, pytest_args=pytest_args, extra_deps=extra_deps)


def qiskit(
    session: nox.Session,
    *,
    install_args: Sequence[str] = (),
    pytest_args: Sequence[str] = (),
) -> None:
    """Test against Qiskit's main branch after installing the locked baseline."""
    tests(
        session,
        install_args=install_args,
        pytest_args=pytest_args,
        extra_deps=["qiskit[qasm3-import] @ git+https://github.com/Qiskit/qiskit.git"],
    )


def minimums(
    session: nox.Session,
    *,
    install_args: Sequence[str] = (),
    pytest_args: Sequence[str] = (),
) -> None:
    """Test lowest direct dependencies without reading or changing uv.lock.

    ``install_args`` are passed to uv pip install.
    """
    session.run(
        "uv",
        "pip",
        "install",
        "--python",
        session.virtualenv.location,
        "--upgrade",
        "--resolution=lowest-direct",
        "--group",
        "test",
        "--editable",
        ".",
        *install_args,
        env=common.get_session_env(session),
    )
    common.run_pytest(session, pytest_args=["-Wdefault", *pytest_args])
    session.run("uv", "pip", "tree", "--python", session.virtualenv.location)


def docs(
    session: nox.Session,
    *,
    install_args: Sequence[str] = (),
    sphinx_args: Sequence[str] = (),
) -> None:
    """Install the docs group and build or serve Sphinx documentation."""
    install(session, groups=["docs"], install_args=install_args)
    common.run_sphinx(session, sphinx_args=sphinx_args)

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

"""Sessions for Python-only and Python-C++ projects using uv dependency groups."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import nox
from mqt.nox import common

if TYPE_CHECKING:
    from collections.abc import Sequence


def prepare_build_env(session: nox.Session) -> None:
    """Ensure CMake and Ninja are available."""
    if shutil.which("cmake") is None:
        session.install("cmake")
    if shutil.which("ninja") is None:
        session.install("ninja")


def install(
    session: nox.Session,
    *,
    build_isolation: bool = True,
    package: str | None = None,
    groups: Sequence[str] = (),
    install_args: Sequence[str] = (),
) -> None:
    """Install the project and selected groups from the lockfile.

    With ``build_isolation=False``, install the ``build`` group and build the project in the session environment.
    ``package`` defaults to ``project.name`` in pyproject.toml. Additional ``install_args`` are passed to uv sync.
    """
    if not build_isolation:
        package = package or nox.project.load_toml()["project"]["name"]
        prepare_build_env(session)
        groups = ["build", *groups]
        install_args = ["--no-build-isolation-package", package, *install_args]
    session.run(
        "uv",
        "sync",
        "--locked",
        "--inexact",
        "--no-dev",
        *(arg for group in groups for arg in ["--group", group]),
        *install_args,
    )


def tests(
    session: nox.Session,
    *,
    build_isolation: bool = True,
    package: str | None = None,
    install_args: Sequence[str] = (),
    pytest_args: Sequence[str] = (),
    extra_deps: Sequence[str] = (),
) -> None:
    """Install the test group and run pytest with optional dependency overrides.

    ``install_args`` go to uv sync. ``pytest_args`` precede session.posargs. ``extra_deps`` are installed after
    synchronization, e.g. an upstream SDK. The test group must include pytest-cov for the shared coverage configuration.
    """
    install(session, build_isolation=build_isolation, package=package, groups=["test"], install_args=install_args)
    common.run_pytest(session, pytest_args=pytest_args, extra_deps=extra_deps)


def qiskit(
    session: nox.Session,
    *,
    build_isolation: bool = True,
    package: str | None = None,
    install_args: Sequence[str] = (),
    pytest_args: Sequence[str] = (),
) -> None:
    """Test against Qiskit's main branch after installing the locked baseline."""
    tests(
        session,
        build_isolation=build_isolation,
        package=package,
        install_args=install_args,
        pytest_args=pytest_args,
        extra_deps=["qiskit[qasm3-import] @ git+https://github.com/Qiskit/qiskit.git"],
    )


def minimums(
    session: nox.Session,
    *,
    build_isolation: bool = True,
    package: str | None = None,
    install_args: Sequence[str] = (),
    pytest_args: Sequence[str] = (),
) -> None:
    """Test lowest direct dependencies without reading or changing uv.lock.

    With ``build_isolation=False``, install the ``build`` and ``test`` groups before building the project.
    ``package`` defaults to ``project.name`` in pyproject.toml. ``install_args`` are passed to uv pip install.
    """
    install_command = [
        "uv",
        "pip",
        "install",
        "--upgrade",
        "--resolution=lowest-direct",
        *(["--group", "build"] if not build_isolation else []),
        "--group",
        "test",
    ]
    if not build_isolation:
        package = package or nox.project.load_toml()["project"]["name"]
        prepare_build_env(session)
        session.run(*install_command, *install_args)
        install_args = ["--no-build-isolation-package", package, *install_args]
    session.run(
        *install_command,
        "--editable",
        ".",
        *install_args,
    )
    common.run_pytest(session, pytest_args=["-Wdefault", *pytest_args])
    session.run("uv", "pip", "tree")


def docs(
    session: nox.Session,
    *,
    build_isolation: bool = True,
    package: str | None = None,
    install_args: Sequence[str] = (),
    sphinx_args: Sequence[str] = (),
) -> None:
    """Install the docs group and build or serve Sphinx documentation."""
    install(session, build_isolation=build_isolation, package=package, groups=["docs"], install_args=install_args)
    common.run_sphinx(session, sphinx_args=sphinx_args)


def stubs(
    session: nox.Session,
    *,
    modules: Sequence[str],
    package: str | None = None,
    output_dir: str | Path | None = None,
    stubgen_args: Sequence[str] = (),
) -> None:
    """Build a nanobind package without isolation, generate its stubs, and run the MQT stub hooks.

    The ``build`` group must include nanobind. ``modules`` contains Python import names, e.g. ``mqt.qmap.sc``.
    MQT distribution names such as ``mqt-qmap`` determine the default output directory, e.g. ``python/mqt/qmap``.
    Extra arguments go to nanobind.stubgen.
    """
    if not modules:
        session.error("At least one nanobind module is required")
    package = package or nox.project.load_toml()["project"]["name"]
    module_prefix = package.replace("-", ".")
    install(session, build_isolation=False, package=package)
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

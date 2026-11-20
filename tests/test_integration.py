"""Exercise shared functions through real Nox sessions and installed packages."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

import pytest


def write_wheel(directory: Path, version: int) -> Path:
    """Provide local dependency versions without relying on a package index."""
    name = "mqt_nox_probe_dep"
    wheel = directory / f"{name}-{version}.0-py3-none-any.whl"
    dist_info = f"{name}-{version}.0.dist-info"
    files = {
        f"{name}/__init__.py": f"VERSION = {version}\n",
        f"{dist_info}/METADATA": (f"Metadata-Version: 2.1\nName: mqt-nox-probe-dep\nVersion: {version}.0\n"),
        f"{dist_info}/WHEEL": "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    files[f"{dist_info}/RECORD"] = "".join(f"{name},,\n" for name in [*files, f"{dist_info}/RECORD"])
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return wheel


@pytest.fixture(params=["python", "cpp"])
def project(tmp_path: Path, request):
    if shutil.which("uv") is None:
        pytest.skip("uv is required for the integration tests")
    native = request.param == "cpp"
    if native and any(shutil.which(tool) is None for tool in ("cmake", "ninja", "c++")):
        pytest.skip("CMake, Ninja, and a C++ compiler are required")
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    for version in (1, 2):
        write_wheel(wheels, version)
    upstream = tmp_path / "upstream"
    (upstream / "src/mqt_nox_probe_dep").mkdir(parents=True)
    (upstream / "src/mqt_nox_probe_dep/__init__.py").write_text("VERSION = 3\n")
    (upstream / "pyproject.toml").write_text(
        textwrap.dedent("""\
        [build-system]
        requires = ["uv-build>=0.13,<0.14"]
        build-backend = "uv_build"
        [project]
        name = "mqt-nox-probe-dep"
        version = "3.0"
        """)
    )
    subprocess.run(["git", "init", "--quiet"], cwd=upstream, check=True)
    subprocess.run(["git", "add", "."], cwd=upstream, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "--no-gpg-sign",
            "-qm",
            "Fixture",
        ],
        cwd=upstream,
        check=True,
    )
    build_requires = ["scikit-build-core>=1.1", "nanobind~=3.1.0"] if native else ["uv-build>=0.13,<0.14"]
    backend = "scikit_build_core.build" if native else "uv_build"
    (tmp_path / "pyproject.toml").write_text(
        textwrap.dedent(f'''\
        [build-system]
        requires = {json.dumps(build_requires)}
        build-backend = "{backend}"
        [project]
        name = "mqt-nox-probe"
        version = "0.1.0"
        requires-python = ">=3.11"
        dependencies = ["mqt-nox-probe-dep>=1,<3"]
        [dependency-groups]
        build = {json.dumps(build_requires)}
        test = ["pytest>=9", "pytest-cov>=7", "pytest-xdist>=3.8"]
        docs = ["sphinx>=9"]
        [tool.uv]
        find-links = ["wheels"]
        [tool.uv.build-backend]
        module-name = "probe"
        [tool.scikit-build]
        wheel.packages = []
        build-dir = "build/shared"
        ''')
    )
    if native:
        (tmp_path / "CMakeLists.txt").write_text(
            textwrap.dedent("""\
            cmake_minimum_required(VERSION 3.18)
            project(probe LANGUAGES CXX)
            file(WRITE "${CMAKE_BINARY_DIR}/parallel_jobs" "$ENV{CMAKE_BUILD_PARALLEL_LEVEL}")
            find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
            execute_process(COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
                OUTPUT_VARIABLE nanobind_DIR OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
            find_package(nanobind CONFIG REQUIRED)
            nanobind_add_module(probe probe.cpp)
            target_compile_definitions(probe PRIVATE PROBE_BUILD_DIR="${CMAKE_BINARY_DIR}")
            install(TARGETS probe LIBRARY DESTINATION .)
            """)
        )
        (tmp_path / "probe.cpp").write_text(
            textwrap.dedent("""\
            #include <nanobind/nanobind.h>
            NB_MODULE(probe, module) {
                module.def("answer", []() { return 42; });
                module.def("build_dir", []() { return PROBE_BUILD_DIR; });
            }
            """)
        )
    else:
        (tmp_path / "src/probe").mkdir(parents=True)
        (tmp_path / "src/probe/__init__.py").write_text("def answer():\n    return 42\n")
    (tmp_path / "test_probe.py").write_text(
        textwrap.dedent("""\
        import json
        import hashlib
        import os
        from importlib.metadata import distribution
        from pathlib import Path
        import sys
        import time
        import mqt_nox_probe_dep
        import probe

        def test_selected():
            assert probe.answer() == 42
            assert mqt_nox_probe_dep.VERSION == int(os.environ["EXPECTED_VERSION"])
            assert Path(sys.prefix).parent.name == ".nox"
            assert os.environ["FROM_SESSION"] == "preserved"
            assert Path(os.environ["UV_PROJECT_ENVIRONMENT"]) == Path(sys.prefix)
            if "EXPECTED_REVISION" in os.environ:
                dist = distribution("mqt-nox-probe-dep")
                source = json.loads(dist.read_text("direct_url.json"))
                assert source["vcs_info"]["vcs"] == "git"
                assert source["vcs_info"]["commit_id"] == os.environ["EXPECTED_REVISION"]
                assert source["url"] == Path("upstream").resolve().as_uri()
                assert Path(mqt_nox_probe_dep.__file__).is_relative_to(Path(sys.prefix))
                assert dist.locate_file("mqt_nox_probe_dep/__init__.py").samefile(mqt_nox_probe_dep.__file__)
            if "PEER_SESSION" in os.environ:
                assert "PYTEST_XDIST_WORKER" not in os.environ
                assert Path(os.environ["COVERAGE_FILE"]).parent == Path(sys.prefix)
                if hasattr(probe, "build_dir"):
                    assert Path(probe.build_dir()).is_relative_to(Path(sys.prefix))
                    expected_jobs = os.environ.get("CMAKE_BUILD_PARALLEL_LEVEL", "1")
                    assert Path(probe.build_dir(), "parallel_jobs").read_text() == expected_jobs
                Path(sys.prefix, "started").touch()
                peer = Path(".nox", os.environ["PEER_SESSION"], "started")
                deadline = time.monotonic() + 60
                while not peer.exists():
                    assert time.monotonic() < deadline, "sessions did not overlap"
                    time.sleep(0.05)
                assert hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest() == os.environ["LOCK_HASH"]

        def test_unselected():
            raise AssertionError("pytest arguments were not forwarded")
        """)
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "conf.py").write_text('project = "Probe"\n')
    (docs / "index.rst").write_text("Probe\n=====\n\nShared documentation works.\n")
    package_arg = ', package="mqt-nox-probe"' if native else ""
    override = f"mqt-nox-probe-dep @ git+{upstream.as_uri()}"
    (tmp_path / "noxfile.py").write_text(
        textwrap.dedent(f"""\
        import nox
        from mqt.nox import {request.param} as shared

        nox.options.default_venv_backend = "uv"

        @nox.session(reuse_venv=True)
        def tests(session):
            session.env["FROM_SESSION"] = "preserved"
            shared.tests(session{package_arg}, pytest_args=("-q",))

        @nox.session(reuse_venv=True)
        def upstream(session):
            session.env["FROM_SESSION"] = "preserved"
            shared.tests(session{package_arg}, install_args=("--locked",), extra_deps=({override!r},))

        @nox.session(reuse_venv=True)
        def minimums(session):
            session.env["FROM_SESSION"] = "preserved"
            shared.minimums(session{package_arg})

        @nox.session(reuse_venv=True)
        def docs(session):
            shared.docs(session{package_arg})

        @nox.session(reuse_venv=True, allow_parallel=True)
        def locked_parallel(session):
            session.env.update(FROM_SESSION="preserved", EXPECTED_VERSION="2", PEER_SESSION="minimums_parallel")
            shared.tests(session{package_arg}, pytest_args=("-n", "auto"))

        @nox.session(reuse_venv=True, allow_parallel=True)
        def minimums_parallel(session):
            session.env.update(FROM_SESSION="preserved", EXPECTED_VERSION="1", PEER_SESSION="locked_parallel")
            shared.minimums(session{package_arg}, pytest_args=("-n", "auto"))
        """)
    )
    if native:
        with (tmp_path / "noxfile.py").open("a") as noxfile:
            noxfile.write(
                textwrap.dedent("""\

                @nox.session(reuse_venv=True)
                def stubs(session):
                    session.install("ruff")
                    shared.stubs(session, package="mqt-nox-probe", modules=("probe",), output_dir="stubs")
                """)
            )
        subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
        (tmp_path / ".pre-commit-config.yaml").write_text(
            textwrap.dedent("""\
            repos:
              - repo: local
                hooks:
                  - id: license-tools
                    name: Validate generated Python syntax
                    language: system
                    entry: python -m py_compile
                  - id: ruff-check
                    name: Ruff
                    language: system
                    entry: python -m ruff check --fix
                  - id: ruff-format
                    name: Ruff format
                    language: system
                    entry: python -m ruff format
            """)
        )
    subprocess.run(["uv", "lock"], cwd=tmp_path, check=True)
    return tmp_path


def run_nox(
    project: Path, session: str, version: int, *args: str, success: bool = True, no_install: bool = False
) -> str:
    env = {**os.environ, "EXPECTED_VERSION": str(version)}
    if session == "upstream":
        env["EXPECTED_REVISION"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=project / "upstream", text=True
        ).strip()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "nox",
            "--non-interactive",
            *(["--no-install"] if no_install else []),
            "-s",
            session,
            "--",
            *args,
        ],
        cwd=project,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) == success, result.stdout
    return result.stdout


def test_tests_minimums_and_upstream_override(project):
    run_nox(project, "tests", 2, "-k", "test_selected")
    lockfile = project / "uv.lock"
    original = lockfile.read_bytes()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project / "upstream", text=True).strip()
    for no_install in (False, True):
        output = run_nox(project, "upstream", 3, "-k", "test_selected", no_install=no_install)
        assert f"mqt-nox-probe-dep @ git+{(project / 'upstream').as_uri()}@{revision}" in output
        assert lockfile.read_bytes() == original
    run_nox(project, "tests", 2, "-k", "test_selected")
    run_nox(project, "minimums", 1, "-k", "test_selected")
    assert lockfile.read_bytes() == original
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(project / ".nox/minimums"),
            str(project / "wheels/mqt_nox_probe_dep-2.0-py3-none-any.whl"),
        ],
        cwd=project,
        check=True,
    )
    run_nox(project, "minimums", 1, "-k", "test_selected", no_install=True)
    assert lockfile.read_bytes() == original
    run_nox(project, "minimums", 1, "-k", "test_unselected", success=False)
    assert lockfile.read_bytes() == original
    lockfile.unlink()
    run_nox(project, "minimums", 1, "-k", "test_selected")
    assert not lockfile.exists()


def test_documentation_build(project):
    run_nox(project, "docs", 2, "-b", "html", "-W")
    assert "Shared documentation works." in (project / "docs/_build/html/index.html").read_text()
    if (project / "probe.cpp").exists():
        run_nox(project, "stubs", 2)
        assert "def answer() -> int:" in (project / "stubs/probe.pyi").read_text()


def test_parallel_sessions(project):
    run_nox(project, "tests", 2, "-k", "test_selected")
    original = (project / "uv.lock").read_bytes()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "nox",
            "--non-interactive",
            "-j",
            "2",
            "-s",
            "locked_parallel",
            "minimums_parallel",
            "--",
            "-k",
            "test_selected",
            "--cov=mqt_nox_probe_dep",
            "--cov-report=xml:coverage.xml",
            "--cov-report",
            "json",
            "--cov-report=lcov:-",
        ],
        cwd=project,
        env={**os.environ, "LOCK_HASH": hashlib.sha256(original).hexdigest(), "PYTEST_XDIST_AUTO_NUM_WORKERS": "2"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout
    assert "SF:" in result.stdout
    assert (project / "uv.lock").read_bytes() == original
    for session in ("locked_parallel", "minimums_parallel"):
        assert (project / f"coverage-{session}.xml").is_file()
        assert json.loads((project / f"coverage-{session}.json").read_text())["totals"]["covered_lines"] > 0
    assert not (project / "coverage.xml").exists()
    assert not (project / "coverage.json").exists()

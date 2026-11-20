"""Check documentation behavior at the public interface."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from mqt.nox import sphinx


@pytest.mark.parametrize(
    ("interactive", "posargs", "command", "builder"),
    [
        (True, [], "sphinx-autobuild", "html"),
        (False, ["-W"], "sphinx-build", "html"),
        (True, ["-b", "linkcheck", "-W"], "sphinx-build", "linkcheck"),
    ],
)
def test_sphinx_builder_and_serving(interactive, posargs, command, builder):
    class Session:
        def __init__(self):
            self.interactive = interactive
            self.posargs = posargs
            self.installed = []
            self.commands = []
            self.virtualenv = SimpleNamespace(location=".nox/docs")

        def install(self, *args):
            self.installed.extend(args)

        def run(self, *args, env):
            assert env["UV_PROJECT_ENVIRONMENT"] == ".nox/docs"
            self.commands.append(args)

    session = Session()
    sphinx(session, sphinx_args=("-E",))
    assert session.installed == (["sphinx-autobuild"] if command == "sphinx-autobuild" else [])
    invocation = session.commands[0]
    assert invocation[0] == command
    assert f"-b={builder}" in invocation
    assert str(Path("docs/_build") / builder) in invocation
    assert "-E" in invocation
    assert ("-W" in invocation) == ("-W" in posargs)

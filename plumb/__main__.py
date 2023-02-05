import plumb as _
from pathlib import Path
import os

from .grammar import parse_commands
from .world import World
from .routable import Routable
from . import ast


def route_command_line_args(commands: list[ast.Command], args: list[str]) -> World:
    world = World()
    for arg in args:
        wdir = None  # TODO from command line args.
        type = None  # TODO from command line args.

        if wdir is None:
            wdir = os.getcwd()
        if wdir and type is None:
            p = Path(wdir).joinpath(arg)
            if p.is_file():
                type = "file"
            if p.is_dir():
                type = "dir"
        if type is None:
            type = "text"
        msg = Routable(
            src="",
            dst="",
            data=arg,
            original_data=arg,
            wdir=Path(wdir),
            type=type,
            attr={},
        )
        world.next_obj(msg)
        world.route(commands, msg)
    return world


def main():
    import sys
    from pathlib import Path

    # TODO: honor XDG_CONFIG_HOME
    with open(Path.home().joinpath(".config/plumb_rules")) as rulefd:
        rules = parse_commands(rulefd.read())
    w = route_command_line_args(rules, sys.argv[1:])
    w.run()


if __name__ == "__main__":
    main()

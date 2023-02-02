import plumb as _

from .grammar import parse_commands
from .world import World
from .routable import Routable
from . import ast


def route_command_line_args(commands: list[ast.Command], args: list[str]) -> World:
    world = World()
    for arg in args:
        msg = Routable(
            src="",
            dst="",
            data=arg,
            original_data=arg,
            wdir=None,
            type="text",
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

import plumb as _

from .grammar import parser, Plumbing
from .world import World
from . import ast


def parse_rules(text):
    p = parser.parse(text)
    rules: list[ast.Rule] = Plumbing().transform(p).children
    return rules


def route(rules: list[ast.Rule], args: list[str]) -> World:
    w = World()
    for arg in args:
        w.stop_routing = False

        for r in rules:
            r.route(w, arg)
            if w.stop_routing:
                break
    return w


def main():
    import sys
    from pathlib import Path

    # TODO: honor XDG_CONFIG_HOME
    with open(Path.home().joinpath(".config/plumb_rules")) as rulefd:
        rules = parse_rules(rulefd.read())
    w = route(rules, sys.argv[1:])
    w.run()


if __name__ == "__main__":
    main()

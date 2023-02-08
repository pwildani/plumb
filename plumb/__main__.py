import plumb as _
from pathlib import Path
import os

from .grammar import parse_commands
from .world import World
from .routable import Routable
from . import ast

import click


def route_file(world: World, commands: list[ast.Command], file: str | Path) -> World:
    wdir = None  # TODO from command line args.
    type = None  # TODO from command line args.
    if wdir is None:
        wdir = os.getcwd()
    if wdir and type is None:
        p = Path(wdir).joinpath(file) if isinstance(file, str) else file
        if p.is_file():
            type = "file"
            print(f"{p} is a file!")
        if p.is_dir():
            type = "dir"
            print(f"{p} is a dir!")
    if type is None:
        type = "text"
    msg = Routable(
        src="",
        dst="",
        data=file,
        original_data=file,
        wdir=Path(wdir),
        type=type,
        attr={},
    )
    world.next_obj(msg)
    world.route(commands, msg)
    return world


def route_command_line_args(
    ctx, commands: list[ast.Command], args: list[str] | list[Path]
) -> World:
    world = World()
    for arg in args:
        route_file(world, commands, arg)
    return world


def load_rules():
    # TODO: honor XDG_CONFIG_HOME
    with open(Path.home().joinpath(".config/plumb_rules")) as rulefd:
        return parse_commands(rulefd.read())


def main():
    import sys

    rules = load_rules()
    w = route_command_line_args(None, rules, sys.argv[1:])
    w.run()


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context):
    if ctx.invoked_subcommand is None:
        ctx.invoke(file)


@cli.command()
@click.option("--verbose", type=bool, default=False)
def check(verbose):
    rules = load_rules()
    if verbose:
        import pprint

        pprint.pprint(rules)


@cli.command()
@click.argument("files", nargs=-1, type=click.Path())
@click.option("--wdir", type=str, default=None)
@click.pass_context
def file(ctx, files, wdir):
    rules = load_rules()
    route_command_line_args(ctx, rules, files)

    pass


@cli.command()
@click.argument("target", nargs=1, type=click.Path())
def watch(target):
    rules = load_rules()
    # on rule file updates: load rules
    # on target dir subtree modification, route new paths
    # TODO decide what to do with removed paths
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    import watchdog.events

    observer = Observer()

    class RuleUpdater(FileSystemEventHandler):
        def on_any_event(self, _: watchdog.events.FileSystemEvent):
            nonlocal rules
            rules = load_rules()

    config = Path.home().joinpath(".config/plumb_rules")
    observer.schedule(RuleUpdater(), str(config))

    class Router(FileSystemEventHandler):
        # on_any_event
        # on_created
        # on_deleted
        # on_modifiedent
        # on_moved
        def on_created(self, event: watchdog.events.FileCreatedEvent):
            world = World()
            world = route_file(world, rules, event.src_path)
            world.run()

        def on_moved(self, event: watchdog.events.FileMovedEvent):
            world = World()
            world = route_file(world, rules, event.dest_path)
            world.run()

    observer.schedule(Router(), target, recursive=True)
    observer.start()
    try:
        while observer.is_alive():
            observer.join(1)
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()

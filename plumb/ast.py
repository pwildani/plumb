from dataclasses import dataclass
from fnmatch import fnmatchcase
import stat
import re
from typing import Any, Generator
import os

import logging

logger = logging.getLogger()
logging.basicConfig()

from .world import World
from .routable import Routable
from .util import optstr


from .aast import Command, CommandResult, Expr, Condition, Action, Value


@dataclass
class RuleCommand(Command):
    """
    A stanza of conditions and actions to run if the conditions are true.
    """

    label: str

    def run(self, world: World, value: Routable) -> CommandResult:
        return CommandResult.NEXT_COMMAND


@dataclass
class VariableReference(Expr):
    var: str

    def eval(self, world: World, value: Routable) -> Value:
        return world.var(self.var, None)


@dataclass
class ExprLiteral(Expr):
    val: str

    def eval(self, world: World, value: Routable) -> Value:
        return self.val


def as_constant(ex: Expr):
    if isinstance(ex, ExprLiteral):
        return ex.val
    return None


@dataclass
class SetVariable(Action, Command):
    var: str
    rhs: Expr

    def run(self, world: World, value: Routable) -> CommandResult:
        world.set_var(self.var, optstr(self.rhs.eval(world, value)))
        return CommandResult.NEXT_COMMAND

    def check(self, world: World, value: Routable) -> bool:
        world.set_var(self.var, optstr(self.rhs.eval(world, value)))
        return True

    def route(self, world: World, value: Routable) -> None:
        world.set_var(self.var, optstr(self.rhs.eval(world, value)))


@dataclass
class CopyToAction(Action, Command):
    destination: Expr

    def run(self, world: World, value: Routable) -> CommandResult:
        src: str | None = optstr(value.data)
        dst = optstr(self.destination.eval(world, value))
        if src is not None and dst is not None:
            world.add_rsync(dst, [src])
        return CommandResult.NEXT_COMMAND


@dataclass
class MoveToAction(Action, Command):
    destination: Expr

    def run(self, world: World, value: Routable) -> CommandResult:
        src: str | None = optstr(value.data)
        dst = optstr(self.destination.eval(world, value))
        if src is not None and dst is not None:
            world.add_move(dst=dst, src=src)

        return CommandResult.NEXT_COMMAND


@dataclass
class StopAction(Action):
    def run(self, world: World, value: Routable) -> CommandResult:
        return CommandResult.STOP


@dataclass
class ConditionCommand(Command):
    condition: Condition

    def run(self, world: World, value: Routable) -> CommandResult:
        if self.condition.check(world, value):
            return CommandResult.NEXT_COMMAND
        return CommandResult.NEXT_RULE


@dataclass
class AndCondition(Condition):
    children: tuple[Condition, ...]

    def check(self, world: World, value: Routable) -> bool:
        return all(c.check(world, value) for c in self.children)


@dataclass
class OrCondition(Condition):
    children: tuple[Condition, ...]

    def check(self, world: World, value: Routable) -> bool:
        return any(c.check(world, value) for c in self.children)


@dataclass
class NotCondition(Condition):
    child: Condition

    def check(self, world: World, value: Routable) -> bool:
        return not self.child.check(world, value)


@dataclass
class GlobCondition(Condition):
    pattern: Expr

    def check(self, world: World, value: Routable) -> bool:
        dat = self.get_str_data(world, value)
        pat = optstr(self.pattern.eval(world, value))
        return dat is not None and pat is not None and fnmatchcase(dat, pat)


@dataclass
class RegexCondition(Condition):
    pattern: Expr

    def check(self, world: World, value: Routable) -> bool:
        dat = self.get_str_data(world, value)
        if dat is None:
            return False
        pat = optstr(self.pattern.eval(world, value))
        if pat is None:
            return False
        regex = re.compile(pat)
        if m := regex.match(dat):
            world.set_var("0", m.group(0))
            for i, g in enumerate(m.groups()):
                world.set_var(str(i + 1), g)
            for k, g in m.groupdict().items():
                world.set_var(k, g)
            return True
        return False


@dataclass
class StatFileTypeCondition(Condition):
    filetype: str

    _notsupported = lambda _: False
    MODE_TYPES = {
        "dir": stat.S_ISDIR,
        "chardev": stat.S_ISCHR,
        "blockdev": stat.S_ISBLK,
        "file": stat.S_ISREG,
        "fifo": stat.S_ISFIFO,
        "pipe": stat.S_ISFIFO,
        "sock": stat.S_ISSOCK,
        "door": getattr(stat, "S_ISDOOR", _notsupported),
        "port": getattr(stat, "S_ISPORT", _notsupported),
        "wht": getattr(stat, "S_ISWHT", _notsupported),
        "whiteout": getattr(stat, "S_ISWHT", _notsupported),
    }

    def check(self, world: World, value: Routable) -> bool:
        dat = self.get_path_data(world, value)
        pathname = world.var("file", dat)
        st = world.stat_path(pathname)
        if st is None:
            return False
        if is_x := self.MODE_TYPES.get(self.filetype):
            return is_x(st.st_mode)
        return False


@dataclass
class InspectAction(Action):
    arg: Any

    def run(self, world: World, value: Routable) -> CommandResult:
        from pprint import pprint

        if self.arg == "all":
            pprint(world.vars)
        elif isinstance(expr := self.arg, Expr):
            pprint(expr)
            print("==>")
            pprint(expr.eval(world, value))
        elif isinstance(cond := self.arg, Condition):
            pprint(cond)
            print("==>")
            pprint(cond.check(world, value))

        return CommandResult.NEXT_COMMAND


import weakref
from pathlib import Path


greps: weakref.WeakSet["GrepCondition"] = weakref.WeakSet()


@dataclass
class GrepCondition(Condition):
    pattern: Expr

    def __post_init__(self):
        greps.add(self)

    def __hash__(self):
        return id(self)

    def _check_all(self, world: World, dat: Path) -> Generator[bool, bytes, None]:
        """
        Arange to run all registered greps over the target, so we only have to
        read each input file once, regardless of the number of greps.
        """
        regexen = {}
        for g in greps:
            if (c := as_constant(g.pattern)) is not None:
                if dat not in world.greps[g]:
                    p = re.compile(c.encode())
                    regexen[g] = p

        try:
            while True:
                line = yield bool(len(regexen))
                hit = set()
                for g, p in regexen.items():
                    if p.search(line):
                        world.greps[g][dat] = True
                        hit.add(g)
                for g in hit:
                    del regexen[g]
        except GeneratorExit:
            for g, p in regexen.items():
                if g in world.greps:  # can hit this during system teardown
                    if dat not in world.greps[g]:
                        world.greps[g][dat] = False

    def check(self, world: World, value: Routable) -> bool:
        pat = optstr(self.pattern.eval(world, value))
        if pat is None:
            return False

        dat = self.get_path_data(world, value)
        if dat:
            # If we've already processed this grep for this file, use the cached result.
            if dat in world.greps[self]:
                return world.greps[self][dat]

            regex = None
            if as_constant(self.pattern) is None:
                regex = re.compile(pat.encode())

            if dat in world.reads:
                # If we have a read in progress for this path, resume it.
                fh, chk = world.reads[dat]
            else:
                # Otherwise, set up to run all greps in parallel over this file.
                chk = self._check_all(world, dat)
                next(chk)  # run initialization code
                fh = open(dat, "rb")
                trace = world.var("debugtrace", False)
                if trace:
                    print("OPEN", dat)

            # TODO: find / write a regex over stream to avoid arbitrarily
            # breaking binary files at newlines without also reading multi GB files into ram.
            # https://github.com/nitely/regexy, maybe?
            for line in fh:
                if regex is not None and regex.search(line):
                    world.greps[self][dat] = True
                    regex = None
                if chk is not None:
                    if not chk.send(line):
                        chk.close()
                        chk = None
                if regex is None and chk is None:
                    # Both this dynamic pattern and all static patterns are found.
                    fh.close()
                    if dat in world.reads:
                        del world.reads[dat]
                    break

                if dat in world.greps[self]:
                    # Hit for this grep (either in chk for static patterns or
                    # regex for dynamic patterns). Save state to resume if
                    # other greps are consulted, but early exit for now.
                    if chk is not None:
                        world.reads[dat] = (fh, chk)
                        chk = None
                    break
            else:
                # We finished the file. Mark that we didn't find a match for
                # this grep (because no early exit) AND we didn't find a match for any other pending
                # greps (by closing chk)
                if regex is not None:
                    world.greps[self][dat] = False
                fh.close()
                if chk is not None:
                    chk.close()
                if dat in world.reads:
                    del world.reads[dat]

            return world.greps[self][dat]

        return False


@dataclass
class EnvironmentLookupExpr(Expr):
    name: Expr

    def eval(self, world: World, value: Routable) -> Value:
        name = self.name.eval(world, value)
        if (strname := optstr(name)) is not None:
            return os.getenv(strname)
        return None


@dataclass
class StringConcatExpr(Expr):
    parts: list[Expr]

    def eval(self, world: World, value: Routable) -> Value:
        return "".join(optstr(p.eval(world, value)) or "" for p in self.parts)

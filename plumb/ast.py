from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Protocol
import stat

from .world import World

Routable = str


class Action(Protocol):
    """
    A thing that modifies the World to make itself happen using the value.
    """

    def run(self, world: World, value: Routable) -> None:
        ...


class Condition(Protocol):
    """
    A thing that checks the world or value for validity.
    """

    def check(self, world: World, value: Routable) -> bool:
        ...


@dataclass
class Rule:
    """
    A stanza of conditions and actions to run if the conditions are true.
    """

    label: str
    conditions: list[Condition]
    actions: list[Action]

    def route(self, world: World, value: Routable):
        if any(c.check(world, value) for c in self.conditions):
            for action in self.actions:
                action.run(world, value)


@dataclass
class CopyToAction(Action):
    destination: str

    def run(self, world: World, value: Routable) -> None:
        world.rsync[self.destination].append(value)


@dataclass
class StopAction(Action):
    def run(self, world: World, value: Routable) -> None:
        world.stop_routing = True


@dataclass
class AndCondition(Condition):
    children: tuple[Condition, ...]

    def check(self, world: World, value: Routable) -> bool:
        return all(c.check(world, value) for c in self.children)


@dataclass
class NotCondition(Condition):
    child: Condition

    def check(self, world: World, value: Routable) -> bool:
        return not self.child.check(world, value)


@dataclass
class GlobCondition(Condition):
    pattern: str

    def check(self, world: World, value: Routable) -> bool:
        return fnmatchcase(value, self.pattern)


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
        st = world.stat_path(value)
        if st is None:
            return False
        if is_x := self.MODE_TYPES.get(self.filetype):
            return is_x(st.st_mode)
        return False

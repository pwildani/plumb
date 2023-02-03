from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol
import typing

from .util import optstr, optpath

from .routable import Routable

if typing.TYPE_CHECKING:
    from .world import World

Value = str | bytes | Path | None


class Action(Protocol):
    """
    A thing that modifies the World to make itself happen using the value.
    """

    def run(self, world: "World", value: Routable) -> None:
        ...


class Expr:
    def eval(self, world: "World", value: Routable) -> Value:
        ...


class Condition:
    """
    A thing that checks the world or value for validity.
    """

    datasource: Expr | None = None

    def get_str_data(self, world: "World", value: Routable) -> str | None:
        if self.datasource is None:
            return optstr(value.data)
        else:
            return optstr(self.datasource.eval(world, value))

    def get_path_data(self, world: "World", value: Routable) -> Path | None:
        if self.datasource is None:
            return optpath(value.data)
        else:
            return optpath(self.datasource.eval(world, value))

    def check(self, world: "World", value: Routable) -> bool:
        ...


class CommandResult(Enum):
    NEXT_COMMAND = None
    NEXT_RULE = "next"
    STOP = "stop"


class Command(Protocol):
    def run(self, world: "World", value: Routable) -> CommandResult:
        ...

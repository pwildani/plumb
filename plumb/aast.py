from enum import Enum
from pathlib import Path
from typing import Protocol
import typing

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


class Condition(Protocol):
    """
    A thing that checks the world or value for validity.
    """

    def check(self, world: "World", value: Routable) -> bool:
        ...


class Expr(Protocol):
    def eval(self, world: "World", value: Routable) -> Value:
        ...


class CommandResult(Enum):
    NEXT_COMMAND = None
    NEXT_RULE = "next"
    STOP = "stop"


class Command(Protocol):
    def run(self, world: "World", value: Routable) -> CommandResult:
        ...

from pathlib import Path
from typing import overload


@overload
def optstr(val: None) -> None:
    ...


@overload
def optstr(val: Path | str | bytes) -> str:
    ...


def optstr(val):
    return None if val is None else str(val)


@overload
def optpath(val: None) -> None:
    ...


@overload
def optpath(val: Path | str | bytes) -> Path:
    ...


def optpath(val):
    return None if val is None else Path(val)

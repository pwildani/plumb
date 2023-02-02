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

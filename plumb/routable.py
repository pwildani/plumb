from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Routable:
    # identifier for source of message
    src: str
    # who the source thinks they are talking to where the message should be routed
    dst: str

    # the thing being routed
    data: str | bytes | Path
    original_data: str | bytes | Path

    type: str

    # Working directory, if data is a file path
    wdir: Optional[Path]

    attr: dict[str, str]

    @property
    def ndata(self):
        if not self.data:
            return 0
        if isinstance(self.data, Path):
            return len(str(self.data))
        return len(self.data)

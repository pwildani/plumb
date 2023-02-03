from collections import defaultdict
import shlex
import os
from typing import TypeVar, TYPE_CHECKING, Iterable
from pathlib import Path

from .routable import Routable
from .util import optstr
from . import aast

if TYPE_CHECKING:
    import ast

T = TypeVar("T")


class World:
    def __init__(self):
        self.rsync: defaultdict[str, list[str]] = defaultdict(list)
        self.dry_run = True
        self.shell_commands: list[list[str]] = []
        self._stat_cache: dict[str, os.stat_result] = {}
        self.mode = aast.CommandResult.NEXT_COMMAND

        self.vars = {}
        self.obj: Routable | None = None

    def run(self):
        # Consolidate rsync/copies to the same destination
        for dest, srcs in self.rsync.items():
            cmd = ["rsync", "-vaP", *srcs, dest]
            self.shell_commands.append(cmd)

        # Run the accumulated external commands
        if self.dry_run:
            for cmd in self.shell_commands:
                print(shlex.join(cmd))
        else:
            for cmd in self.shell_commands:
                system.execute.the.command.notimplemented

    def stat_path(self, path: str | bytes | Path | None) -> os.stat_result | None:
        if path is None:
            return None
        assert path is not None
        if path not in self._stat_cache:
            self._stat_cache[optstr(path)] = Path(path).stat()
        return self._stat_cache[optstr(path)]

    def next_obj(self, obj):
        self.obj = obj
        self.init_obj_dir_vars()
        self.vars["attr"] = ",".join(f"{k}={v}" for k, v in self.obj.attr.items())
        self.vars["data"] = self.obj.data
        self.vars["dst"] = self.obj.dst
        self.vars["type"] = self.obj.type
        self.vars["src"] = self.obj.src
        self.vars["wdir"] = self.obj.wdir

    def init_obj_dir_vars(self):
        obj = self.obj
        assert obj
        dat = optstr(obj.data)
        if obj.wdir is not None and dat is not None:
            self.set_var("dir", str(obj.wdir.joinpath(dat)))
            self.set_var("file", str(obj.wdir.joinpath(dat)))

    def set_var(self, key: str, value: str | None) -> None:
        assert self.obj
        strvalue = "" if value is None else value
        match key:
            case "attr":
                self.obj.attr = {
                    k: v for o in strvalue.split(",") for k, _, v in o.partition("=")
                }
            case "data":
                self.obj.data = strvalue
            case "dst":
                self.obj.dst = strvalue
            case "type":
                self.obj.type = strvalue
            case "src":
                self.obj.src = strvalue
            case "wdir":
                if value:
                    self.obj.wdir = Path(value)
                    self.init_obj_dir_vars()
                else:
                    self.obj.wdir = None
        self.vars[key] = value

    def var(self, key: str, default: str | T) -> str | bytes | Path | None | T:
        assert self.obj
        match key:
            case "attr":
                return ",".join(f"{k}={v}" for k, v in self.obj.attr.items())
            case "data":
                return self.obj.data
            case "dst":
                return self.obj.dst
            case "type":
                return self.obj.type
            case "src":
                return self.obj.src
            case "wdir":
                return self.obj.wdir
        return self.vars.get(key, default)

    def route(self, commands: Iterable[aast.Command], value: Routable):
        from .ast import RuleCommand

        self.mode = aast.CommandResult.NEXT_COMMAND
        for cmd in commands:
            match self.mode:
                case aast.CommandResult.NEXT_COMMAND:
                    self.mode = cmd.run(self, value)
                case aast.CommandResult.NEXT_RULE:
                    if isinstance(cmd, RuleCommand):
                        self.mode = cmd.run(self, value)
                case aast.CommandResult.STOP:
                    break

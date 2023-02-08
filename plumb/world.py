from collections import defaultdict
from dataclasses import dataclass, field
import shlex
import os.path
from typing import TypeVar, TYPE_CHECKING, Iterable, Self
from pathlib import Path

from .routable import Routable
from .util import optstr
from . import aast

if TYPE_CHECKING:
    import ast

T = TypeVar("T")


@dataclass
class Op:
    type: str
    args: list[str]

    requires_names: list[str] = field(default_factory=list)
    requires_op: list[Self] = field(default_factory=list)
    provides_names: list[str] = field(default_factory=list)
    provides_op: list[Self] = field(default_factory=list)

    ready_: bool = False
    executed: bool = False

    def ready(self) -> bool:
        if self.ready_:
            return True
        self.ready_ = all(op.executed for op in self.requires_op)
        return self.ready_


class World:
    def add_rsync(self, dst: str, srcs: list[str]) -> Op:
        self.rsync[dst].append(op := Op("rsync", list(srcs)))
        op.requires_names = list(srcs)
        if dst.endswith(os.path.sep):
            op.provides_names = [str(Path(dst).joinpath(Path(s).name)) for s in srcs]
        else:
            op.provides_names = [dst]
        self.add_op(op)
        return op

    def add_move(self, dst: str, src: str) -> Op:
        self.move_files[dst].append(op := Op("mv", [src]))
        op.requires_names = [src]
        self.add_op(op)
        return op

    def add_shell(self, reqs: list[str], cmd: list[str]) -> Op:
        self.shell_commands.append(op := Op("shell", list(cmd)))
        op.requires_names = list(reqs)
        self.add_op(op)
        return op

    def add_op(self, newop: Op) -> None:
        for op in self.ops:
            # todo: index ops by names rather than this ... O(N^3)-ish approach
            if any(a == b for a in newop.provides_names for b in op.requires_names):
                if newop is not op:
                    newop.requires_op.append(op)
                    op.provides.append(self)
        self.ops.append(newop)
        self.pending_ops.append(newop)

    def __init__(self):
        self.dry_run = True
        self._stat_cache: dict[str, os.stat_result] = {}
        self.mode = aast.CommandResult.NEXT_COMMAND

        self.vars = {}
        self.obj: Routable | None = None

        self.ops = []
        self.pending_ops = []

        self.rsync: defaultdict[str, list[Op]] = defaultdict(list)
        self.move_files: defaultdict[str, list[Op]] = defaultdict(list)
        self.shell_commands: list[Op] = []

    def run(self):
        # Consolidate rsync/copies to the same destination
        while self.pending_ops:
            executed_ops = list()

            # Translate ready rsyncs into shell commands
            for dest, srcs in self.rsync.items():
                goable = [s for s in srcs if s.ready() and not s.executed]
                args = [x for s in goable for x in s.args]
                cmd = ["rsync", "-vaP", *args, dest]
                for s in goable:
                    s.executed = True
                    executed_ops.append(s)
                self.add_shell(reqs=args, cmd=cmd)

            # Translate ready moves into shell commands
            for dest, srcs in self.move_files.items():
                goable = [s for s in srcs if s.ready() and not s.executed]
                args = [x for s in goable for x in s.args]
                cmd = ["mv", *args, dest]
                for s in goable:
                    s.executed = True
                    executed_ops.append(s)
                self.add_shell(reqs=args, cmd=cmd)

            # Run the accumulated external commands
            if self.dry_run:
                for cmd in self.shell_commands:
                    if not cmd.ready() or cmd.executed:
                        continue
                    print(shlex.join(cmd.args))
                    cmd.executed = True
                    executed_ops.append(cmd)
            else:
                for cmd in self.shell_commands:
                    if not cmd.ready():
                        continue
                    cmd.executed = True
                    executed_ops.append(cmd)
                    system.execute.the.command.notimplemented

            trace = self.var("debugtrace", False)
            for o in reversed(executed_ops):
                # if trace: print(o)
                self.pending_ops.remove(o)

    def stat_path(self, path: str | bytes | Path | None) -> os.stat_result | None:
        if path is None:
            return None
        assert path is not None
        if path not in self._stat_cache:
            p = optstr(path)
            if p is not None:
                self._stat_cache[p] = Path(p).stat()
        return self._stat_cache[optstr(path)]

    def next_obj(self, obj: Routable) -> None:
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
            self.set_var("dir", str(obj.wdir.joinpath(dat).parent))
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
            trace = self.var("debugtrace", False)
            match self.mode:
                case aast.CommandResult.NEXT_COMMAND:
                    if trace:
                        print("RUN", cmd, end="  ")
                    self.mode = cmd.run(self, value)
                    if trace:
                        print("->", self.mode)
                case aast.CommandResult.NEXT_RULE:
                    if isinstance(cmd, RuleCommand):
                        if trace:
                            print("RULE", cmd)
                        self.mode = cmd.run(self, value)
                case aast.CommandResult.STOP:
                    if trace and isinstance(cmd, RuleCommand):
                        print("STOP", cmd)
                    break

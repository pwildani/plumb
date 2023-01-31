from collections import defaultdict

import shlex
import os


class World:
    def __init__(self):
        self.rsync: defaultdict[str, list[str]] = defaultdict(list)
        self.dry_run = True
        self.shell_commands: list[list[str]] = []
        self.stop_routing = False
        self._stat_cache: dict[str, os.stat_result] = {}

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

    def stat_path(self, path: str) -> os.stat_result:
        if path not in self._stat_cache:
            self._stat_cache[path] = os.stat(path)
        return self._stat_cache[path]

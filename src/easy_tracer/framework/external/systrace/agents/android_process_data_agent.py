# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Tracing agent that captures friendly process and thread data (names, pids,
# tids) to enrich display in the trace viewer.
#
# NOTE:
# This repo uses the legacy systrace agent interface (SystraceAgent). The file
# was migrated down from a higher-version systrace that depended on
# tracing_agents + devil.device_utils. This implementation is refactored to
# match this repo's agent lifecycle and adb helpers (systrace.util).

import sys

from .. import systrace_agent
from .. import util


# Prefer modern ps with explicit columns, then thread ps. The importer expects
# to see two "USER ..." header lines (one for processes, one for threads).
PS_COMMAND_PROC = (
    "ps -A -o USER,PID,PPID,VSIZE,RSS,WCHAN,ADDR=PC,S,NAME,COMM"
    " && ps -AT -o USER,PID,TID,CMD"
)

# Fallback for older devices / toybox variants.
PS_COMMAND_PROC_LEGACY = "ps && ps -t"

# Identify this chunk as a process/thread dump for trace-viewer importer.
TRACE_HEADER = "PROCESS DUMP\n"


def try_create_agent(options, categories):  # pylint: disable=unused-argument
    return AndroidProcessDataAgent(options, categories)


class AndroidProcessDataAgent(systrace_agent.SystraceAgent):
    def __init__(self, options, categories):
        super(AndroidProcessDataAgent, self).__init__(options, categories)
        self._trace_data = ""
        self._expect_trace = True

    def start(self):
        # Snapshot at trace start to capture initial names.
        # self._trace_data = self._get_process_snapshot()
        pass

    def collect_result(self):
        # Snapshot at trace end to capture processes created during trace.
        self._trace_data += self._get_process_snapshot()

    def expect_trace(self):
        return self._expect_trace

    def get_trace_data(self):
        # Trace-viewer uses the header to select ProcessDataImporter.
        return TRACE_HEADER + self._trace_data

    def get_class_name(self):
        # The class name is not used by the importer selection (header is),
        # but should remain stable to keep HTML structure predictable.
        return "trace-data"

    def _get_process_snapshot(self):
        serial = getattr(self._options, "device_serial", None)

        dump, ret_code = util.run_adb_shell([PS_COMMAND_PROC], serial)
        dump = "" if dump is None else str(dump)
        dump = dump.replace("\r", "")

        # If the modern command fails (or looks clearly wrong), fall back.
        # Some old devices print a single-line error for each command.
        lines = dump.split("\n") if dump else []
        looks_like_failure = (ret_code != 0) or (len(lines) <= 2)
        if looks_like_failure:
            dump2, ret_code2 = util.run_adb_shell([PS_COMMAND_PROC_LEGACY], serial)
            dump2 = "" if dump2 is None else str(dump2)
            dump2 = dump2.replace("\r", "")
            lines2 = dump2.split("\n") if dump2 else []
            if ret_code2 != 0 or len(lines2) <= 2:
                # Don't hard-fail the whole trace; just omit process data.
                sys.stderr.write("WARNING: Unable to extract process data via ps.\n")
                return ""
            dump = dump2

        if dump and not dump.endswith("\n"):
            dump += "\n"
        return dump

# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility classes for systrace agents.

ADB operations have been consolidated into easy_tracer.framework.adb_helper.
This module retains only argument parsing utilities needed by the agent infrastructure.
"""

import argparse


class OptionParserIgnoreErrors(argparse.ArgumentParser):
    """Wrapper for ArgumentParser that ignores errors and produces no output."""

    def error(self, msg):
        pass

    def exit(self, status=0, msg=None):
        pass

    def print_usage(self, out_file=None):
        pass

    def print_help(self, out_file=None):
        pass

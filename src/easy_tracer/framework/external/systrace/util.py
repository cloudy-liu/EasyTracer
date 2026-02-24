# Copyright (c) 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import subprocess
import sys
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Default adb executable used by vendored systrace internals.
# The host adapter can override this at runtime.
ADB_EXECUTABLE = 'adb'

# Cache SDK lookup per-device to avoid redundant adb getprop calls.
_SDK_VERSION_CACHE = {}


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


def add_adb_serial(adb_command, device_serial):
    if device_serial is not None:
        adb_command.insert(1, device_serial)
        adb_command.insert(1, '-s')


def construct_adb_shell_command(shell_args, device_serial):
    adb_command = [ADB_EXECUTABLE, 'shell', ' '.join(shell_args)]
    add_adb_serial(adb_command, device_serial)
    return adb_command


def set_adb_executable(adb_path):
    global ADB_EXECUTABLE
    ADB_EXECUTABLE = adb_path or 'adb'


def run_adb_shell(shell_args, device_serial):
    """Runs "adb shell" with the given arguments.

    Args:
        shell_args: array of arguments to pass to adb shell.
        device_serial: if not empty, will add the appropriate command-line
            parameters so that adb targets the given device.
    Returns:
        A tuple containing the adb output (stdout & stderr) and the return code
        from adb.  Will exit if adb fails to start.
    """
    adb_command = construct_adb_shell_command(shell_args, device_serial)

    # Keep systrace-internal adb commands out of normal INFO logs.
    logger.debug("Systrace Internal Exec: %s", " ".join(adb_command))

    adb_output = []
    adb_return_code = 0
    try:
        kwargs = {}
        if sys.platform == 'win32':
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs['startupinfo'] = si
            kwargs['creationflags'] = getattr(
                subprocess, 'CREATE_NO_WINDOW', 0x0800)

        adb_output = subprocess.check_output(adb_command, stderr=subprocess.STDOUT,
                                             shell=False, universal_newlines=True,
                                             **kwargs)
    except OSError as error:
        # This usually means that the adb executable was not found in the path.
        print('\nThe command "%s" failed with the following error:'
              % ' '.join(adb_command), file=sys.stderr)
        print('    %s' % str(error), file=sys.stderr)
        print('Is adb in your path?', file=sys.stderr)
        adb_return_code = error.errno
        adb_output = str(error)
    except subprocess.CalledProcessError as error:
        # The process exited with an error.
        adb_return_code = error.returncode
        adb_output = error.output

    return (adb_output, adb_return_code)


def get_device_sdk_version(device_serial=None):
    """Uses adb to attempt to determine the SDK version of a running device."""
    cache_key = device_serial if device_serial else '__default__'
    if cache_key in _SDK_VERSION_CACHE:
        return _SDK_VERSION_CACHE[cache_key]

    getprop_args = ['getprop', 'ro.build.version.sdk']

    if device_serial is None:
        # Legacy fallback: parse serial from process argv.
        parser = OptionParserIgnoreErrors()
        parser.add_argument('-e', '--serial', dest='device_serial', type=str)
        options, _ = parser.parse_known_args()
        device_serial = options.device_serial

    success = False
    version = -1

    adb_output, adb_return_code = run_adb_shell(getprop_args, device_serial)

    if adb_return_code == 0:
        # ADB may print output other than the version number (e.g. it could
        # print a message about starting the ADB server).
        # Break the ADB output into white-space delimited segments.
        parsed_output = str.split(adb_output)
        if parsed_output:
            # Assume that the version number is the last thing printed by ADB.
            version_string = parsed_output[-1]
            if version_string:
                try:
                    # Try to convert the text into an integer.
                    version = int(version_string)
                except ValueError:
                    version = -1
                else:
                    success = True

    if not success:
        print('\nThe command "%s" failed with the following message:'
              % ' '.join(getprop_args), file=sys.stderr)
        print(adb_output, file=sys.stderr)
        sys.exit(1)

    _SDK_VERSION_CACHE[cache_key] = version
    return version

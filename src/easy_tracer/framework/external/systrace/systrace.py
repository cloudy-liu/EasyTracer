# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Android system-wide tracing utility.

This is a tool for capturing a trace that includes data from both userland and
the kernel.  It creates an HTML file for visualizing the trace.
"""

import importlib.resources
import importlib.util
import argparse
import os
import sys

from .agents import atrace_agent
from .agents import android_process_data_agent

# The default agent directory.
DEFAULT_AGENT_DIR = 'agents'


def parse_options(argv):
    """Parses and checks the command-line options.

    Returns:
        A tuple containing the options structure and a list of categories to
        be traced.
    """
    parser = argparse.ArgumentParser(
        description='Example: systrace -b 32768 -t 15 gfx input view sched freq'
    )
    parser.add_argument('-o', dest='output_file', help='write HTML to FILE',
                        default='trace.html', metavar='FILE')
    parser.add_argument('-t', '--time', dest='trace_time', type=int,
                        help='trace for N seconds', metavar='N')
    parser.add_argument('-b', '--buf-size', dest='trace_buf_size', type=int,
                        help='use a trace buffer size of N KB', metavar='N')
    parser.add_argument('-k', '--ktrace', dest='kfuncs', action='store',
                        help='specify a comma-separated list of kernel functions '
                        'to trace')
    parser.add_argument('-l', '--list-categories', dest='list_categories',
                        default=False, action='store_true',
                        help='list the available categories and exit')
    parser.add_argument('-a', '--app', dest='app_name', default=None, type=str,
                        action='store',
                        help='enable application-level tracing for comma-separated '
                        'list of app cmdlines')
    parser.add_argument('--no-fix-threads', dest='fix_threads', default=True,
                        action='store_false',
                        help="don't fix missing or truncated thread names")
    parser.add_argument('--no-fix-tgids', dest='fix_tgids', default=True,
                        action='store_false',
                        help='Do not run extra commands to restore missing thread '
                        'to thread group id mappings.')
    parser.add_argument('--no-fix-circular', dest='fix_circular', default=True,
                        action='store_false',
                        help="don't fix truncated circular traces")
    parser.add_argument('--no-compress', dest='compress_trace_data',
                        default=True, action='store_false',
                        help='Tell the device not to send the trace data in '
                        'compressed form.')
    parser.add_argument('--boot', dest='boot', default=False, action='store_true',
                        help='reboot the device with tracing during boot enabled. '
                        'The report is created by hitting Ctrl+C after the device '
                        'has booted up.')
    parser.add_argument('--from-file', dest='from_file', action='store',
                        help='read the trace from a file (compressed) rather than '
                        'running a live trace')
    parser.add_argument('-e', '--serial', dest='device_serial', type=str,
                        help='adb device serial number')
    parser.add_argument('--agent-dirs', dest='agent_dirs', type=str,
                        help='the directories of additional systrace agent modules.'
                        ' The directories should be comma separated, e.g., '
                        '--agent-dirs=dir1,dir2,dir3. Directory |%s| is the default'
                        ' agent directory and will always be checked.'
                        % DEFAULT_AGENT_DIR)
    parser.add_argument('categories', nargs='*', help='trace categories')

    args = parser.parse_args(argv[1:])

    if (args.trace_time is not None) and (args.trace_time <= 0):
        parser.error('the trace time must be a positive number')

    if (args.trace_buf_size is not None) and (args.trace_buf_size <= 0):
        parser.error('the trace buffer size must be a positive number')

    return (args, args.categories)


def write_trace_html(html_filename, agents):
    """Writes out a trace html file.

    Args:
        html_filename: The name of the file to write.
        agents: The systrace agents.
    """
    html_prefix = read_asset('prefix.html')
    html_suffix = read_asset('suffix.html')
    trace_viewer_html = read_asset('systrace_trace_viewer.html')

    # Open the file in text mode with explicit encoding
    with open(html_filename, 'w', encoding='utf-8') as html_file:
        html_file.write(html_prefix.replace('{{SYSTRACE_TRACE_VIEWER_HTML}}',
                                            trace_viewer_html))

        html_file.write('<!-- BEGIN TRACE -->\n')
        for a in agents:
            html_file.write('  <script class="')
            html_file.write(a.get_class_name())
            html_file.write('" type="application/text">\n')
            html_file.write(a.get_trace_data())
            html_file.write('  </script>\n')
        html_file.write('<!-- END TRACE -->\n')

        html_file.write(html_suffix)

    print('\n    wrote file://%s\n' % os.path.abspath(html_filename))


def create_agents(options, categories):
    """Create systrace agents.

    This function will search systrace agent modules in agent directories and
    create the corresponding systrace agents.
    Args:
        options: The command-line options.
        categories: The trace categories to capture.
    Returns:
        The list of systrace agents.
    """
    agents = []
    # Built-in agents are bundled as package modules (no filesystem scanning).
    for module in (android_process_data_agent, atrace_agent):
        try:
            agent = module.try_create_agent(options, categories)
        except Exception as e:
            print(f"Warning: Failed to init agent {module.__name__}: {e}", file=sys.stderr)
            continue
        if agent:
            agents.append(agent)

    # Optional: load extra agent modules from user-supplied directories.
    # This keeps compatibility with the original systrace CLI option.
    if options.agent_dirs:
        for agent_dir in options.agent_dirs.split(","):
            agent_dir = agent_dir.strip()
            if not agent_dir or not os.path.isdir(agent_dir):
                continue
            for filename in os.listdir(agent_dir):
                (module_name, ext) = os.path.splitext(filename)
                if ext != ".py" or module_name in {"__init__"}:
                    continue
                module_path = os.path.join(agent_dir, filename)
                try:
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    if spec is None or spec.loader is None:
                        continue
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                except Exception as e:
                    print(f"Warning: Failed to load agent {module_name}: {e}", file=sys.stderr)
                    continue
                if hasattr(module, "try_create_agent"):
                    agent = module.try_create_agent(options, categories)
                    if agent:
                        agents.append(agent)

    return agents


def main_impl(argv):
    """Main implementation that can be called with custom argv."""
    options, categories = parse_options(argv)
    agents = create_agents(options, categories)

    if not agents:
        dirs = DEFAULT_AGENT_DIR
        if options.agent_dirs:
            dirs += ',' + options.agent_dirs
        sys.stderr.write('No systrace agent is available in directories |%s|.\n' %
                         dirs)
        sys.exit(1)

    for a in agents:
        a.start()

    for a in agents:
        a.collect_result()
        if not a.expect_trace():
            # Nothing more to do.
            return

    # If we're only listing categories, agents have already printed the list.
    # Avoid writing an (empty) HTML trace file that pollutes the working dir and
    # also confuses callers that parse stdout.
    if options.list_categories:
        return

    write_trace_html(options.output_file, agents)


def main():
    main_impl(sys.argv)


def read_asset(filename):
    # Package data access that works in zip/pyinstaller environments.
    return (
        importlib.resources.files(__package__)
        .joinpath(filename)
        .read_text(encoding="utf-8")
    )


if __name__ == '__main__':
    main()

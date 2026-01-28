import re
import unittest
from pathlib import Path


TOOL_PATTERNS = {
    "systrace": [r"\bsystrace\b", r"run_systrace\.py", r"\batrace\b"],
    "perfetto": [r"\bperfetto\b"],
    "simpleperf": [r"\bsimpleperf\b", r"app_profiler\.py", r"report_html\.py"],
    "traceview": [r"\btraceview\b", r"\bam profile\b"],
}

# Keep in sync with existing IT coverage in tests/integration/test_e2e.py
COVERED_BY_IT = {"systrace", "perfetto", "simpleperf", "traceview", "combo"}


def _detect_tools(content: str) -> set[str]:
    tools: set[str] = set()
    for tool, patterns in TOOL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                tools.add(tool)
                break
    return tools


class TestPerfAllInOneReleaseCoverage(unittest.TestCase):
    def test_bat_files_covered_by_it(self):
        repo_root = Path(__file__).resolve().parents[3]
        release_dirs = sorted(repo_root.glob("PerfAllInOne_release_*"))

        if not release_dirs:
            self.skipTest("PerfAllInOne_release_* directory not found in repo root.")

        bat_files = []
        for release_dir in release_dirs:
            bat_files.extend(sorted(release_dir.rglob("*.bat")))

        if not bat_files:
            self.fail("No .bat files found under PerfAllInOne_release_* directories.")

        unknown_tools = []
        missing_coverage = []

        for bat_file in bat_files:
            content = bat_file.read_text(encoding="utf-8", errors="ignore")
            tools = _detect_tools(content)

            if not tools:
                unknown_tools.append(str(bat_file))
                continue

            required = {"combo"} if len(tools) > 1 else tools
            uncovered = required - COVERED_BY_IT
            if uncovered:
                missing_coverage.append(
                    f"{bat_file} -> tools={sorted(tools)} missing={sorted(uncovered)}"
                )

        if unknown_tools or missing_coverage:
            messages = []
            if unknown_tools:
                messages.append("Unrecognized bat files (no tool match):")
                messages.extend(unknown_tools)
            if missing_coverage:
                messages.append("Missing IT coverage for bat files:")
                messages.extend(missing_coverage)
            self.fail("\n".join(messages))


if __name__ == "__main__":
    unittest.main()

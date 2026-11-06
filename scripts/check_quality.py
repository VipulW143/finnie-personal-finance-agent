"""Run the entire offline test suite and enforce the configured coverage target."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main():
    (ROOT / "reports").mkdir(exist_ok=True)
    commands = [
        ["run", "-m", "unittest", "discover", "-s", "tests", "-q"],
        ["json", "--fail-under=0", "-o", "reports/coverage.json"],
        ["html", "--fail-under=0", "-d", "reports/coverage_html"],
        ["report"],
    ]
    for arguments in commands:
        subprocess.run([sys.executable, "-m", "coverage", *arguments], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()

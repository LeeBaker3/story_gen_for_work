#!/usr/bin/env python3
"""Generate an SVG coverage badge from coverage.xml.

Usage:
  python scripts/generate_coverage_badge.py            # runs pytest with coverage then builds badge
  python scripts/generate_coverage_badge.py --no-test  # just parse existing coverage.xml

Color thresholds (line coverage):
  >= 90  brightgreen
  >= 80  green
  >= 70  yellowgreen
  >= 60  yellow
  >= 50  orange
  <  50  red

Outputs:
  coverage.xml (if tests run)
  coverage_badge.svg (updated)
  Prints summary to stdout.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BADGE_PATH = ROOT / "coverage_badge.svg"
COVERAGE_XML = ROOT / "coverage.xml"

THRESHOLDS = [
    (90, "#4c1"),          # brightgreen
    (80, "#2ea44f"),       # green
    (70, "#a1cf34"),       # yellowgreen
    (60, "#dfb317"),       # yellow
    (50, "#fe7d37"),       # orange
    (0,  "#e05d44"),       # red
]


def run_tests_with_coverage(pytest_args: list[str]) -> None:
    cmd = [sys.executable, "-m", "pytest", "--cov=backend",
           "--cov-report=xml:coverage.xml"] + pytest_args
    print(f"[badge] Running tests: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=ROOT)
    if res.returncode != 0:
        print("[badge] Test run failed; badge not updated.", file=sys.stderr)
        sys.exit(res.returncode)


def parse_coverage() -> float:
    if not COVERAGE_XML.exists():
        print(
            f"[badge] coverage.xml not found at {COVERAGE_XML}", file=sys.stderr)
        sys.exit(1)
    tree = ET.parse(COVERAGE_XML)
    root = tree.getroot()
    # coverage.py XML root tag is <coverage line-rate="..." branch-rate="..." ...>
    line_rate = root.get("line-rate")
    if line_rate is None:
        # Fallback: compute from lines-covered & lines-valid attributes (if present)
        covered = root.get("lines-covered")
        valid = root.get("lines-valid")
        if covered and valid:
            try:
                pct = (int(covered) / int(valid)) * 100.0
                return pct
            except ZeroDivisionError:
                return 0.0
        print("[badge] Could not determine line coverage.", file=sys.stderr)
        sys.exit(1)
    return float(line_rate) * 100.0


def pick_color(pct: float) -> str:
    for threshold, color in THRESHOLDS:
        if pct >= threshold:
            return color
    return "#e05d44"


def build_badge_svg(pct: float, color: str) -> str:
    pct_str = f"{pct:.0f}%"
    # Dynamic width: fixed label (62) then value segment
    label = "coverage"
    value_len = len(pct_str)
    value_width = 34 + (value_len * 6)
    total_width = 62 + value_width
    svg = f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{total_width}\" height=\"20\" role=\"img\" aria-label=\"coverage:{pct_str}\"><linearGradient id=\"s\" x2=\"0\" y2=\"100%\"><stop offset=\"0\" stop-color=\"#bbb\" stop-opacity=\".1\"/><stop offset=\"1\" stop-opacity=\".1\"/></linearGradient><rect rx=\"3\" width=\"{total_width}\" height=\"20\" fill=\"#555\"/><rect rx=\"3\" x=\"62\" width=\"{value_width}\" height=\"20\" fill=\"{color}\"/><path fill=\"{color}\" d=\"M62 0h4v20h-4z\"/><rect rx=\"3\" width=\"{total_width}\" height=\"20\" fill=\"url(#s)\"/><g fill=\"#fff\" text-anchor=\"middle\" font-family=\"Verdana,Geneva,DejaVu Sans,sans-serif\" text-rendering=\"geometricPrecision\" font-size=\"110\"><text aria-hidden=\"true\" x=\"310\" y=\"150\" fill=\"#010101\" fill-opacity=\".3\" transform=\"scale(.1)\" textLength=\"620\">{label}</text><text x=\"310\" y=\"140\" transform=\"scale(.1)\" fill=\"#fff\" textLength=\"620\">{label}</text><text aria-hidden=\"true\" x=\"{(62+value_width/2)*10}\" y=\"150\" fill=\"#010101\" fill-opacity=\".3\" transform=\"scale(.1)\" textLength=\"{value_width*10}\">{pct_str}</text><text x=\"{(62+value_width/2)*10}\" y=\"140\" transform=\"scale(.1)\" fill=\"#fff\" textLength=\"{value_width*10}\">{pct_str}</text></g></svg>"""
    return svg


def write_badge(svg: str) -> None:
    BADGE_PATH.write_text(svg, encoding="utf-8")
    print(f"[badge] Wrote {BADGE_PATH.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-test", action="store_true",
                        help="Do not run pytest; just read existing coverage.xml")
    parser.add_argument("--pytest-args", nargs=argparse.REMAINDER,
                        help="Extra args passed to pytest (after --)")
    args = parser.parse_args()

    if not args.no_test:
        extra = args.pytest_args or []
        run_tests_with_coverage(extra)
    pct = parse_coverage()
    color = pick_color(pct)
    svg = build_badge_svg(pct, color)
    write_badge(svg)
    print(f"[badge] Coverage: {pct:.2f}% -> {color}")


if __name__ == "__main__":
    main()

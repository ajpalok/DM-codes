"""Compile paper/main.tex to paper/main.pdf with Tectonic and report pages, fonts and layout warnings.

    python tools/build_paper.py

Tectonic is a single program (https://tectonic-typesetting.github.io). It is looked up on the PATH and in the
per-user install folder %LOCALAPPDATA%\\Programs\\Tectonic.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"


def find_tectonic():
    found = shutil.which("tectonic")
    if found:
        return found
    candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tectonic" / "tectonic.exe"
    return str(candidate) if candidate.exists() else None


def main():
    tectonic = find_tectonic()
    if tectonic is None:
        sys.exit("Tectonic was not found. Install it, or compile paper/main.tex on Overleaf with pdfLaTeX.")
    run = subprocess.run([tectonic, "main.tex"], cwd=PAPER, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = run.stdout + run.stderr
    if run.returncode != 0:
        print(log[-3000:])
        sys.exit("compilation failed")

    warnings = sorted(set(re.findall(r"warning: (main\.tex:\d+: .*)", log)))
    overfull = [w for w in warnings if "Overfull" in w]
    print(f"compiled {PAPER / 'main.pdf'}")
    try:
        import fitz                                   # PyMuPDF, optional
        doc = fitz.open(PAPER / "main.pdf")
        fonts = sorted({f[3].split("+")[-1] for page in doc for f in page.get_fonts()})
        print(f"pages: {len(doc)} | fonts: {', '.join(fonts[:6])}{' ...' if len(fonts) > 6 else ''}")
    except ImportError:
        pass
    print(f"layout warnings: {len(warnings)} ({len(overfull)} overfull)")
    for w in overfull:
        print("  ", w)


if __name__ == "__main__":
    main()

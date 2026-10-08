"""Check that the notebook source also parses on Python 3.10 and 3.11 (Kaggle and Colab).

Python 3.12 relaxed two f-string rules. Before 3.12 an expression inside an f-string may not reuse the
string's own quote character and may not contain a backslash. This script flags both.

    python tools/check_py310.py
"""
import io
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
problems = []

for path in sorted((ROOT / "notebooks" / "parts").glob("*.py")) + sorted((ROOT / "algorithms").glob("*.py")):
    source = path.read_text(encoding="utf-8")
    quote_stack, depth = [], 0
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.FSTRING_START:
            quote_stack.append(tok.string.lstrip("rRbBfFuU")[0])
        elif tok.type == tokenize.FSTRING_END:
            quote_stack.pop()
        elif quote_stack and tok.type != tokenize.FSTRING_MIDDLE:
            # a token inside an f-string expression
            if tok.type == tokenize.STRING and tok.string.lstrip("rRbBuU")[0] == quote_stack[-1]:
                problems.append(f"{path.name}:{tok.start[0]} reuses the f-string's quote inside an expression: {tok.line.strip()[:90]}")
            if "\\" in tok.string:
                problems.append(f"{path.name}:{tok.start[0]} backslash inside an f-string expression: {tok.line.strip()[:90]}")

if problems:
    print("Not compatible with Python 3.10 / 3.11:")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("notebook source uses no f-string syntax that needs Python 3.12")

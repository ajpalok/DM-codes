"""Build notebooks/FormTrap_DM.ipynb from the cell-marked sources in notebooks/parts/.

    python tools/make_notebook.py            build the notebook and execute it (outputs embedded)
    python tools/make_notebook.py --no-run   build only
    python tools/make_notebook.py --script   also write notebooks/formtrap_dm.py (plain script, for quick runs)
"""
import os
import re
import sys
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
PARTS = sorted((ROOT / "notebooks" / "parts").glob("*.py"))
OUT = ROOT / "notebooks" / "FormTrap_DM.ipynb"


def cells(src):
    for block in re.split(r"^# %%", src, flags=re.M)[1:]:
        head, _, body = block.partition("\n")
        body = body.strip("\n")
        if "[markdown]" in head:
            yield nbformat.v4.new_markdown_cell("\n".join(line[2:] if line.startswith("# ") else line.lstrip("#")
                                                          for line in body.splitlines()))
        elif body:
            yield nbformat.v4.new_code_cell(body)


def expand_includes(source):
    """Replace each "# %include algorithms/<file>.py" line with that file's code (without its docstring).

    The algorithms live in one place, algorithms/, and the notebook still runs on its own on Colab.
    """
    def include(match):
        code = (ROOT / match.group(1)).read_text(encoding="utf-8")
        code = re.sub(r'\A"""[\s\S]*?"""\n', "", code).strip("\n")
        return f"# ---- {match.group(1)} ----\n{code}"
    return re.sub(r"^# %include (\S+)$", include, source, flags=re.M)


def main():
    source = expand_includes("\n\n".join(p.read_text(encoding="utf-8") for p in PARTS))
    if "--script" in sys.argv:
        (ROOT / "notebooks" / "formtrap_dm.py").write_text(source, encoding="utf-8")
    nb = nbformat.v4.new_notebook(cells=list(cells(source)))
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    if "--no-run" not in sys.argv:
        from nbclient import NotebookClient
        os.environ.setdefault("FORMTRAP_ARTIFACTS", str(ROOT / "artifacts"))
        NotebookClient(nb, timeout=3600, kernel_name="python3",
                       resources={"metadata": {"path": str(ROOT / "notebooks")}}).execute()
    nbformat.write(nb, OUT)
    print(f"wrote {OUT} ({len(nb.cells)} cells)")


if __name__ == "__main__":
    main()

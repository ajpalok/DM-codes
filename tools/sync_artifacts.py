"""Copy the notebook's exports to the places that use them.

    artifacts/*.joblib, *.json  -> software/ml_service/artifacts/
    src/features.py             -> software/ml_service/features.py
    artifacts/figures/*.png     -> paper/figures/

Run after tools/make_notebook.py.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
SERVICE = ROOT / "software" / "ml_service"
PAPER_FIGS = ROOT / "paper" / "figures"


def main():
    (SERVICE / "artifacts").mkdir(parents=True, exist_ok=True)
    PAPER_FIGS.mkdir(parents=True, exist_ok=True)
    for f in sorted(ART.glob("*.joblib")) + sorted(ART.glob("*.json")):
        shutil.copy2(f, SERVICE / "artifacts" / f.name)
    shutil.copy2(ROOT / "src" / "features.py", SERVICE / "features.py")
    for f in sorted((ART / "figures").glob("*.png")):
        shutil.copy2(f, PAPER_FIGS / f.name)
    print("service artifacts:", sorted(p.name for p in (SERVICE / "artifacts").iterdir()))
    print("paper figures:", len(list(PAPER_FIGS.glob("*.png"))))


if __name__ == "__main__":
    main()

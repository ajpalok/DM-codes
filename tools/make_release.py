"""Assemble what gets shown or uploaded into release/.

    release/FormTrap_DM.ipynb       the executed notebook (open it in Colab)
    release/formtrap_dataset.zip    the dataset in one archive (Colab upload, when GitHub is not used)
    release/dataset/                the dataset files (the same files as data/prepared/, for a gist or Kaggle)
    release/kaggle/                 metadata for a later Kaggle upload

Nothing from data/raw/ is copied: the raw export contains names, e-mail addresses and phone numbers.
"""
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREPARED = ROOT / "data" / "prepared"
RELEASE = ROOT / "release"
DATASET_FILES = ["formtrap_spam_clean.csv", "formtrap_features.csv", "formtrap_spam_ham_merged.csv",
                 "external_sms_spam_check.csv", "legit_contact_form_holdout.csv", "prep_log.json", "README.md"]
DATASET_SLUG = "formtrap-contact-form-spam"


def main():
    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    dataset, kaggle = RELEASE / "dataset", RELEASE / "kaggle"
    dataset.mkdir(parents=True)
    kaggle.mkdir(parents=True)

    for name in DATASET_FILES:
        shutil.copy2(PREPARED / name, dataset / name)
    shutil.copy2(ROOT / "notebooks" / "FormTrap_DM.ipynb", RELEASE / "FormTrap_DM.ipynb")

    with zipfile.ZipFile(RELEASE / "formtrap_dataset.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in DATASET_FILES:
            archive.write(PREPARED / name, name)

    shutil.copy2(PREPARED / "dataset-metadata.json", kaggle / "dataset-metadata.json")
    (kaggle / "kernel-metadata.json").write_text(json.dumps({
        "id": "KAGGLE_USERNAME/formtrap-dm-mining-contact-form-spam",
        "title": "FormTrap-DM: Mining Contact-Form Spam",
        "code_file": "FormTrap_DM.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": False,
        "enable_internet": False,
        "dataset_sources": [f"KAGGLE_USERNAME/{DATASET_SLUG}"],
    }, indent=2), encoding="utf-8")

    for path in sorted(RELEASE.rglob("*")):
        if path.is_file():
            print(f"{path.relative_to(ROOT).as_posix():<54} {path.stat().st_size / 1024:>9,.0f} KB")


if __name__ == "__main__":
    main()

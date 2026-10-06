# FormTrap-DM

Data mining on five years of spam received by one website contact form, and the software that uses the result.

## What is here

| Folder | Content |
| --- | --- |
| `data/prepared/` | The cleaned, anonymized dataset (CSV files, dataset card, row counts of each cleaning step) |
| `data/raw/` | The original export. **Contains names, e-mail addresses and phone numbers. Never publish it.** |
| `data/external/` | SMS Spam Collection (UCI, CC BY 4.0), source of the legitimate messages |
| `notebooks/FormTrap_DM.ipynb` | The analysis, executed, with outputs. Runs unchanged on Kaggle and Colab |
| `notebooks/parts/` | The notebook's source, one cell-marked Python file per group of sections |
| `src/` | `prepare_dataset.py` (cleaning, anonymization, features) and `features.py` (shared with the software) |
| `artifacts/` | What the notebook exports: models, metrics, campaign profiles, rules, figures |
| `software/` | FormTrap: PHP + MySQL honeypot form, Python scoring service, mining dashboard. See `software/docs/DATA_MINING.md` |
| `paper/` | IEEE conference paper (`main.tex`, `main.pdf`, `IEEEtran.cls`, `figures/`) |
| `release/` | The executed notebook, the dataset as a zip and as files, and Kaggle metadata |
| `tools/` | Build scripts, and `dev.mjs`, which starts the whole system |
| `package.json`, `dev.bat` | The commands listed under "Run it" |
| `OLD/` | The earlier project, untouched |

## Run it

One command starts the whole system (it needs Node.js, PHP 8, Python 3.10+ and a running MySQL server):

```bash
npm run dev
```

It checks the requirements, creates the database, tables and rules if they are missing, starts the scoring
service and the web application, and prints the addresses. On a first run it also loads the dataset history so
the dashboards have something to show. Press Ctrl+C to stop. On Windows you can double-click `dev.bat` instead,
which also opens the browser.

| Command | What it does |
| --- | --- |
| `npm run dev` | Start everything: database check, scoring service (port 5055), web application (port 8090) |
| `npm run dev:open` | The same, and open the form and the data-mining view in the browser |
| `npm run dev:check` | Start everything, confirm it answers, stop again |
| `npm run stop` | Stop a scoring service and web application left running by an earlier start |
| `npm test` | The eight component tests of the software |
| `npm run setup` | Only create the database, tables and rules |
| `npm run import` | Load the dataset history into the database (the scoring service must be running) |
| `npm run data` | Rebuild the prepared dataset from the raw export |
| `npm run notebook` | Execute the notebook and copy its exports to the software and the paper |
| `npm run check` | Check the paper against the notebook's numbers, and the notebook source for Python 3.10 |
| `npm run paper` | Compile `paper/main.pdf` |
| `npm run release` | Rebuild `release/` |
| `npm run build` | The whole pipeline: data, notebook, checks, paper, release |

No `npm install` is needed; the scripts use nothing outside Node itself.

## What the notebook covers

| Section | Topic | Type of learning |
| --- | --- | --- |
| 1 | Data understanding, quality report, audit of the label | - |
| 2 | Preprocessing: redundancy, feature creation, discretization, normalization, standardization, one-hot encoding | - |
| 3 | Euclidean, Minkowski, SMC, Jaccard, cosine | descriptive |
| 4 | OLAP: roll-up, drill-down, slice, dice | descriptive |
| 5 | Apriori association rules | unsupervised |
| 6 | PCA | unsupervised |
| 7 | K-means, K-medoids, EM (Gaussian mixture) | unsupervised |
| 8 | Task A, honeypot evasion: Naive Bayes, logistic regression, decision tree (ID3 / C4.5 criteria), KNN, Mahalanobis, perceptron, MLP | supervised |
| 9 | Task B, spam vs legitimate: the same models on text, with out-of-corpus checks | supervised |
| 10 | Which algorithm suits which task | - |
| 11 | Linear and polynomial regression (trend) | supervised |
| 12 | Export for the software and the paper | - |

Each algorithm section has five parts: what it is, type of learning, why it is needed here, implementation,
analysis of results. Most algorithms are also written from scratch and checked against the library.

## Reproduce

```bash
pip install pandas numpy scipy scikit-learn matplotlib openpyxl mlxtend nbformat nbclient ipykernel flask joblib

python src/prepare_dataset.py     # data/raw -> data/prepared, with a PII scan
python tools/make_notebook.py     # builds and executes the notebook (about 6 minutes); writes artifacts/
python tools/sync_artifacts.py    # models -> software/ml_service/artifacts, figures -> paper/figures
python tools/check_paper.py       # LaTeX structure, citations, and every table value against metrics.json
python tools/check_py310.py       # the notebook source also parses on Python 3.10 / 3.11 (Kaggle, Colab)
python tools/make_release.py      # release/: notebook, dataset zip, dataset files
tectonic paper/main.tex           # paper/main.pdf
```

## Show it on Google Colab

The notebook downloads the dataset by itself from raw GitHub links, so nothing has to be uploaded by hand.

**One-time setup: put the project on GitHub.**

1. On github.com create an empty **public** repository named `FormTrap-DM` (raw links only work for public
   repositories).
2. In this folder:

   ```bash
   git init -b main
   git add .
   git commit -m "FormTrap-DM: dataset, notebook, software and paper"
   git remote add origin https://github.com/ajpalok/FormTrap-DM.git
   git push -u origin main
   ```

   `.gitignore` keeps the raw export (`data/raw/`, `OLD/`), the course slides and the planning notes out of the
   repository. Check `git status` before the first commit.

**Then, every time:**

1. Open
   `https://colab.research.google.com/github/ajpalok/FormTrap-DM/blob/main/notebooks/FormTrap_DM.ipynb`
   (or upload `release/FormTrap_DM.ipynb` to Colab).
2. *Runtime > Run all*. The first code cell fetches the six dataset files from
   `https://raw.githubusercontent.com/ajpalok/FormTrap-DM/main/data/prepared/`.

If the repository has another name or owner, change one line in the first code cell:

```python
DATA_URL = "https://raw.githubusercontent.com/<user>/<repository>/main/data/prepared"
```

A gist works too: add the files of `release/dataset/` to a gist and use
`https://gist.githubusercontent.com/<user>/<gist id>/raw` as `DATA_URL`.

If the download fails (no repository yet, or no network), the notebook falls back to asking for
`release/formtrap_dataset.zip` on Colab.

The saved outputs are from a local run (Python 3.13, scikit-learn 1.8, pandas 3.0). The code avoids
version-specific features and `tools/check_py310.py` confirms it uses no syntax newer than Python 3.10, but it
has not been run on Colab; numbers can differ slightly there.

## Kaggle (optional, later)

`release/kaggle/` holds the two metadata files. Replace `KAGGLE_USERNAME`, upload the files of
`release/dataset/` as a dataset, import `release/FormTrap_DM.ipynb` as a notebook and attach the dataset. The
notebook finds data under `/kaggle/input/` by itself.

## Paper

`paper/main.pdf` is built from `paper/main.tex` with Tectonic, which is installed for your user account
(`%LOCALAPPDATA%\Programs\Tectonic`, on your PATH in new terminals):

```bash
cd paper
tectonic main.tex
```

The same folder also compiles on Overleaf with pdfLaTeX. All numbers in the paper come from
`artifacts/metrics.json`; `tools/check_paper.py` verifies the tables.

## Software

See `software/README.md` and `software/docs/DATA_MINING.md`. In short: create the database, start
`python ml_service/app.py`, start `php -S 127.0.0.1:8090` in `software/`, open `mining.php`.

"""Static checks for paper/main.tex: balanced braces and environments, citations, references, figure files,
and every number in the results tables against artifacts/metrics.json.

    python tools/check_paper.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tex = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
metrics = json.loads((ROOT / "artifacts" / "metrics.json").read_text(encoding="utf-8"))
problems = []

body = re.sub(r"(?<!\\)%.*", "", tex)
if body.count("{") != body.count("}"):
    problems.append(f"unbalanced braces: {body.count('{')} open, {body.count('}')} close")

stack = []
for kind, name in re.findall(r"\\(begin|end)\{(\w+\*?)\}", body):
    if kind == "begin":
        stack.append(name)
    elif not stack or stack.pop() != name:
        problems.append(f"environment mismatch at \\end{{{name}}}")
if stack:
    problems.append(f"unclosed environments: {stack}")

cites = {k.strip() for group in re.findall(r"\\cite\{([^}]*)\}", body) for k in group.split(",")}
bibs = set(re.findall(r"\\bibitem\{([^}]*)\}", body))
if cites - bibs:
    problems.append(f"undefined citations: {sorted(cites - bibs)}")
if bibs - cites:
    problems.append(f"bibliography entries never cited: {sorted(bibs - cites)}")

labels, refs = set(re.findall(r"\\label\{([^}]*)\}", body)), set(re.findall(r"\\ref\{([^}]*)\}", body))
if refs - labels:
    problems.append(f"undefined references: {sorted(refs - labels)}")
if labels - refs:
    problems.append(f"labels never referenced: {sorted(labels - refs)}")

for fig in re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]*)\}", body):
    if not (ROOT / "paper" / "figures" / fig).exists():
        problems.append(f"missing figure file: {fig}")

prose = re.sub(r"\\begin\{(tabular|align)\}.*?\\end\{\1\}", "", body, flags=re.S)
if re.search(r"(?<!\\)&", prose):
    problems.append("unescaped & outside a table")
if re.search(r"(?<!\\)#", body):
    problems.append("unescaped #")


def expect(label, value, digits=3):
    """The value, rounded as printed, must appear in the paper."""
    shown = f"{value:.{digits}f}"
    if shown not in tex:
        problems.append(f"{label}: {shown} not found in the paper")


task_a_names = {"Naive Bayes": "Naive Bayes", "Logistic regression": "Logistic regression", "Decision tree": "Decision tree",
                "KNN": "KNN", "Mahalanobis (PCA)": "Mahalanobis", "Perceptron": "Perceptron",
                "MLP (one hidden layer)": "MLP", "Baseline: rule 'has a URL'": "URL rule"}
for split in ("cv", "time_split"):
    for row in metrics["task_a"][split]:
        if row["model"] in task_a_names:
            expect(f"Task A {split} {row['model']} balanced accuracy", row["balanced_acc"])
            expect(f"Task A {split} {row['model']} AUC", row["auc"])

cross = {r["model"]: r for r in metrics["task_b"]["cross_source"]}
for row in metrics["task_b"]["cv"]:
    if row["model"].startswith("Baseline: majority"):
        continue
    for key in ("balanced_acc", "f1", "auc"):
        expect(f"Task B {row['model']} {key}", row[key])
    if row["model"] in cross:
        expect(f"Task B {row['model']} same-source AUC", cross[row["model"]]["same-source AUC"])

for row in metrics["tree_root"]["table"]:
    if row["attribute"] in ("template id (almost unique)", "length bin", "url bin", "name is joined",
                            "e-mail domain (many values)", "money keyword"):
        expect(f"root split {row['attribute']} gain", row["information gain"])
        expect(f"root split {row['attribute']} gain ratio", row["gain ratio"])

for rule in metrics["apriori"]["top_filled"][:1] + metrics["apriori"]["top_empty"][1:2]:
    expect(f"rule {rule['antecedent']} confidence", rule["confidence"], 2)
    expect(f"rule {rule['antecedent']} lift", rule["lift"], 2)

for label, value in [("window rows", metrics["window"]["rows"]), ("labelled rows", metrics["task_a"]["rows"]),
                     ("frequent itemsets", metrics["apriori"]["frequent_itemsets"]), ("rules", metrics["apriori"]["rules"]),
                     ("test rows", metrics["task_a"]["test_rows"]), ("templates without vocabulary", metrics["clustering"]["templates_no_vocabulary"])]:
    if f"{value:,}" not in tex:
        problems.append(f"{label}: {value:,} not found in the paper")

words = len(re.findall(r"[A-Za-z]{2,}", re.sub(r"\\[a-zA-Z]+", " ", prose.split("\\begin{thebibliography}")[0])))
print(f"body text: about {words:,} words | citations: {len(cites)} | references: {len(bibs)} | figures: {len(re.findall('includegraphics', body))}")
if problems:
    print("PROBLEMS:")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("paper checks passed: structure is consistent and every table value matches artifacts/metrics.json")

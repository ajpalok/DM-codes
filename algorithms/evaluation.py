"""Classification metrics from the confusion matrix: accuracy, precision, recall, specificity, F1, balanced accuracy.

Used to score every classifier.
"""

def confusion_counts(y_true, y_pred):
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    return tp, fn, fp, tn


def metrics_from_counts(tp, fn, fp, tn):
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"accuracy": (tp + tn) / (tp + fn + fp + tn), "precision": precision, "recall": recall,
            "specificity": specificity, "f1": f1, "balanced_acc": (recall + specificity) / 2}

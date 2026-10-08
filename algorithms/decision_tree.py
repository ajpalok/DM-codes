"""Split criteria of decision trees: entropy, information gain (ID3), split information and gain ratio (C4.5).

Type: supervised learning (classification).
"""
import numpy as np


def entropy_of(labels):
    _, counts = np.unique(labels, return_counts=True)
    p = counts / counts.sum()
    return float(-(p * np.log2(p)).sum())


def split_measures(attribute, labels):
    values, counts = np.unique(attribute, return_counts=True)
    weights = counts / counts.sum()
    after = sum(w * entropy_of(labels[attribute == v]) for v, w in zip(values, weights))
    gain = entropy_of(labels) - after
    split_info = float(-(weights * np.log2(weights)).sum())
    return {"distinct values": len(values), "information gain": gain, "split information": split_info,
            "gain ratio": gain / split_info if split_info else 0.0}

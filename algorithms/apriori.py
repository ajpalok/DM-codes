"""Apriori: frequent itemsets and association rules.

Type: unsupervised learning.
apriori(M, min_support): join frequent (k-1)-itemsets into candidates, prune those with an infrequent subset.
make_rules(support, min_confidence): rules A -> B with support, confidence and lift.
"""
import itertools

import numpy as np
import pandas as pd


def apriori(M, min_support):
    """Frequent itemsets of a boolean transaction matrix: {frozenset(item indices): support}."""
    support = {}
    level = []
    for j in range(M.shape[1]):                                   # L1
        s = M[:, j].mean()
        if s >= min_support:
            support[frozenset([j])] = s
            level.append(frozenset([j]))
    k = 2
    while level:
        prev = set(level)
        candidates = {a | b for a in level for b in level if len(a | b) == k}                     # join
        candidates = [c for c in candidates
                      if all(frozenset(sub) in prev for sub in itertools.combinations(c, k - 1))]  # prune
        level = []
        for c in candidates:
            s = M[:, sorted(c)].all(axis=1).mean()                # one pass over the transactions
            if s >= min_support:
                support[c] = s
                level.append(c)
        k += 1
    return support


def make_rules(support, min_confidence):
    """All rules A -> B with A and B a split of a frequent itemset."""
    rows = []
    for itemset, s in support.items():
        for r in range(1, len(itemset)):
            for ante in map(frozenset, itertools.combinations(itemset, r)):
                cons = itemset - ante
                conf = s / support[ante]
                if conf >= min_confidence:
                    rows.append({"antecedent": ante, "consequent": cons, "support": s, "confidence": conf,
                                 "lift": conf / support[cons]})
    return pd.DataFrame(rows)

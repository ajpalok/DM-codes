"""Perceptron learning rule: w <- w + eta (target - output) x, one pattern at a time.

Type: supervised learning (classification), linear.
"""
import numpy as np


def perceptron_train(X, y, epochs=20, eta=1.0):
    w, b = np.zeros(X.shape[1]), 0.0
    errors = []
    for _ in range(epochs):
        wrong = 0
        for x, target in zip(X, y):
            output = int(w @ x + b > 0)                # forward pass with a step activation
            delta = target - output                    # 0 if correct, +1 or -1 if wrong
            if delta:
                w += eta * delta * x                   # weight update
                b += eta * delta                       # bias update
                wrong += 1
        errors.append(wrong)
    return w, b, errors

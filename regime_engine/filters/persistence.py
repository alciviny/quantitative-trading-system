import pandas as pd
import logging

def majority_filter(labels, window=5):
    s = pd.Series(labels)
    return s.rolling(window, min_periods=1).apply(
        lambda x: x.mode()[0] if len(x.mode()) > 0 else None
    )

def min_persistence_filter(labels, min_len=2, max_iter=100):
    labels = pd.Series(labels)
    filtered = labels.copy()
    changed = True
    iter_count = 0
    while changed:
        changed = False
        prev_label, count = labels.iloc[0], 1
        for i in range(1, len(labels)):
            if labels.iloc[i] == prev_label:
                count += 1
            else:
                if count < min_len:
                    filtered.iloc[i - count:i] = labels.iloc[i]
                    changed = True
                count = 1
                prev_label = labels.iloc[i]
        if count < min_len:
            filtered.iloc[len(labels) - count:] = prev_label
            changed = True
        labels = filtered.copy()
        iter_count += 1
        logging.info(f'min_persistence_filter: iteração {iter_count}, changed={changed}')
        if iter_count >= max_iter:
            logging.warning(f'min_persistence_filter atingiu o limite de {max_iter} iterações. Saindo do loop para evitar travamento.')
            break
    return filtered

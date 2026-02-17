"""
Módulo de validação quantitativa de regimes.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score

def validate_regimes(df, stress_periods):
    # Exemplo: calcula métricas simples
    # (Adapte para incluir lag, falsos alarmes, ROC-AUC, etc)
    real_stress = df['realized_volatility'] > df['realized_volatility'].quantile(0.9)
    pred_stress = df['regime'] == df['regime'].max()
    precision = precision_score(real_stress, pred_stress)
    recall = recall_score(real_stress, pred_stress)
    f1 = f1_score(real_stress, pred_stress)
    return {'precision': precision, 'recall': recall, 'f1': f1}

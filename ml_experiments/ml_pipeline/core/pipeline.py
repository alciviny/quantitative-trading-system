import pandas as pd
from ml_pipeline.utils.preprocessing import generate_signal, select_features
from ml_pipeline.core.modeling import train_ensemble, evaluate_model
import os
import json

def run_full_pipeline(data_path, output_dir, n_dias_futuro=5, threshold_compra=0.05, threshold_venda=-0.10, random_state=42):
    df = pd.read_csv(data_path)
    df = generate_signal(df, n_dias_futuro, threshold_compra, threshold_venda)
    features = select_features(df)
    target = 'SIGNAL'
    split_idx = int(len(df) * 0.8)
    X = df[features].fillna(0)
    y = df[target]
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    model = train_ensemble(X_train, y_train, random_state=random_state)
    report, cm, y_pred = evaluate_model(model, X_test, y_test)
    os.makedirs(output_dir, exist_ok=True)
    result = {
        'acuracia': report['accuracy'],
        'f1_macro': report['macro avg']['f1-score'],
        'f1_weighted': report['weighted avg']['f1-score'],
        'support': len(y_test),
        'relatorio': report,
        'matriz_confusao': cm.tolist()
    }
    with open(os.path.join(output_dir, 'relatorio.json'), 'w') as f:
        json.dump(result, f, indent=2)
    return result

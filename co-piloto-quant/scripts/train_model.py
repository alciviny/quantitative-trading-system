import sys
import os
import pandas as pd
import numpy as np
import joblib
import logging
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score
)
from sklearn.inspection import permutation_importance

# =========================
# Configuração
# =========================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("Trainer")

DATA_DIR = 'data/ml_ready'
MODEL_DIR = 'models'
os.makedirs(MODEL_DIR, exist_ok=True)

RANDOM_STATE = 42
PROB_THRESHOLD = 0.60


# =========================
# Load Dataset
# =========================
def load_dataset():
    logger.info("Carregando dataset...")
    try:
        df = pd.read_parquet(DATA_DIR)
        df = df.dropna()
        logger.info(f"Dataset: {df.shape[0]} linhas | {df.shape[1]} colunas")
        return df
    except Exception as e:
        logger.error(f"Erro ao carregar dados: {e}")
        return None


# =========================
# Walk-forward split
# =========================
def temporal_split(df, split_ratio=0.8):
    split_point = int(len(df) * split_ratio)
    train = df.iloc[:split_point]
    test = df.iloc[split_point:]
    return train, test


# =========================
# Training Pipeline
# =========================
def train_oracle():
    df = load_dataset()
    if df is None:
        return

    # Ordenação temporal (CRÍTICO)
    df = df.sort_values(by='data_pregao')

    target = 'target_class_5d'

    features = [
        c for c in df.columns
        if c not in [
            'ticker',
            'data_pregao',
            'target_ret_5d',
            'target_logret_5d',
            'target_class_5d'
        ]
    ]

    # Split temporal
    df_train, df_test = temporal_split(df)

    X_train, y_train = df_train[features], df_train[target]
    X_test, y_test = df_test[features], df_test[target]

    logger.info(f"Treino até {df_train['data_pregao'].iloc[-1]}")
    logger.info(f"Testando em dados futuros: {len(X_test)} registros")

    # =========================
    # Modelo (Ajustado para Agressividade Controlada)
    # =========================
    model = RandomForestClassifier(
        n_estimators=500,        # Mais árvores para diluir o risco
        max_depth=10,            # Aumentamos a profundidade (era 6) para ele aprender nuances
        min_samples_leaf=20,     # Reduzimos a exigência (era 50) para ele aceitar mais padrões
        class_weight="balanced", # O PULO DO GATO: Obriga o modelo a dar atenção aos sinais de compra
        n_jobs=-1,
        random_state=RANDOM_STATE
    )

    logger.info("Treinando modelo...")
    model.fit(X_train, y_train)

    # =========================
    # Avaliação
    # =========================
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print("\n" + "=" * 70)
    print("📊 PERFORMANCE — DADOS OUT-OF-SAMPLE")
    print("=" * 70)
    print(classification_report(y_test, y_pred))

    print("Matriz de Confusão:")
    print(confusion_matrix(y_test, y_pred))

    # Distribuição de sinais
    pct_positive = (y_prob > PROB_THRESHOLD).mean()
    logger.info(f"Sinais > {PROB_THRESHOLD:.0%}: {pct_positive:.1%} do período")

    # =========================
    # Sniper Mode
    # =========================
    sniper = pd.DataFrame({
        'real': y_test,
        'prob': y_prob
    })

    sniper = sniper[sniper['prob'] >= PROB_THRESHOLD]

    if len(sniper):
        win_rate = sniper['real'].mean()
        precision = precision_score(sniper['real'], np.ones(len(sniper)))

        print("\n🎯 SNIPER MODE ATIVO")
        print(f"Trades: {len(sniper)}")
        print(f"Win Rate: {win_rate:.1%}")
        print(f"Precision (classe 1): {precision:.1%}")
    else:
        print("\n⚠️ Nenhum trade com alta confiança no teste.")

    # =========================
    # Importância REAL (Permutation)
    # =========================
    logger.info("Calculando importância das features (Permutation)")

    perm = permutation_importance(
        model,
        X_test,
        y_test,
        n_repeats=10,
        random_state=RANDOM_STATE,
        n_jobs=-1
    )

    importance_df = (
        pd.DataFrame({
            'feature': features,
            'importance': perm.importances_mean
        })
        .sort_values(by='importance', ascending=False)
    )

    print("\n" + "=" * 70)
    print("🏆 TOP INDICADORES (IMPORTÂNCIA REAL)")
    print("=" * 70)
    print(importance_df.head(15).to_string(index=False))

    # =========================
    # Persistência
    # =========================
    joblib.dump(model, os.path.join(MODEL_DIR, 'market_brain_rf.joblib'))
    joblib.dump(features, os.path.join(MODEL_DIR, 'features_list.joblib'))
    joblib.dump(importance_df, os.path.join(MODEL_DIR, 'feature_importance.joblib'))

    logger.info("✅ Modelo e metadados salvos com sucesso.")


if __name__ == "__main__":
    train_oracle()

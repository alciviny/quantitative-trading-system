"""
Script: detect_market_regimes_hmm.py
Pipeline para detecção de regimes de mercado usando HMM (diário).
"""

import pandas as pd
import numpy as np
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler
import joblib
import warnings
warnings.filterwarnings('ignore')
import os
from pathlib import Path


# Função para rodar o regime detection para um arquivo enriched

def run_regime_detection_for_file(enriched_path, output_dir):
    import pandas as pd
    import numpy as np
    from hmmlearn.hmm import GaussianHMM
    from sklearn.preprocessing import StandardScaler
    import joblib
    import warnings
    warnings.filterwarnings('ignore')

    data = pd.read_parquet(enriched_path)

    # 2. Adicionar returns
    if 'returns' not in data.columns:
        data['returns'] = data['close'].pct_change()

    # 3. Selecionar features estruturais + returns
    features = [
        'realized_volatility',
        'volatility_of_volatility',
        'rolling_trend_strength',
        'drift_t_stat',
        'efficiency_ratio',
        'hurst',
        'market_entropy',
        'returns',
    ]
    data = data.dropna(subset=features)
    X = data[features]

    # 4. Split temporal (70% treino, 30% teste)
    train_size = int(len(X) * 0.7)
    X_train = X.iloc[:train_size]
    X_test = X.iloc[train_size:]

    # 5. Normalização (fit só no treino)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 6. Seleção do número de regimes (testa 2 a 5) usando BIC correto e covariância diagonal
    def compute_bic(model, X_scaled, n_states):
        log_likelihood = model.score(X_scaled)
        n_features = X_scaled.shape[1]
        n_params = (
            n_states - 1 +                       # startprob
            n_states * (n_states - 1) +          # transition matrix
            n_states * n_features +              # means
            n_states * n_features                # diag covariances
        )
        bic = -2 * log_likelihood + n_params * np.log(len(X_scaled))
        return bic

    best_bic = np.inf
    best_model = None
    best_n = None
    for n_states in range(2, 6):
        model = GaussianHMM(n_components=n_states, covariance_type='diag', n_iter=1000, random_state=42)
        model.fit(X_train_scaled)
        bic = compute_bic(model, X_train_scaled, n_states)
        if bic < best_bic:
            best_bic = bic
            best_model = model
            best_n = n_states

    print(f'Melhor número de regimes: {best_n} (BIC={best_bic:.2f})')

    # 7. Rolling training (3 anos treino, 3 meses teste)
    window_train = 756  # 3 anos de pregão (~252 dias/ano)
    window_test = 63    # 3 meses (~21 dias/mês)
    regimes_full = np.full(len(X), np.nan)
    probs_full = np.full((len(X), best_n), np.nan)
    for start in range(0, len(X) - window_train - window_test + 1, window_test):
        end_train = start + window_train
        end_test = end_train + window_test
        if end_test > len(X):
            break
        X_train_win = X.iloc[start:end_train]
        X_test_win = X.iloc[end_train:end_test]
        scaler_win = StandardScaler()
        X_train_win_scaled = scaler_win.fit_transform(X_train_win)
        X_test_win_scaled = scaler_win.transform(X_test_win)
        model_win = GaussianHMM(n_components=best_n, covariance_type='diag', n_iter=1000, random_state=42)
        model_win.fit(X_train_win_scaled)
        regimes_win = model_win.predict(X_test_win_scaled)
        regimes_full[end_train:end_test] = regimes_win
        probs_win = model_win.predict_proba(X_test_win_scaled)
        probs_full[end_train:end_test, :] = probs_win

    # 8. Preencher início com modelo global (caso rolling não cubra tudo)
    if np.isnan(regimes_full).any():
        X_start = X.iloc[:window_train]
        scaler_start = StandardScaler()
        X_start_scaled = scaler_start.fit_transform(X_start)
        model_start = GaussianHMM(n_components=best_n, covariance_type='diag', n_iter=1000, random_state=42)
        model_start.fit(X_start_scaled)
        regimes_start = model_start.predict(X_start_scaled)
        regimes_full[:window_train] = regimes_start
        probs_start = model_start.predict_proba(X_start_scaled)
        probs_full[:window_train, :] = probs_start

    data = data.copy()
    data['regime'] = regimes_full.astype(int)
    for i in range(best_n):
        data[f'regime_prob_{i}'] = probs_full[:, i]

    # 9. Persistência média dos regimes
    expected_duration = 1 / (1 - np.diag(best_model.transmat_))
    print('Persistência média dos regimes (dias):', expected_duration)

    # 10. Salvar resultados
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{enriched_path.stem.replace('_processed','')}_regimes_hmm.parquet"
    data.to_parquet(output_path)
    joblib.dump(best_model, output_dir / f"{enriched_path.stem.replace('_processed','')}_hmm_model.joblib")
    joblib.dump(scaler, output_dir / f"{enriched_path.stem.replace('_processed','')}_hmm_scaler.joblib")
    print(f"Regimes salvos para {enriched_path.name} em {output_path}")

if __name__ == "__main__":
    features_dir = Path(__file__).parent.parent / "data" / "processed"
    output_dir = Path(__file__).parent.parent / "data" / "results"
    processed_files = list(features_dir.glob("*_processed.parquet"))
    for processed_path in processed_files:
        try:
            run_regime_detection_for_file(processed_path, output_dir)
        except Exception as e:
            print(f"Erro ao processar {processed_path.name}: {e}")

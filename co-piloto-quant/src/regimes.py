"""
Módulo de detecção de regimes de mercado.
"""
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler

def detect_regimes(df, features, n_states=2, window_train=756, window_test=63):
    X = df[features].dropna()
    regimes_full = np.full(len(df), np.nan)
    probs_full = np.full((len(df), n_states), np.nan)
    for start in range(0, len(X) - window_train - window_test + 1, window_test):
        end_train = start + window_train
        end_test = end_train + window_test
        if end_test > len(X):
            break
        X_train = X.iloc[start:end_train]
        X_test = X.iloc[end_train:end_test]
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        model = GaussianHMM(n_components=n_states, covariance_type='diag', n_iter=1000, random_state=42)
        model.fit(X_train_scaled)
        regimes = model.predict(X_test_scaled)
        regimes_full[end_train:end_test] = regimes
        probs = model.predict_proba(X_test_scaled)
        probs_full[end_train:end_test, :] = probs
    # Preencher início e final
    if np.isnan(regimes_full[:window_train]).any():
        X_start = X.iloc[:window_train]
        scaler_start = StandardScaler()
        X_start_scaled = scaler_start.fit_transform(X_start)
        model_start = GaussianHMM(n_components=n_states, covariance_type='diag', n_iter=1000, random_state=42)
        model_start.fit(X_start_scaled)
        regimes_start = model_start.predict(X_start_scaled)
        regimes_full[:window_train] = regimes_start
        probs_start = model_start.predict_proba(X_start_scaled)
        probs_full[:window_train, :] = probs_start
    if np.isnan(regimes_full).any():
        last_train_start = max(0, len(X) - window_train)
        X_last = X.iloc[last_train_start:]
        scaler_last = StandardScaler()
        X_last_scaled = scaler_last.fit_transform(X_last)
        model_last = GaussianHMM(n_components=n_states, covariance_type='diag', n_iter=1000, random_state=42)
        model_last.fit(X_last_scaled)
        nan_idx = np.where(np.isnan(regimes_full))[0]
        if len(nan_idx) > 0:
            X_nan = X.iloc[nan_idx]
            X_nan_scaled = scaler_last.transform(X_nan)
            regimes_nan = model_last.predict(X_nan_scaled)
            probs_nan = model_last.predict_proba(X_nan_scaled)
            regimes_full[nan_idx] = regimes_nan
            probs_full[nan_idx, :] = probs_nan
    df['regime'] = regimes_full
    for i in range(n_states):
        df[f'regime_prob_{i}'] = probs_full[:, i]
    return df

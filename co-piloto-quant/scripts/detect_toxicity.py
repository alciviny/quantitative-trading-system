# toxicity_forensics_pro.py
import os
import sys
import logging
from typing import Optional, Tuple, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import shap


try:
    from scipy.stats import median_abs_deviation
except ImportError:
    try:
        from scipy.stats import median_absolute_deviation as median_abs_deviation
    except ImportError:
        median_abs_deviation = None # Fallback será tratado na função
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.inspection import permutation_importance
from sklearn.metrics import classification_report
from sklearn.cluster import KMeans

# Configuração de Logs Profissional
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [FORENSIC] - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Adiciona a raiz do projeto ao path (assumindo estrutura similar à sua)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))  

# Dependências do projeto (deve existir no seu repo)
from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.analysis import calculate_indicators

# --- CONFIGURAÇÕES ---
REPORT_PATH = 'src/co_piloto_quant/data/reports/ranking_backtest.csv'
PLOTS_DIR = 'src/co_piloto_quant/data/plots'
MIN_DATA_POINTS = 200
ROLL_ZSCORE_WINDOW = 100  # para rolling zscore
TAIL_PERCENTILE = 0.05    # tail risk 5%

# -------------------------
# Utilitários / Engenharia
# -------------------------
class FeatureEngineer:
    """Responsável por extrair e calcular métricas avançadas (Alpha Factors)."""

    @staticmethod
    def calculate_slope(series: pd.Series, window: int = 50) -> float:
        """Calcula inclinação robusta (Tendência) usando polyfit na janela final."""
        clean_window = min(window, len(series))
        if clean_window < 5:
            return 0.0
        y = series.values[-clean_window:]
        x = np.arange(len(y))
        try:
            slope, _ = np.polyfit(x, y, 1)
            return float(slope)
        except Exception:
            return 0.0

    @staticmethod
    def calculate_vol_of_vol(price_series: pd.Series, window: int = 20) -> float:
        """
        Calcula Vol-of-Vol robusto usando MAD (median absolute deviation),
        menos sensível a outliers que std.
        """
        returns = price_series.pct_change().dropna()
        if len(returns) < window + 2:
            return 0.0
        vol = returns.rolling(window).std().dropna()
        if len(vol) < 2:
            return 0.0
        vol_diff = vol.diff().dropna()
        # usar median absolute deviation (MAD)
        try:
            mad = median_abs_deviation(vol_diff, scale='normal')  # SciPy v1.11+ maybe; fallback handled
        except Exception:
            # fallback manual
            mad = np.median(np.abs(vol_diff - np.median(vol_diff)))
        return float(mad) if not np.isnan(mad) else 0.0

    @staticmethod
    def get_rolling_zscore(series: pd.Series, window: int = ROLL_ZSCORE_WINDOW) -> float:
        """Z-score do último valor relativa a uma janela rolling para reduzir viés de drift."""
        if len(series) < 5:
            return 0.0
        w = min(window, len(series))
        rolling = series.iloc[-w:]
        std = rolling.std()
        if std == 0 or np.isnan(std):
            return 0.0
        return float((rolling.iloc[-1] - rolling.mean()) / (std + 1e-9))

    @staticmethod
    def tail_risk(returns: pd.Series, percentile: float = TAIL_PERCENTILE) -> float:
        """Proporção de observações abaixo do quantil (ex: 5% tail)."""
        rets = returns.dropna()
        if len(rets) < 10:
            return 0.0
        q = rets.quantile(percentile)
        return float((rets < q).mean())

    @staticmethod
    def extract(ticker: str, row_data: pd.Series) -> Optional[dict]:
        """
        Extrai features avançadas de um ativo:
         - níveis (mean, last)
         - dinâmica (slope)
         - regime relativo (rolling zscore)
         - autocorr lag1
         - vol, vol-of-vol (MAD)
         - skew/kurt/tail risk
         - liquidez log
         - return_total (target preliminar)
        """
        try:
            df_raw = load_price_data(ticker)
            if df_raw is None or df_raw.empty or len(df_raw) < MIN_DATA_POINTS:
                return None

            df_ind = calculate_indicators(df_raw)
            if df_ind is None or df_ind.empty:
                return None

            features = {'Ticker': ticker}

            # métricas mapeadas (sua naming convention)
            metrics_map = {
                'Hurst': 'Hurst_72_returns',
                'Entropy': 'Entropy_20',
                'HalfLife': 'HalfLife_60',
                'RSI': 'IFR_120'
            }

            for name, col in metrics_map.items():
                if col in df_ind.columns:
                    series = df_ind[col].dropna()
                    if len(series) > 10:
                        features[f'{name}_Mean'] = float(series.mean())
                        features[f'{name}_Last'] = float(series.iloc[-1])
                        features[f'{name}_Slope'] = FeatureEngineer.calculate_slope(series)
                        features[f'{name}_ZScore'] = FeatureEngineer.get_rolling_zscore(series)
                        # autocorr lag=1 (correto)
                        try:
                            features[f'{name}_AC1'] = float(series.autocorr(1))
                        except Exception:
                            features[f'{name}_AC1'] = 0.0

            # NOVA CAPTURA: Features Z-Score Profissionais (Vindas do analysis.py atualizado)
            z_cols = ['Entropy_Z', 'Hurst_Z', 'VolVol_Z']
            for z_col in z_cols:
                if z_col in df_ind.columns:
                    series_z = df_ind[z_col].dropna()
                    if len(series_z) > 10:
                        features[f'{z_col}_Last'] = float(series_z.iloc[-1])
                        features[f'{z_col}_Mean'] = float(series_z.mean())
                        # Max Z-Score atingido no período (foi um pico de anomalia?)
                        features[f'{z_col}_Max'] = float(series_z.max())

            # Volatilidade e Vol-of-Vol (robusto)
            if 'close' in df_ind.columns:
                close = df_ind['close']
                returns = close.pct_change().dropna()
                features['Vol_Mean'] = float(returns.rolling(20).std().mean() * 100)
                features['Vol_Last'] = float(returns.rolling(20).std().iloc[-1] * 100) if len(returns) >= 20 else 0.0
                features['VolVol_MAD'] = FeatureEngineer.calculate_vol_of_vol(close, window=20)

                # Skew, Kurtosis, Tail risk
                if len(returns) >= 10:
                    features['Skew'] = float(returns.skew())
                    # pandas has kurtosis method named kurtosis() or kurt(); use .kurtosis() for compat
                    try:
                        features['Kurtosis'] = float(returns.kurtosis())
                    except Exception:
                        features['Kurtosis'] = float(returns.kurt())
                    features['Tail_Risk_5p'] = FeatureEngineer.tail_risk(returns, percentile=TAIL_PERCENTILE)

            # Liquidez proxy (mediana de volume $)
            if 'volume' in df_ind.columns and 'close' in df_ind.columns:
                fin_vol = (df_ind['close'] * df_ind['volume']).rolling(20).median().dropna()
                if not fin_vol.empty:
                    liq_proxy = float(fin_vol.iloc[-1])
                else:
                    liq_proxy = 0.0
                features['Liquidity_Log'] = float(np.log1p(max(liq_proxy, 1e-9)))

            # Target preliminar
            features['Return_Total'] = float(row_data['Retorno Total (%)'])

            return features

        except Exception as e:
            logger.warning(f"Falha na extração de {ticker}: {e}")
            return None

# -------------------------
# Modelagem / Pipeline
# -------------------------
def remove_correlated_features(X: pd.DataFrame, threshold: float = 0.95) -> pd.DataFrame:
    """
    Remove features com correlação absoluta > threshold (mantém a primeira coluna).
    Retorna X com colunas reduzidas.
    """
    if X.shape[1] <= 1:
        return X
    corr = X.corr().abs()
    # máscara triang superior
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    to_drop = [col for col in upper.columns if any(upper[col] > threshold)]
    if to_drop:
        logger.info(f"Removendo {len(to_drop)} features altamente correlacionadas: {to_drop}")
        X = X.drop(columns=to_drop)
    return X

class ToxicityModel:
    def __init__(self):
        self.clf = RandomForestClassifier(
            n_estimators=200,
            max_depth=5,
            min_samples_leaf=4,
            random_state=42,
            class_weight='balanced',
            n_jobs=-1
        )

    def prepare_data(self, df_features: pd.DataFrame, use_clustering_labels: bool = False) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Produz X, y preparados:
         - y: usa threshold quantil (bottom 30%) por default, ou clustering se use_clustering_labels True
         - X: limpa, remove infs, aplica feature selection correlacional
        """
        df = df_features.copy()
        # opcao de cluster-based labeling (opcional)
        if use_clustering_labels:
            try:
                # kmeans com 3 clusters: assume clusters representam bom/med/ruim
                kmeans = KMeans(n_clusters=3, random_state=42)
                # usar Return_Total para clusterizar
                clusters = kmeans.fit_predict(df[['Return_Total']].values.reshape(-1, 1))
                # escolher cluster com média menor como 'falha'
                cluster_means = pd.DataFrame({'cluster': clusters, 'ret': df['Return_Total']}).groupby('cluster')['ret'].mean()
                worst_cluster = cluster_means.idxmin()
                df['is_failure'] = (clusters == worst_cluster).astype(int)
                logger.info("Labeling: cluster-based (kmeans) selecionado.")
            except Exception as e:
                logger.warning(f"Clustering labels falhou: {e}. Voltando para quantil.")
                threshold = df['Return_Total'].quantile(0.30)
                df['is_failure'] = np.where(df['Return_Total'] <= threshold, 1, 0)
                logger.info(f"Critério de Falha (fallback): Retorno <= {threshold:.2f}%")
        else:
            threshold = df['Return_Total'].quantile(0.30)
            df['is_failure'] = np.where(df['Return_Total'] <= threshold, 1, 0)
            logger.info(f"Critério de Falha: Retorno <= {threshold:.2f}%")

        # X, y split
        X = df.drop(columns=['is_failure', 'Return_Total', 'Ticker'], errors='ignore')
        y = df['is_failure']

        # Sanitização: inf -> nan, dropna, alinhar índices
        X = X.replace([np.inf, -np.inf], np.nan)
        # small tolerance: if many missing features drop rows; else try imputation (here drop)
        X = X.dropna(axis=0, how='any')
        y = y.loc[X.index]

        # Remover colinearidade extrema
        X = remove_correlated_features(X, threshold=0.95)

        # final sanitization cast
        X = X.astype(float)

        return X, y

    def train_and_evaluate(self, X: pd.DataFrame, y: pd.Series) -> Optional[str]:
        """
        Treina o modelo, avalia via CV (ROC-AUC), imprime classification_report,
        calcula permutation importance, gera SHAP summary plot e retorna a top feature.
        """
        if len(y.unique()) < 2:
            logger.warning("Apenas uma classe presente em y. Não é possível treinar.")
            return None

        # Cross-validation (ROC-AUC médio)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        try:
            scores = cross_val_score(self.clf, X, y, cv=cv, scoring='roc_auc', n_jobs=-1)
            logger.info(f"ROC-AUC Médio (CV): {scores.mean():.3f} (+/- {scores.std()*2:.3f})")
        except Exception as e:
            logger.warning(f"CV ROC-AUC falhou: {e}")

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.30, stratify=y, random_state=42)
        self.clf.fit(X_train, y_train)

        # Performance on test
        y_pred = self.clf.predict(X_test)
        logger.info("Performance no Test Set:")
        logger.info("\n" + classification_report(y_test, y_pred))

        # Permutation importance (mais robusto)
        try:
            logger.info("Calculando Permutation Importance (pode demorar)...")
            perm = permutation_importance(self.clf, X_test, y_test, n_repeats=10, random_state=42, n_jobs=-1)
            sorted_idx = perm.importances_mean.argsort()[::-1]
            top_k = [X.columns[i] for i in sorted_idx[:10]]
            logger.info("🏆 TOP 10 FATORES REAIS DE RISCO (Permutation Importance):")
            for rank, idx in enumerate(sorted_idx[:10], start=1):
                logger.info(f"{rank:02d}. {X.columns[idx]:<25} | Impacto: {perm.importances_mean[idx]:.6f}")
        except Exception as e:
            logger.warning(f"Permutation importance falhou: {e}")
            top_k = list(X.columns[:10])

        # SHAP explanation (final model)
        try:
            logger.info("Gerando SHAP summary plot...")
            explainer = shap.TreeExplainer(self.clf)
            shap_values = explainer.shap_values(X_test)
            # Ensure plot directory
            os.makedirs(PLOTS_DIR, exist_ok=True)
            shap_path = os.path.join(PLOTS_DIR, 'shap_summary_ultimate.png')
            plt.figure(figsize=(10, 6))
            shap.summary_plot(shap_values[1], X_test, show=False)
            plt.savefig(shap_path, bbox_inches='tight')
            # Cleanup
            plt.clf()
            plt.close('all')
            logger.info(f"Gráfico SHAP salvo: {shap_path}")
        except Exception as e:
            logger.error(f"Erro no SHAP: {e}")

        # Return top feature name (permutation if available)
        try:
            return top_k[0]
        except Exception:
            return X.columns[0] if X.shape[1] > 0 else None

# -------------------------
# Orquestração principal
# -------------------------
def main():
    logger.info("--- 🛡️  SISTEMA DE DETECÇÃO DE TOXICIDADE V2 (FINAL) ---")

    if not os.path.exists(REPORT_PATH):
        logger.error("Relatório não encontrado. Rode o backtest antes.")
        return

    df_report = pd.read_csv(REPORT_PATH)
    logger.info(f"Encontrados {len(df_report)} ativos no relatório.")

    # Extração de features (batch)
    features_list: List[dict] = []
    for idx, row in df_report.iterrows():
        ticker = row['Ticker']
        feat = FeatureEngineer.extract(ticker, row)
        if feat is not None:
            features_list.append(feat)
        # feedback mínimo
        if idx % 20 == 0:
            print(".", end="", flush=True)

    if not features_list:
        logger.error("Nenhuma feature foi extraída. Verifique load_price_data / calculate_indicators.")
        return

    df_features = pd.DataFrame(features_list)
    logger.info(f"Dataset de features extraído: {df_features.shape}")

    # Salva snapshot das features (útil para auditoria)
    os.makedirs('src/co_piloto_quant/data/features', exist_ok=True)
    features_path = 'src/co_piloto_quant/data/features/features_snapshot.parquet'
    try:
        df_features.to_parquet(features_path, index=False)
        logger.info(f"Snapshot de features salvo: {features_path}")
    except Exception:
        # fallback CSV
        df_features.to_csv('src/co_piloto_quant/data/features/features_snapshot.csv', index=False)
        logger.info("Snapshot salvo em csv (fallback).")

    # Modelagem
    model = ToxicityModel()
    # use_clustering_labels=True se preferir cluster-based labeling (opcional)
    X, y = model.prepare_data(df_features, use_clustering_labels=False)

    if X.shape[0] < 10:
        logger.warning("Amostra muito pequena para modelagem confiável (<10). Abortando.")
        return

    top_feature = model.train_and_evaluate(X, y)

    # Insight final: direcionalidade da correlação com is_failure
    if top_feature is not None and top_feature in X.columns:
        corr = X[top_feature].corr(y)
        direction = "ALTA" if corr > 0 else "BAIXA"
        logger.info("--- CONCLUSÃO ---")
        logger.info(f"Maior preditor de falha (feature): {top_feature}")
        logger.info(f"Correlação com falha: {corr:.3f} => Valores {direction} aumentam chance de prejuízo.")
        logger.info("Considere adicionar filtros no seu universo com base nesta métrica (ex: se ALTA então excluir ativos com feature > LIMITE).")
    else:
        logger.info("Não foi possível identificar um top feature conclusivo.")

if __name__ == "__main__":
    main()

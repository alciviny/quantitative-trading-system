import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from co_piloto_quant.data.data_manager import DataManager
from co_piloto_quant.pricing import (
    black_scholes,
    calculate_greeks,
    implied_volatility,
    _to_years,
    get_mid_price,
)
from co_piloto_quant.risk_regime import RiskRegimeManager, ValidationResult


class TestDataManagerUtilities:
    """Testes para utilidades do DataManager"""

    def test_normalize_index_with_date_column(self):
        df = pd.DataFrame({
            'Date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'close': [100.0, 101.0, 102.0]
        })
        result = DataManager._normalize_index(df)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 3

    def test_normalize_index_with_datetime_index(self):
        dates = pd.date_range('2024-01-01', periods=3)
        df = pd.DataFrame({'close': [100.0, 101.0, 102.0]}, index=dates)
        result = DataManager._normalize_index(df)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 3

    def test_merge_data_empty_old_data(self):
        df_new = pd.DataFrame({
            'close': [100.0, 101.0]
        }, index=pd.date_range('2024-01-01', periods=2))

        result = DataManager._merge_data(pd.DataFrame(), df_new)
        assert len(result) == 2
        assert result['close'].iloc[0] == 100.0

    def test_merge_data_removes_duplicates(self):
        df_old = pd.DataFrame({
            'close': [100.0, 101.0]
        }, index=pd.date_range('2024-01-01', periods=2))

        df_new = pd.DataFrame({
            'close': [101.5, 102.0]
        }, index=pd.date_range('2024-01-02', periods=2))

        result = DataManager._merge_data(df_old, df_new)
        assert len(result) == 3
        assert result.iloc[1]['close'] == 101.5

    def test_compute_hash_deterministic(self):
        df = pd.DataFrame({'close': [100.0, 101.0, 102.0]})
        hash1 = DataManager._compute_hash(df)
        hash2 = DataManager._compute_hash(df)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex string

    def test_compute_hash_different_data(self):
        df1 = pd.DataFrame({'close': [100.0, 101.0]})
        df2 = pd.DataFrame({'close': [100.0, 102.0]})
        hash1 = DataManager._compute_hash(df1)
        hash2 = DataManager._compute_hash(df2)
        assert hash1 != hash2

    def test_needs_update_empty_data(self):
        dm = DataManager(max_age_days=2)
        result = dm._needs_update(pd.DataFrame(), force_update=False)
        assert result is True

    def test_needs_update_force_update(self):
        dm = DataManager(max_age_days=2)
        df = pd.DataFrame(
            {'close': [100.0]},
            index=pd.DatetimeIndex(['2020-01-01'])
        )
        result = dm._needs_update(df, force_update=True)
        assert result is True

    def test_needs_update_recent_data(self):
        dm = DataManager(max_age_days=2)
        today = datetime.now()
        df = pd.DataFrame(
            {'close': [100.0]},
            index=pd.DatetimeIndex([today])
        )
        result = dm._needs_update(df, force_update=False)
        assert result is False

    def test_needs_update_old_data(self):
        dm = DataManager(max_age_days=2)
        old_date = datetime.now() - timedelta(days=5)
        df = pd.DataFrame(
            {'close': [100.0]},
            index=pd.DatetimeIndex([old_date])
        )
        result = dm._needs_update(df, force_update=False)
        assert result is True


class TestPricing:
    """Testes para Black-Scholes e Gregas"""

    def test_to_years_conversion(self):
        years = _to_years(252)
        assert years == pytest.approx(1.0)
        
        years = _to_years(126)
        assert years == pytest.approx(0.5)

    def test_get_mid_price_valid_spread(self):
        mid = get_mid_price(bid=100.0, ask=102.0, last=101.0)
        assert mid == 101.0

    def test_get_mid_price_invalid_spread_uses_last(self):
        mid = get_mid_price(bid=102.0, ask=100.0, last=101.0)
        assert mid == 101.0

    def test_black_scholes_call_basic(self):
        S = 100.0
        K = 100.0
        T = _to_years(30)
        r = 0.05
        sigma = 0.2
        
        price = black_scholes(S, K, T, r, sigma, option_type='call')
        assert price > 0
        assert price < S

    def test_black_scholes_put_basic(self):
        S = 100.0
        K = 100.0
        T = _to_years(30)
        r = 0.05
        sigma = 0.2
        
        price = black_scholes(S, K, T, r, sigma, option_type='put')
        assert price > 0

    def test_black_scholes_atm_call_put_parity(self):
        S = 100.0
        K = 100.0
        T = _to_years(30)
        r = 0.05
        sigma = 0.2
        
        call = black_scholes(S, K, T, r, sigma, option_type='call')
        put = black_scholes(S, K, T, r, sigma, option_type='put')
        
        c_minus_p = call - put
        pv_k = K * np.exp(-r * T)
        assert c_minus_p == pytest.approx(S - pv_k, rel=1e-6)

    def test_black_scholes_itm_call_intrinsic(self):
        S = 110.0
        K = 100.0
        T = _to_years(30)
        r = 0.05
        sigma = 0.2
        
        price = black_scholes(S, K, T, r, sigma, option_type='call')
        intrinsic = S - K
        assert price >= intrinsic

    def test_black_scholes_expired_option(self):
        S = 110.0
        K = 100.0
        T = 0.0
        r = 0.05
        sigma = 0.2
        
        price = black_scholes(S, K, T, r, sigma, option_type='call')
        assert price == pytest.approx(10.0)

    def test_calculate_greeks_all_keys_present(self):
        S = 100.0
        K = 100.0
        T = _to_years(30)
        r = 0.05
        sigma = 0.2
        
        greeks = calculate_greeks(S, K, T, r, sigma, option_type='call')
        
        assert 'delta' in greeks
        assert 'gamma' in greeks
        assert 'vega' in greeks
        assert 'theta' in greeks
        assert 'rho' in greeks

    def test_calculate_greeks_delta_bounds(self):
        S = 100.0
        K = 100.0
        T = _to_years(30)
        r = 0.05
        sigma = 0.2
        
        call_greeks = calculate_greeks(S, K, T, r, sigma, option_type='call')
        put_greeks = calculate_greeks(S, K, T, r, sigma, option_type='put')
        
        assert 0 <= call_greeks['delta'] <= 1
        assert -1 <= put_greeks['delta'] <= 0

    def test_calculate_greeks_nan_propagation(self):
        S = 100.0
        K = 100.0
        T = _to_years(30)
        r = 0.05
        sigma = float('nan')
        
        greeks = calculate_greeks(S, K, T, r, sigma, option_type='call')
        
        assert np.isnan(greeks['delta']) or np.isnan(greeks['vega'])

    def test_implied_volatility_basic(self):
        S = 100.0
        K = 100.0
        T = _to_years(30)
        r = 0.05
        sigma_true = 0.2
        
        price = black_scholes(S, K, T, r, sigma_true, option_type='call')
        sigma_implied = implied_volatility(price, S, K, T, r, option_type='call')
        
        assert not np.isnan(sigma_implied)
        assert sigma_implied == pytest.approx(sigma_true, rel=1e-3)

    def test_implied_volatility_invalid_price_below_intrinsic(self):
        S = 100.0
        K = 100.0
        T = _to_years(30)
        r = 0.05
        price = 0.01
        
        iv = implied_volatility(price, S, K, T, r, option_type='call')
        assert np.isnan(iv)

    def test_implied_volatility_zero_time(self):
        S = 100.0
        K = 100.0
        T = 0.0
        r = 0.05
        price = 10.0
        
        iv = implied_volatility(price, S, K, T, r, option_type='call')
        assert np.isnan(iv)


class TestRiskRegime:
    """Testes para RiskRegimeManager"""

    def test_validation_result_dataclass(self):
        result = ValidationResult(approved=True, reason="Test")
        assert result.approved is True
        assert result.reason == "Test"

    def test_validate_market_regime_insufficient_data(self):
        rm = RiskRegimeManager()
        df = pd.DataFrame({'close': [100.0, 101.0]})
        
        result = rm.validate_market_regime(df)
        assert result.approved is False
        assert "insuficientes" in result.reason

    def test_validate_market_regime_learning_mode(self):
        rm = RiskRegimeManager()
        df = pd.DataFrame({
            'close': np.random.randn(100).cumsum() + 100,
            'Entropy_20': 1.5,
            'VolVol_Z': 1.0,
            'Entropy_Z': 1.0,
        })
        
        result = rm.validate_market_regime(df)
        assert result.approved is True
        assert "Aprendizado" in result.reason

    def test_validate_market_regime_high_entropy_absolute(self):
        rm = RiskRegimeManager()
        df = pd.DataFrame({
            'close': np.random.randn(300).cumsum() + 100,
            'Entropy_20': 3.5,
            'VolVol_Z': 1.0,
            'Entropy_Z': 1.0,
        })
        
        result = rm.validate_market_regime(df)
        assert result.approved is False
        assert "Entropia Tóxica" in result.reason

    def test_validate_market_regime_low_entropy_trend(self):
        rm = RiskRegimeManager()
        df = pd.DataFrame({
            'close': np.array([100.0, 101.0, 102.0, 103.0] * 100),
            'Entropy_20': 0.05,
            'VolVol_Z': 1.0,
            'Entropy_Z': 1.0,
        })
        
        result = rm.validate_market_regime(df)
        assert result.approved is False
        assert "Tendência Extrema" in result.reason

    def test_validate_market_regime_high_volatility(self):
        rm = RiskRegimeManager()
        df = pd.DataFrame({
            'close': np.concatenate([
                np.array([100.0] * 100),
                np.array([80.0, 120.0] * 100)
            ]),
            'Entropy_20': 1.5,
            'VolVol_Z': 1.0,
            'Entropy_Z': 1.0,
        })
        
        result = rm.validate_market_regime(df)
        
        if result.approved is False:
            assert "Volatilidade Alta" in result.reason

    def test_validate_market_regime_approved(self):
        rm = RiskRegimeManager()
        df = pd.DataFrame({
            'close': np.random.normal(100, 2, 300),
            'Entropy_20': 1.5,
            'VolVol_Z': 1.0,
            'Entropy_Z': 1.0,
        })
        
        result = rm.validate_market_regime(df)
        assert result.approved is True
        assert "aprovado" in result.reason.lower()


class TestDataIntegration:
    """Testes de integração entre componentes"""

    def test_pricing_greeks_consistency(self):
        S = 100.0
        K = 100.0
        T = _to_years(30)
        r = 0.05
        sigma = 0.2
        
        price = black_scholes(S, K, T, r, sigma, option_type='call')
        greeks = calculate_greeks(S, K, T, r, sigma, option_type='call')
        
        assert price > 0
        assert 0 < greeks['delta'] < 1
        assert greeks['vega'] > 0
        assert not np.isnan(price)
        assert not np.isnan(greeks['delta'])

    def test_implied_vol_round_trip(self):
        S = 100.0
        K = 100.0
        T = _to_years(30)
        r = 0.05
        sigma_original = 0.25
        
        price = black_scholes(S, K, T, r, sigma_original, option_type='put')
        sigma_recovered = implied_volatility(price, S, K, T, r, option_type='put')
        
        assert not np.isnan(sigma_recovered)
        assert sigma_recovered == pytest.approx(sigma_original, rel=1e-2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

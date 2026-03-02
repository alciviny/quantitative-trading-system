import pandas as pd
from regime_engine.pipeline.main import run_pipeline

def test_run_pipeline():
    # Exemplo de teste com dados simulados
    df = pd.DataFrame({
        'close': np.linspace(10, 20, 400),
        'high': np.linspace(10.5, 20.5, 400),
        'low': np.linspace(9.5, 19.5, 400),
        'volume': np.random.randint(1000, 5000, 400),
        'daily_return': np.random.normal(0, 0.01, 400),
        'hurst_72_returns': np.random.normal(0.5, 0.1, 400),
        'half_life_60': np.random.normal(30, 5, 400),
        'entropy_20': np.random.normal(1, 0.2, 400),
        'Choppiness_14': np.random.normal(50, 10, 400),
        'volatility_21': np.random.normal(0.02, 0.005, 400)
    })
    result = run_pipeline(df)
    assert 'regime_rolling' in result.columns

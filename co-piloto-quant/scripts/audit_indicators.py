"""
Script de Auditoria de Indicadores
===================================
Verifica se entropy, hurst e half_life estão sendo calculados corretamente
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from co_piloto_quant.data.data_manager import data_manager
from co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst
from co_piloto_quant.indicators.special.half_life import calculate_rolling_ou_params

def audit_ticker(ticker: str, verbose=False):
    """Audita um ticker específico"""
    print(f"\n{'='*80}")
    print(f"AUDITANDO: {ticker}")
    print(f"{'='*80}")
    
    # 1. Carrega dados do banco
    df = data_manager.get_data(ticker)
    
    if df.empty:
        print(f"❌ Sem dados para {ticker}")
        return None
    
    print(f"✓ Dados carregados: {len(df)} linhas")
    print(f"  Período: {df.index[0].date()} até {df.index[-1].date()}")
    
    # 2. Verifica colunas básicas OHLCV
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    missing = [c for c in required_cols if c not in df.columns]
    
    if missing:
        print(f"❌ Colunas faltando: {missing}")
        return None
    
    print(f"✓ Colunas OHLCV presentes")
    
    # 3. Verifica se close tem valores válidos
    close_stats = df['close'].describe()
    print(f"\n📊 Estatísticas do Close:")
    print(f"  Min: {close_stats['min']:.2f}")
    print(f"  Max: {close_stats['max']:.2f}")
    print(f"  Média: {close_stats['mean']:.2f}")
    print(f"  NaN: {df['close'].isna().sum()}")
    
    if df['close'].min() == 0.0 and df['close'].max() == 0.0:
        print(f"❌ ERRO: Todos os valores de close são ZERO!")
        return None
    
    # 4. Calcula indicadores manualmente
    print(f"\n🧮 Calculando indicadores manualmente...")
    
    try:
        entropy_manual = calculate_rolling_entropy(df['close'], window=20)
        print(f"✓ Entropy calculado: {len(entropy_manual)} valores")
        
        hurst_manual = calculate_rolling_hurst(df['close'], window=72, kind='returns')
        print(f"✓ Hurst calculado: {len(hurst_manual)} valores")
        
        halflife_df = calculate_rolling_ou_params(df['close'], window=60)
        print(f"✓ Half-life calculado: {len(halflife_df)} valores")
        
    except Exception as e:
        print(f"❌ Erro ao calcular indicadores: {e}")
        return None
    
    # 5. Verifica se indicadores estão no DataFrame salvo
    print(f"\n🔍 Verificando indicadores salvos...")
    
    indicators_check = {
        'entropy_20': entropy_manual,
        'hurst_72_returns': hurst_manual,
        'half_life_60': halflife_df['half_life_60'] if 'half_life_60' in halflife_df.columns else None
    }
    
    results = {}
    
    for ind_name, manual_series in indicators_check.items():
        if manual_series is None:
            print(f"  ⚠️  {ind_name}: Não calculado")
            continue
            
        if ind_name in df.columns:
            saved_series = df[ind_name]
            
            # Compara valores (ignora NaN)
            valid_mask = ~(manual_series.isna() | saved_series.isna())
            
            if valid_mask.sum() == 0:
                print(f"  ⚠️  {ind_name}: Todos os valores são NaN")
                continue
            
            diff = (manual_series[valid_mask] - saved_series[valid_mask]).abs()
            max_diff = diff.max()
            mean_diff = diff.mean()
            
            if max_diff < 1e-6:
                print(f"  ✓ {ind_name}: Idêntico (diff max: {max_diff:.2e})")
                results[ind_name] = 'OK'
            elif max_diff < 0.01:
                print(f"  ✓ {ind_name}: Muito próximo (diff max: {max_diff:.4f})")
                results[ind_name] = 'OK'
            else:
                print(f"  ❌ {ind_name}: DIFERENÇA SIGNIFICATIVA (max: {max_diff:.4f}, média: {mean_diff:.4f})")
                results[ind_name] = 'ERRO'
                
                if verbose:
                    print(f"     Manual (últimas 5): {manual_series.tail().tolist()}")
                    print(f"     Salvo (últimas 5):  {saved_series.tail().tolist()}")
        else:
            print(f"  ❌ {ind_name}: NÃO ESTÁ SALVO NO BANCO")
            results[ind_name] = 'FALTANDO'
    
    # 6. Verifica ranges dos indicadores
    print(f"\n📈 Ranges dos Indicadores:")
    
    if 'entropy_20' in df.columns:
        entropy_vals = df['entropy_20'].dropna()
        if len(entropy_vals) > 0:
            print(f"  Entropy: [{entropy_vals.min():.4f}, {entropy_vals.max():.4f}] (esperado: [0, ~5])")
            if entropy_vals.max() > 10:
                print(f"    ⚠️  Valores muito altos detectados!")
    
    if 'hurst_72_returns' in df.columns:
        hurst_vals = df['hurst_72_returns'].dropna()
        if len(hurst_vals) > 0:
            print(f"  Hurst: [{hurst_vals.min():.4f}, {hurst_vals.max():.4f}] (esperado: [0, 1])")
            if hurst_vals.min() < 0 or hurst_vals.max() > 1:
                print(f"    ⚠️  Valores fora do range esperado!")
    
    if 'half_life_60' in df.columns:
        hl_vals = df['half_life_60'].dropna()
        if len(hl_vals) > 0:
            print(f"  Half-Life: [{hl_vals.min():.2f}, {hl_vals.max():.2f}] dias")
    
    return results


def main():
    """Audita múltiplos tickers"""
    print("\n" + "="*80)
    print("AUDITORIA DE INDICADORES - Co-Piloto Quant")
    print("="*80)
    
    # Tickers para testar
    test_tickers = ['PETR4.SA', 'VALE3.SA', 'BBDC4.SA', 'ITUB4.SA', 'WEGE3.SA']
    
    all_results = {}
    
    for ticker in test_tickers:
        try:
            result = audit_ticker(ticker, verbose=False)
            all_results[ticker] = result
        except Exception as e:
            print(f"❌ Erro ao auditar {ticker}: {e}")
            all_results[ticker] = None
    
    # Resumo final
    print(f"\n{'='*80}")
    print("RESUMO DA AUDITORIA")
    print(f"{'='*80}")
    
    ok_count = 0
    error_count = 0
    missing_count = 0
    
    for ticker, results in all_results.items():
        if results is None:
            print(f"{ticker}: ❌ Falhou")
            error_count += 1
        else:
            status = "✓" if all(v == 'OK' for v in results.values()) else "⚠️"
            print(f"{ticker}: {status} {results}")
            
            if all(v == 'OK' for v in results.values()):
                ok_count += 1
            elif 'FALTANDO' in results.values():
                missing_count += 1
            else:
                error_count += 1
    
    print(f"\n📊 Total:")
    print(f"  ✓ OK: {ok_count}/{len(test_tickers)}")
    print(f"  ❌ Erros: {error_count}/{len(test_tickers)}")
    print(f"  ⚠️  Faltando: {missing_count}/{len(test_tickers)}")
    
    if ok_count == len(test_tickers):
        print(f"\n🎉 TODOS OS INDICADORES ESTÃO CORRETOS!")
    else:
        print(f"\n⚠️  Alguns indicadores precisam de atenção")


if __name__ == "__main__":
    main()

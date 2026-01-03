#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
walk_forward_simple.py - Versão simplificada para validação
Executa walk-forward sem dependências customizadas
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from co_piloto_quant.strategies.mean_reversion import MeanReversionStrategy

ML_READY_PATH = Path(__file__).parent.parent / "src" / "co_piloto_quant" / "data" / "ml_ready"
CUSTO_TOTAL_TRADE = 0.0006


def load_and_prepare_file(file_path: Path, train_start, train_end, test_start, test_end):
    """Carrega arquivo e retorna dados de treino e teste"""
    try:
        df = pd.read_parquet(file_path)
        
        if 'data_pregao' in df.columns:
            df.index = pd.to_datetime(df['data_pregao'])
        else:
            df.index = pd.to_datetime(df.index, errors='coerce')
        
        df = df.sort_index()
        
        # Filtra períodos
        df_train = df[(df.index >= train_start) & (df.index <= train_end)].copy()
        df_test = df[(df.index >= test_start) & (df.index <= test_end)].copy()
        
        return df_train, df_test
    except Exception as e:
        print(f"❌ Erro ao carregar {file_path.name}: {e}")
        return None, None


def run_simple_backtest(df: pd.DataFrame, ticker: str) -> list:
    """Executa backtest simples usando a estratégia"""
    if df.empty or 'close' not in df.columns:
        return []
    
    try:
        strategy = MeanReversionStrategy(
            bb_std_dev=1.5,
            rsi_period=120,
            bb_std_dev_volatile=2.5,
            adaptive_rsi=True,
            adaptive_bb=True,
            use_regime_filter=True,
            max_half_life=25
        )
        
        df_eval = strategy.evaluate(df.copy(), ticker)
        
        if 'SIGNAL' not in df_eval.columns:
            return []
        
        trades = []
        in_trade = False
        entry_price = 0.0
        entry_date = None
        
        for i in range(1, len(df_eval)):
            sig = df_eval['SIGNAL'].iloc[i] if 'SIGNAL' in df_eval.columns else ''
            close = df_eval['close'].iloc[i]
            date = df_eval.index[i]
            
            if not in_trade and sig == 'BUY':
                in_trade = True
                entry_price = close
                entry_date = date
            
            elif in_trade and (sig == 'SELL' or i == len(df_eval) - 1):
                exit_price = close
                raw_ret = (exit_price / entry_price) - 1
                net_ret = raw_ret - (CUSTO_TOTAL_TRADE * 2)
                days = (date - entry_date).days
                
                trades.append({
                    'ticker': ticker,
                    'return': net_ret,
                    'win': 1 if net_ret > 0 else 0,
                    'days_held': days,
                    'date_entry': entry_date,
                    'date_exit': date
                })
                
                in_trade = False
        
        return trades
    
    except Exception as e:
        print(f"⚠️ Erro ao processar {ticker}: {e}")
        return []


def main():
    print("\n" + "="*70)
    print("🔄 WALK-FORWARD VALIDATION (Versão Simplificada)")
    print("="*70)
    
    # Lista arquivos
    files = sorted(list(ML_READY_PATH.glob("*_SA.parquet")))
    print(f"\n📁 Encontrados {len(files)} ativos")
    
    if not files:
        print("❌ Nenhum arquivo encontrado em", ML_READY_PATH)
        return
    
    # Lê datas do primeiro arquivo para determinar períodos
    print("\n📅 Determinando períodos disponíveis...")
    df_sample = pd.read_parquet(files[0])
    if 'data_pregao' in df_sample.columns:
        dates = pd.to_datetime(df_sample['data_pregao'])
    else:
        dates = pd.to_datetime(df_sample.index, errors='coerce')
    
    min_date = dates.min()
    max_date = dates.max()
    print(f"   Período: {min_date.date()} a {max_date.date()}")
    
    # Define janelas (6 meses treino + 3 meses teste)
    windows = []
    current = min_date
    
    while True:
        train_end = current + pd.DateOffset(months=6)
        test_end = train_end + pd.DateOffset(months=3)
        
        if test_end > max_date:
            break
        
        windows.append({
            'name': f"{current.strftime('%Y-%m')} -> {train_end.strftime('%Y-%m')}",
            'train_start': current,
            'train_end': train_end,
            'test_start': train_end + pd.Timedelta(days=1),
            'test_end': test_end
        })
        
        current = current + pd.DateOffset(months=1)
    
    print(f"   Geradas {len(windows)} janelas\n")
    
    # Processa cada janela
    all_results = []
    
    for idx, window in enumerate(windows, 1):
        print(f"\n📊 [{idx}/{len(windows)}] Janela: {window['name']}")
        print(f"   Treino: {window['train_start'].date()} a {window['train_end'].date()}")
        print(f"   Teste:  {window['test_start'].date()} a {window['test_end'].date()}")
        
        window_trades = {'TRAIN': [], 'TEST': []}
        
        # Processa cada arquivo
        for file_idx, file_path in enumerate(files, 1):
            ticker = file_path.stem.replace('_', '.')
            
            df_train, df_test = load_and_prepare_file(
                file_path,
                window['train_start'], window['train_end'],
                window['test_start'], window['test_end']
            )
            
            if df_train is not None and not df_train.empty:
                trades = run_simple_backtest(df_train, ticker)
                for t in trades:
                    t['phase'] = 'TRAIN'
                    t['window'] = window['name']
                window_trades['TRAIN'].extend(trades)
            
            if df_test is not None and not df_test.empty:
                trades = run_simple_backtest(df_test, ticker)
                for t in trades:
                    t['phase'] = 'TEST'
                    t['window'] = window['name']
                window_trades['TEST'].extend(trades)
            
            if file_idx % 20 == 0:
                print(f"   ✓ Processados {file_idx}/{len(files)} ativos", end='\r')
        
        print(f"   ✓ Processados {len(files)}/{len(files)} ativos")
        all_results.extend(window_trades['TRAIN'])
        all_results.extend(window_trades['TEST'])
    
    # Análise de resultados
    if all_results:
        df_results = pd.DataFrame(all_results)
        
        print("\n" + "="*70)
        print("📈 RESULTADOS")
        print("="*70)
        
        # Por fase
        print("\n🎯 PERFORMANCE POR FASE (TREINO vs TESTE):")
        for phase in ['TRAIN', 'TEST']:
            phase_data = df_results[df_results['phase'] == phase]
            if not phase_data.empty:
                avg_ret = phase_data['return'].mean()
                win_rate = (phase_data['return'] > 0).mean()
                trades = len(phase_data)
                print(f"   {phase:6} | {trades:4} trades | {avg_ret:8.4f} retorno | {win_rate:6.2%} win_rate")
        
        # Degradação
        train_ret = df_results[df_results['phase'] == 'TRAIN']['return'].mean()
        test_ret = df_results[df_results['phase'] == 'TEST']['return'].mean()
        
        if train_ret != 0:
            degradation = ((test_ret - train_ret) / abs(train_ret)) * 100
        else:
            degradation = 0
        
        print(f"\n⚠️  DEGRADAÇÃO GERAL: {degradation:.2f}%")
        
        if abs(degradation) < 20:
            print("   ✅ Sistema CONSISTENTE (degradação < 20%)")
        elif abs(degradation) < 50:
            print("   ⚠️  Degradação MODERADA (20% < degradação < 50%)")
        else:
            print("   ❌ Sistema OVERFITTED (degradação > 50%)")
        
        # Por janela
        print("\n🪟 PERFORMANCE POR JANELA:")
        for window_name in df_results['window'].unique():
            window_data = df_results[df_results['window'] == window_name]
            
            train_data = window_data[window_data['phase'] == 'TRAIN']
            test_data = window_data[window_data['phase'] == 'TEST']
            
            if not train_data.empty:
                train_ret = train_data['return'].mean()
                train_wr = (train_data['return'] > 0).mean()
                train_cnt = len(train_data)
                print(f"   {window_name}")
                print(f"      Treino: {train_cnt:3} trades | {train_ret:7.4f} ret | {train_wr:6.2%} WR")
            
            if not test_data.empty:
                test_ret = test_data['return'].mean()
                test_wr = (test_data['return'] > 0).mean()
                test_cnt = len(test_data)
                
                if train_data is not None and not train_data.empty:
                    deg = ((test_ret - train_ret) / abs(train_ret) * 100) if train_ret != 0 else 0
                    print(f"      Teste:  {test_cnt:3} trades | {test_ret:7.4f} ret | {test_wr:6.2%} WR (deg: {deg:6.1f}%)")
                else:
                    print(f"      Teste:  {test_cnt:3} trades | {test_ret:7.4f} ret | {test_wr:6.2%} WR")
        
        # Salva CSV
        out_path = Path(__file__).parent.parent / "walk_forward_results.csv"
        df_results.to_csv(out_path, index=False)
        print(f"\n💾 Resultados salvos em: {out_path}")
    
    else:
        print("\n❌ Nenhum trade gerado")


if __name__ == '__main__':
    main()

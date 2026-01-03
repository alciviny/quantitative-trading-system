#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
walk_forward_ultra_simple.py - Versão ULTRA SIMPLES
Sinal baseado apenas em média móvel (sem dependência de RSI)
"""

import pandas as pd
import numpy as np
from pathlib import Path

ML_READY_PATH = Path(__file__).parent.parent / "src" / "co_piloto_quant" / "data" / "ml_ready"


def load_file(file_path):
    """Carrega arquivo parquet"""
    try:
        df = pd.read_parquet(file_path)
        if 'data_pregao' in df.columns:
            df.index = pd.to_datetime(df['data_pregao'])
        else:
            df.index = pd.to_datetime(df.index, errors='coerce')
        return df.sort_index()
    except Exception as e:
        return None


def calc_trades_ma(df, ticker):
    """Calcula trades usando apenas Média Móvel (SMA 20/50)"""
    trades = []
    
    if df.empty or 'close' not in df.columns:
        return trades
    
    close = df['close'].fillna(method='ffill').fillna(method='bfill')
    
    # Calcula médias móveis
    sma20 = close.rolling(20, min_periods=1).mean()
    sma50 = close.rolling(50, min_periods=1).mean()
    
    in_trade = False
    entry = 0
    entry_date = None
    
    for i in range(1, len(df)):
        c = close.iloc[i]
        s20 = sma20.iloc[i]
        s50 = sma50.iloc[i]
        date = df.index[i]
        
        # Sinal de entrada: preço cruza acima de SMA20 que tá acima de SMA50
        if not in_trade and close.iloc[i-1] <= sma20.iloc[i-1] and c > s20 and s20 > s50:
            in_trade = True
            entry = c
            entry_date = date
        
        # Sinal de saída: preço cruza abaixo de SMA20
        elif in_trade and c < s20:
            ret = (c / entry) - 1 - 0.0012
            trades.append({
                'ticker': ticker,
                'return': ret,
                'win': 1 if ret > 0 else 0,
                'days': (date - entry_date).days
            })
            in_trade = False
    
    return trades


def main():
    print("\n" + "="*70)
    print("🔄 WALK-FORWARD VALIDATION (ULTRA SIMPLES)")
    print("="*70)
    
    files = sorted(list(ML_READY_PATH.glob("*_SA.parquet")))
    print(f"\n📁 Encontrados {len(files)} ativos")
    
    if not files:
        print(f"❌ Nenhum arquivo em {ML_READY_PATH}")
        return
    
    # Lê datas
    print("\n📅 Determinando períodos...")
    df_sample = load_file(files[0])
    if df_sample is None:
        print("❌ Erro ao carregar arquivo de amostra")
        return
    
    min_date = df_sample.index.min()
    max_date = df_sample.index.max()
    print(f"   Período: {min_date.date()} a {max_date.date()}")
    
    # Janelas: 6 meses treino + 3 meses teste, avança 1 mês
    windows = []
    current = min_date
    
    while True:
        train_end = current + pd.DateOffset(months=6)
        test_end = train_end + pd.DateOffset(months=3)
        
        if test_end > max_date:
            break
        
        windows.append({
            'name': f"{current.strftime('%Y-%m')}",
            'train_start': current,
            'train_end': train_end,
            'test_start': train_end + pd.Timedelta(days=1),
            'test_end': test_end
        })
        
        current = current + pd.DateOffset(months=1)
    
    print(f"   {len(windows)} janelas de teste\n")
    
    all_trades = []
    
    for w_idx, window in enumerate(windows, 1):
        print(f"\n[{w_idx}/{len(windows)}] {window['name']}")
        print(f"  Treino: {window['train_start'].date()} → {window['train_end'].date()}")
        print(f"  Teste:  {window['test_start'].date()} → {window['test_end'].date()}")
        
        train_trades = []
        test_trades = []
        
        for file_idx, fp in enumerate(files, 1):
            ticker = fp.stem.replace('_', '.')
            df = load_file(fp)
            
            if df is None:
                continue
            
            # Treino
            df_train = df[(df.index >= window['train_start']) & (df.index <= window['train_end'])]
            if not df_train.empty:
                trades = calc_trades_ma(df_train, ticker)
                for t in trades:
                    t['phase'] = 'TRAIN'
                    t['window'] = window['name']
                train_trades.extend(trades)
            
            # Teste
            df_test = df[(df.index >= window['test_start']) & (df.index <= window['test_end'])]
            if not df_test.empty:
                trades = calc_trades_ma(df_test, ticker)
                for t in trades:
                    t['phase'] = 'TEST'
                    t['window'] = window['name']
                test_trades.extend(trades)
            
            if file_idx % 20 == 0:
                print(f"  ✓ {file_idx}/{len(files)}", end='\r')
        
        print(f"  ✓ {len(files)}/{len(files)} - Treino: {len(train_trades):>3} trades | Teste: {len(test_trades):>3} trades")
        
        all_trades.extend(train_trades)
        all_trades.extend(test_trades)
    
    # Análise
    if all_trades:
        df_res = pd.DataFrame(all_trades)
        
        print("\n" + "="*70)
        print("📊 RESULTADOS")
        print("="*70)
        
        # Por fase
        print("\n📈 POR FASE:")
        for phase in ['TRAIN', 'TEST']:
            phase_df = df_res[df_res['phase'] == phase]
            if not phase_df.empty:
                avg = phase_df['return'].mean()
                wr = (phase_df['return'] > 0).mean()
                cnt = len(phase_df)
                std = phase_df['return'].std()
                print(f"  {phase:6} | {cnt:4} trades | avg: {avg:8.4f} | WR: {wr:6.1%} | std: {std:8.4f}")
        
        # Degradação
        train_avg = df_res[df_res['phase'] == 'TRAIN']['return'].mean()
        test_avg = df_res[df_res['phase'] == 'TEST']['return'].mean()
        
        if train_avg != 0:
            deg = ((test_avg - train_avg) / abs(train_avg)) * 100
        else:
            deg = 0
        
        print(f"\n⚠️  DEGRADAÇÃO GERAL: {deg:.2f}%")
        
        if abs(deg) < 20:
            print("  ✅ CONSISTENTE (degradação < 20%)")
        elif abs(deg) < 50:
            print("  ⚠️  MODERADA (20% < degradação < 50%)")
        else:
            print("  ❌ OVERFITTED (degradação > 50%)")
        
        # Resumo por janela
        print("\n🪟 RESUMO POR JANELA:")
        print("-" * 70)
        
        for window_name in sorted(df_res['window'].unique()):
            window_df = df_res[df_res['window'] == window_name]
            
            train_df = window_df[window_df['phase'] == 'TRAIN']
            test_df = window_df[window_df['phase'] == 'TEST']
            
            if not train_df.empty:
                train_avg = train_df['return'].mean()
                train_wr = (train_df['return'] > 0).mean()
                train_cnt = len(train_df)
            else:
                train_avg = train_wr = train_cnt = 0
            
            if not test_df.empty:
                test_avg = test_df['return'].mean()
                test_wr = (test_df['return'] > 0).mean()
                test_cnt = len(test_df)
            else:
                test_avg = test_wr = test_cnt = 0
            
            print(f"\n  {window_name}")
            print(f"    TREINO: {train_cnt:3} trades | {train_avg:7.4f} ret | {train_wr:6.1%} WR")
            print(f"    TESTE:  {test_cnt:3} trades | {test_avg:7.4f} ret | {test_wr:6.1%} WR", end="")
            
            if train_avg != 0:
                deg_window = ((test_avg - train_avg) / abs(train_avg)) * 100
                print(f" | deg: {deg_window:6.1f}%")
            else:
                print()
        
        # Salva
        out = Path(__file__).parent.parent / "walk_forward_results.csv"
        df_res.to_csv(out, index=False)
        print(f"\n💾 Resultados salvos em: {out}")
        print(f"   Total de trades: {len(df_res)}")
    else:
        print("\n❌ Nenhum trade gerado")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
walk_forward_minimal.py - Versão MUITO SIMPLES
Sem dependências customizadas - apenas lê parquets e calcula stats
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
        print(f"  ❌ {file_path.name}: {e}")
        return None


def calc_simple_trades(df, ticker):
    """Calcula trades muito simples: quando RSI sai de oversold"""
    trades = []
    
    if df.empty or 'close' not in df.columns:
        return trades
    
    # Se tiver RSI, usa como sinal
    rsi_col = None
    for col in df.columns:
        if 'rsi' in col.lower():
            rsi_col = col
            break
    
    if rsi_col is None:
        return trades
    
    in_trade = False
    entry = 0
    entry_date = None
    
    for i in range(1, len(df)):
        rsi = df[rsi_col].iloc[i]
        close = df['close'].iloc[i]
        date = df.index[i]
        
        if not in_trade and rsi < 30:
            in_trade = True
            entry = close
            entry_date = date
        elif in_trade and rsi > 70:
            ret = (close / entry) - 1 - 0.0012
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
    print("🔄 WALK-FORWARD VALIDATION (MINIMAL)")
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
                trades = calc_simple_trades(df_train, ticker)
                for t in trades:
                    t['phase'] = 'TRAIN'
                    t['window'] = window['name']
                train_trades.extend(trades)
            
            # Teste
            df_test = df[(df.index >= window['test_start']) & (df.index <= window['test_end'])]
            if not df_test.empty:
                trades = calc_simple_trades(df_test, ticker)
                for t in trades:
                    t['phase'] = 'TEST'
                    t['window'] = window['name']
                test_trades.extend(trades)
            
            if file_idx % 20 == 0:
                print(f"  ✓ {file_idx}/{len(files)}", end='\r')
        
        print(f"  ✓ {len(files)}/{len(files)} - Treino: {len(train_trades)} trades | Teste: {len(test_trades)} trades")
        
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
                print(f"  {phase:6} | {cnt:4} trades | avg: {avg:8.4f} | WR: {wr:6.1%}")
        
        # Degradação
        train_avg = df_res[df_res['phase'] == 'TRAIN']['return'].mean()
        test_avg = df_res[df_res['phase'] == 'TEST']['return'].mean()
        
        if train_avg != 0:
            deg = ((test_avg - train_avg) / abs(train_avg)) * 100
        else:
            deg = 0
        
        print(f"\n⚠️  DEGRADAÇÃO: {deg:.2f}%")
        
        if abs(deg) < 20:
            print("  ✅ CONSISTENTE")
        elif abs(deg) < 50:
            print("  ⚠️  MODERADA")
        else:
            print("  ❌ OVERFITTED")
        
        # Salva
        out = Path(__file__).parent.parent / "walk_forward_results.csv"
        df_res.to_csv(out, index=False)
        print(f"\n💾 Salvo em: {out}")
    else:
        print("\n❌ Nenhum trade gerado")


if __name__ == '__main__':
    main()

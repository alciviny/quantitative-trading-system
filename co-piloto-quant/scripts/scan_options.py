"""
Scanner de Opções Quantitativo — VERSÃO COM SIMULAÇÃO (FALLBACK)
Objetivo: Encontrar oportunidades. Se o Yahoo falhar (comum na B3), gera dados simulados para validar a lógica.
"""
import sys
import pandas as pd
import yfinance as yf
import numpy as np
import random
from datetime import datetime, timedelta
from joblib import Parallel, delayed
import os

# Ajuste de path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    from co_piloto_quant.pricing import implied_volatility, calculate_greeks, get_mid_price
except ImportError:
    print("ERRO: co_piloto_quant.pricing não encontrado.")
    sys.exit(1)

# === CONFIGURAÇÕES ===
ATIVO_OBJETO = "PETR4.SA"
RISK_FREE = 0.1225
MIN_LIQUIDEZ = 1       
DIAS_MIN_VENCIMENTO = 0
DIAS_MAX_VENCIMENTO = 90
USE_MOCK_ON_FAIL = True  # <--- NOVA FLAG: Ativa simulação se o Yahoo falhar

def generate_mock_options(spot_price):
    """Gera opções fictícias para testar o sistema quando a API falha."""
    print("\n⚠️  ATIVANDO MODO SIMULAÇÃO (MOCK) ⚠️")
    print("-> Gerando dados matemáticos coerentes para validar sua lógica de scanner...")
    
    mock_data = []
    # Cria vencimentos fictícios: 15 dias e 30 dias
    vencimentos = [
        datetime.now() + timedelta(days=15),
        datetime.now() + timedelta(days=35)
    ]
    
    # Gera Strikes de -10% a +10% do spot
    strikes = np.linspace(spot_price * 0.90, spot_price * 1.10, 15)
    
    for venc in vencimentos:
        dias_uteis = int((venc - datetime.now()).days * (252/365))
        T_years = dias_uteis / 252.0
        
        for K in strikes:
            # Simula um preço de mercado "justo" com uma Vol de 30% + ruído
            vol_simulada = 0.30 + (random.random() * 0.05) # 30% a 35%
            
            # Black-Scholes reverso para achar o preço dessa opção simulada
            # Usamos uma função simplificada aqui só pra gerar o preço
            from scipy.stats import norm
            d1 = (np.log(spot_price/K) + (RISK_FREE + 0.5*vol_simulada**2)*T_years) / (vol_simulada*np.sqrt(T_years))
            d2 = d1 - vol_simulada*np.sqrt(T_years)
            price_sim = spot_price * norm.cdf(d1) - K * np.exp(-RISK_FREE*T_years) * norm.cdf(d2)
            
            # Adiciona ruído de spread e liquidez
            bid = price_sim * 0.98
            ask = price_sim * 1.02
            last = price_sim
            vol = random.randint(50, 5000)
            
            mock_data.append({
                'contractSymbol': f"PETR{chr(65+random.randint(0,11))}{int(K)}", # Ex: PETRA32
                'strike': round(K, 2),
                'expiration': venc.strftime("%Y-%m-%d"),
                'type': 'call',
                'bid': bid,
                'ask': ask,
                'lastPrice': last,
                'volume': vol,
                'openInterest': vol * 10
            })
            
    return pd.DataFrame(mock_data)

def fetch_option_chain(ticker, spot_price):
    tk = yf.Ticker(ticker)
    
    try:
        exps = tk.options
        if not exps and USE_MOCK_ON_FAIL:
            print(f"DEBUG: Yahoo retornou vazio para {ticker}.")
            return generate_mock_options(spot_price)
    except Exception as e:
        print(f"Erro na conexão com Yahoo: {e}")
        if USE_MOCK_ON_FAIL: return generate_mock_options(spot_price)
        return pd.DataFrame()

    all_opts = []
    print(f"Baixando opções reais de {ticker}...")
    for date in exps:
        # (Lógica de download original mantida...)
        try:
            opt = tk.option_chain(date)
            calls = opt.calls
            if not calls.empty:
                calls['type'] = 'call'
                calls['expiration'] = date
                all_opts.append(calls)
        except: continue
            
    if not all_opts and USE_MOCK_ON_FAIL:
        return generate_mock_options(spot_price)
        
    return pd.concat(all_opts).reset_index(drop=True)

def process_option(row, spot_price):
    # Lógica de processamento IDÊNTICA à original
    # (Para validar que seu pricing.py funciona com qualquer dado)
    
    vol = row.get('volume', 0)
    if vol < MIN_LIQUIDEZ: return None

    # T
    vencimento = datetime.strptime(row['expiration'], "%Y-%m-%d")
    dias_corridos = (vencimento - datetime.now()).days
    dias_uteis = int(dias_corridos * (252/365))
    if dias_uteis < 1: dias_uteis = 1
    T_years = dias_uteis / 252.0

    # Preço
    price = get_mid_price(row.get('bid', 0), row.get('ask', 0), row.get('lastPrice', 0))
    if price <= 0.01: return None

    # IV e Gregas (Aqui testamos seu Módulo Pricing Real)
    iv = implied_volatility(price, spot_price, row['strike'], T_years, RISK_FREE, 'call')
    
    if pd.isna(iv) or iv <= 0: return None

    greeks = calculate_greeks(spot_price, row['strike'], T_years, RISK_FREE, iv, 'call')

    return {
        'Ticker': row['contractSymbol'],
        'Strike': row['strike'],
        'Preco': price,
        'Dias': dias_uteis,
        'IV': iv,
        'Delta': greeks['delta'],
        'Gamma': greeks['gamma'],
        'Theta': greeks['theta'],
        'Vega': greeks['vega']
    }

def main():
    print(f"--- SCANNER INICIADO: {ATIVO_OBJETO} ---")
    
    # 1. Spot
    try:
        spot_hist = yf.download(ATIVO_OBJETO, period="1d", progress=False)
        vals = spot_hist['Close']
        if isinstance(vals, pd.DataFrame): spot_price = float(vals.iloc[-1, 0])
        else: spot_price = float(vals.iloc[-1])
        print(f"Spot Real: R$ {spot_price:.2f}")
    except:
        spot_price = 30.00
        print(f"Spot Fallback: R$ {spot_price:.2f}")

    # 2. Busca Dados (Reais ou Mock)
    df_raw = fetch_option_chain(ATIVO_OBJETO, spot_price)
    
    # 3. Processamento
    results = Parallel(n_jobs=-1)(
        delayed(process_option)(row, spot_price) 
        for _, row in df_raw.iterrows()
    )
    
    clean_results = [r for r in results if r is not None]
    df = pd.DataFrame(clean_results)

    if df.empty:
        print("Nenhum resultado gerado.")
        return

    # 4. Exibição
    df = df.sort_values(by='IV')
    print("\n" + "="*95)
    print(f"RESULTADO DO SCANNER (Validando Lógica)")
    print("="*95)
    print(f"{'Ticker':<10} | {'Strike':<8} | {'Preço':<8} | {'Delta':<6} | {'IV':<6} | {'Theta':<8} | {'Gamma':<8}")
    print("-" * 95)

    for _, row in df.head(15).iterrows():
        print(f"{row['Ticker']:<10} | "
              f"{row['Strike']:<8.2f} | "
              f"{row['Preco']:<8.2f} | "
              f"{row['Delta']:.2f}   | "
              f"{row['IV']:.1%}  | "
              f"{row['Theta']:.3f}   | "
              f"{row['Gamma']:.3f}")
    print("-" * 95)

if __name__ == "__main__":
    main()
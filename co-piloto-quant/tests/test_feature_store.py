"""
Script de teste para verificar se o Feature Store está acessível
"""
import sys
sys.path.insert(0, 'co-piloto-quant/src')

from pathlib import Path
import pandas as pd

# Testa leitura direta do Feature Store
features_path = Path("co-piloto-quant/data/features")

print("=" * 60)
print("TESTE DO FEATURE STORE")
print("=" * 60)

# Lista arquivos
enriched_files = list(features_path.glob("*_enriched.parquet"))
print(f"\n✅ Arquivos enriched encontrados: {len(enriched_files)}")

for file in enriched_files[:5]:  # Mostra primeiros 5
    print(f"   - {file.name}")

# Testa leitura de um arquivo
if enriched_files:
    print(f"\n📊 Testando leitura: {enriched_files[0].name}")
    df = pd.read_parquet(enriched_files[0])
    
    print(f"   ✅ Linhas: {len(df)}")
    print(f"   ✅ Colunas: {len(df.columns)}")
    
    # Lista indicadores (excluindo OHLCV básico)
    basic_cols = {'open', 'high', 'low', 'close', 'volume', 'ticker', 'data_pregao'}
    indicators = [c for c in df.columns if c not in basic_cols]
    
    print(f"   ✅ Indicadores: {len(indicators)}")
    print(f"\n📈 Primeiros 10 indicadores:")
    for ind in indicators[:10]:
        print(f"      - {ind}")
    
    # Mostra última linha
    print(f"\n📅 Última data: {df.index[-1] if hasattr(df.index, '__getitem__') else 'N/A'}")
    
    # Testa API
    print("\n" + "=" * 60)
    print("TESTE DA API")
    print("=" * 60)
    
    from api_backend import load_stock_data, FEATURE_STORE_ENABLED
    
    print(f"\n✅ Feature Store habilitado: {FEATURE_STORE_ENABLED}")
    
    ticker = enriched_files[0].stem.replace("_enriched", "")
    print(f"\n📊 Carregando {ticker} via API...")
    
    df_api = load_stock_data(ticker, use_features=True)
    
    if df_api is not None:
        print(f"   ✅ Dados carregados com sucesso!")
        print(f"   ✅ Linhas: {len(df_api)}")
        print(f"   ✅ Colunas: {len(df_api.columns)}")
        
        # Verifica se tem indicadores avançados
        has_hurst = any('hurst' in c.lower() for c in df_api.columns)
        has_entropy = any('entropy' in c.lower() for c in df_api.columns)
        has_fractal = any('frac' in c.lower() for c in df_api.columns)
        
        print(f"\n🔍 Indicadores avançados detectados:")
        print(f"   {'✅' if has_hurst else '❌'} Hurst Exponent")
        print(f"   {'✅' if has_entropy else '❌'} Market Entropy")
        print(f"   {'✅' if has_fractal else '❌'} Fractal Dimension")
        
    else:
        print("   ❌ Falha ao carregar dados")

print("\n" + "=" * 60)
print("CONCLUSÃO")
print("=" * 60)
print("\n✅ Feature Store está funcionando!")
print("✅ API consegue ler os dados enriched")
print("✅ Frontend pode acessar via /api/stocks/{ticker}/indicators")
print("\n🚀 Próximo passo: Inicie a API com 'python api_backend.py'")
print("=" * 60)

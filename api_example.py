"""
Exemplo de API FastAPI para servir dados ao Frontend React

Instale: pip install fastapi uvicorn python-multipart aiofiles

Execute: uvicorn api_example:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import os
from typing import List, Optional

app = FastAPI(title="Co-Piloto Quant API")

# Configurar CORS para aceitar requisições do React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Caminho dos dados
DATA_PATH = "co-piloto-quant/data/results"

# Lista de ações disponíveis
STOCKS = [
    'ABEV3_SA', 'ALOS3_SA', 'ASAI3_SA', 'AURE3_SA', 'AZUL4_SA',
    'B3SA3_SA', 'BBAS3_SA', 'BBDC3_SA', 'BBDC4_SA', 'BBSE3_SA',
    'PETR3_SA', 'PETR4_SA', 'VALE3_SA', 'WEGE3_SA'
]

@app.get("/api/stocks")
async def get_available_stocks() -> List[str]:
    """Retorna lista de ações disponíveis"""
    return STOCKS

@app.get("/api/stocks/{stock}/metrics")
async def get_stock_metrics(stock: str, horizon: str = "5d"):
    """
    Retorna métricas de um ativo por horizonte
    
    Horizontes: 5d, 10d, 20d, 40d
    """
    try:
        filename = f"{stock}_metrics_{horizon}.csv"
        filepath = os.path.join(DATA_PATH, filename)
        
        if not os.path.exists(filepath):
            return {"error": f"Arquivo não encontrado: {filename}"}
        
        df = pd.read_csv(filepath)
        return df.to_dict(orient='records')
    
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/stocks/{stock}/vwap")
async def get_vwap_data(stock: str, period: str = "global"):
    """
    Retorna dados VWAP de um ativo
    
    Períodos: global, yearly
    """
    try:
        filename = f"{stock}_vwap_lab_{period}.csv"
        filepath = os.path.join(DATA_PATH, filename)
        
        if not os.path.exists(filepath):
            return {"error": f"Arquivo não encontrado: {filename}"}
        
        df = pd.read_csv(filepath)
        return df.to_dict(orient='records')
    
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/stocks/{stock}/returns")
async def get_forward_returns(stock: str, horizon: str = "5d"):
    """
    Retorna retornos futuros de um ativo
    
    Horizontes: 5d, 10d, 20d, 40d
    """
    try:
        filename = f"{stock}_fwd_ret_{horizon}.csv"
        filepath = os.path.join(DATA_PATH, filename)
        
        if not os.path.exists(filepath):
            return {"error": f"Arquivo não encontrado: {filename}"}
        
        df = pd.read_csv(filepath)
        return df.to_dict(orient='records')
    
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/stocks/{stock}/price-history")
async def get_price_history(stock: str, days: int = 365):
    """
    Retorna histórico de preços
    
    Nota: Esta é uma implementação stub.
    Integre com seu banco de dados ou yfinance para dados reais.
    """
    try:
        import yfinance as yf
        
        # Baixar dados do Yahoo Finance
        ticker = stock.replace('_SA', '.SA')
        df = yf.download(ticker, period=f"{days}d", progress=False)
        
        # Preparar dados
        df = df.reset_index()
        df['date'] = df['Date'].dt.strftime('%Y-%m-%d')
        
        data = []
        for _, row in df.iterrows():
            data.append({
                'date': row['date'],
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume'])
            })
        
        return data
    
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/health")
async def health_check():
    """Verificação de saúde da API"""
    return {
        "status": "ok",
        "service": "Co-Piloto Quant API",
        "version": "1.0.0"
    }

@app.get("/api/stats")
async def get_global_stats(horizon: str = "5d"):
    """Retorna estatísticas globais"""
    try:
        filename = f"global_stats_fwd_ret_{horizon}.csv"
        filepath = os.path.join(DATA_PATH, filename)
        
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            return df.to_dict(orient='records')
        
        return {"error": "Arquivo não encontrado"}
    
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

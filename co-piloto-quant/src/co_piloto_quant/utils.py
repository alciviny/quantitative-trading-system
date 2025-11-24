"""
Módulo de utilidades para fornecer listas de tickers e outras informações de apoio.
"""

def get_ibov_tickers():
    """
    Retorna uma lista completa de tickers que compõem o IBOVESPA.
    A lista foi compilada manualmente e pode precisar de atualizações periódicas.
    """
    return [
        "RRRP3.SA", "ALPA4.SA", "ABEV3.SA", "AMER3.SA", "ASAI3.SA", "AZUL4.SA", "B3SA3.SA", "BIDI11.SA",
        "BPAN4.SA", "BBSE3.SA", "BRML3.SA", "BBDC3.SA", "BBDC4.SA", "BRAP4.SA", "BBAS3.SA", "BRKM5.SA",
        "BRFS3.SA", "BPAC11.SA", "CRFB3.SA", "CCRO3.SA", "CMIG4.SA", "CIEL3.SA", "COGN3.SA", "CPLE6.SA",
        "CSAN3.SA", "CPFE3.SA", "CMIN3.SA", "CVCB3.SA", "CYRE3.SA", "DXCO3.SA", "ECOR3.SA", "ELET3.SA",
        "ELET6.SA", "EMBR3.SA", "ENBR3.SA", "ENGI11.SA", "ENEV3.SA", "EGIE3.SA", "EQTL3.SA", "EZTC3.SA",
        "FLRY3.SA", "GGBR4.SA", "GOAU4.SA", "GOLL4.SA", "NTCO3.SA", "SOMA3.SA", "HAPV3.SA", "HYPE3.SA",
        "IGTI11.SA", "IRBR3.SA", "ITSA4.SA", "ITUB4.SA", "JBSS3.SA", "JHSF3.SA", "KLBN11.SA", "RENT3.SA",
        "LWSA3.SA", "LREN3.SA", "MGLU3.SA", "MRFG3.SA", "CASH3.SA", "BEEF3.SA", "MRVE3.SA", "MULT3.SA",
        "PCAR3.SA", "PETR3.SA", "PETR4.SA", "PRIO3.SA", "PETZ3.SA", "QUAL3.SA", "RADL3.SA", "RAIL3.SA",
        "RDOR3.SA", "RAIZ4.SA", "SBSP3.SA", "SANB11.SA", "SMTO3.SA", "CSNA3.SA", "SLCE3.SA", "SUZB3.SA",
        "TAEE11.SA", "VIVT3.SA", "TIMS3.SA", "TOTS3.SA", "UGPA3.SA", "USIM5.SA", "VALE3.SA", "VIIA3.SA",
        "WEGE3.SA", "YDUQ3.SA"
    ]

def get_top_50_tickers():
    """
    Retorna os 50 primeiros tickers da lista do IBOVESPA.
    """
    return get_ibov_tickers()[:50]

if __name__ == '__main__':
    # Exemplo de uso e verificação
    all_tickers = get_ibov_tickers()
    top_50 = get_top_50_tickers()
    
    print(f"Total de tickers no IBOV: {len(all_tickers)}")
    print(f"Top 50 tickers: {len(top_50)}")
    print("Amostra (top 5):", top_50[:5])


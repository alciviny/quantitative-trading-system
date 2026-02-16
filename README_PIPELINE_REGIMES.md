# Pipeline Quantitativo: Detecção de Regimes de Mercado

## 1. Instalação de dependências

No terminal, ative o ambiente virtual e instale as dependências:
```sh
cd co-piloto-quant
./vbt_env/Scripts/activate
pip install -r requirements.txt
```

## 2. Baixar e processar dados de todos os ativos

Execute o script para baixar e calcular todas as features quantitativas:
```sh
python scripts/build_ml_dataset.py
```
- Os dados processados serão salvos em `data/processed/`.

## 3. Detectar regimes de mercado (HMM)

Execute o script de detecção de regimes:
```sh
python scripts/detect_market_regimes_hmm.py
```
- Os resultados dos regimes serão salvos em `data/results/reports/b3_market_dna.csv` e arquivos individuais em `data/results/`.

## 4. Analisar os resultados

- O arquivo `b3_market_dna.csv` traz, para cada ativo, o regime atual, scores de entropia, hurst, volatilidade e classificação (NORMAL, TÓXICO, TENDÊNCIA).
- Use pandas, Excel ou Google Sheets para filtrar, ordenar e visualizar os regimes.

---

Se quiser exemplos de análise em Python ou integração com dashboards, peça aqui!

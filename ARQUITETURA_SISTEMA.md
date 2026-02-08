# 📊 Arquitetura do Co-Piloto Quantitativo

## 🎯 Visão Geral do Sistema

O **Co-Piloto Quantitativo** é um sistema modular de análise de mercado financeiro composto por três camadas principais:

1. **Camada de Aquisição**: Baixa dados de mercado
2. **Camada de Processamento**: Calcula indicadores e features
3. **Camada de Visualização**: Exibe análises e resultados

---

## 📥 CAMADA 1: AQUISIÇÃO DE DADOS

Responsável por baixar e armazenar dados brutos de preços do mercado.

### 🔧 Arquivos Principais

#### **1.1 `src/co_piloto_quant/data/data_fetching.py`**
- **O quê**: Faz download de dados históricos OHLCV (Open, High, Low, Close, Volume)
- **Função principal**: `fetch_data(ticker, start, end, period, interval)`
- **Fonte**: Yahoo Finance via biblioteca `yfinance`
- **Saída**: DataFrame pandas com histórico de preços
- **Características**:
  - Suporta múltiplos períodos (1d, 1h, etc)
  - Tratamento de erros robusto
  - Logging detalhado

#### **1.2 `src/co_piloto_quant/data/data_manager.py`**
- **O quê**: Orquestra o armazenamento e recuperação de dados
- **Responsabilidades**:
  - Gerencia cache local (banco SQLite `market_data.db`)
  - Busca incremental (apenas novos dados)
  - Paralelização de downloads com `get_data_batch()`
  - Evita downloads redundantes

#### **1.3 `src/co_piloto_quant/data/database.py`**
- **O quê**: Abstração do banco de dados SQLite
- **Tabela principal**: `market_data` (OHLCV + timestamp + ticker)
- **Operações**:
  - Inserção de novos dados
  - Consulta de histórico
  - Limpeza de dados antigos

#### **1.4 `src/co_piloto_quant/universe.py`**
- **O quê**: Define quais ativos monitorar
- **Funções**:
  - `get_b3_tickers()`: Ativos da bolsa brasileira
  - `get_us_tech_tickers()`: Ações tech americanas
  - `get_expanded_universe()`: Todos os ativos do sistema
  - `get_scanner_tickers()`: Ativos em foco para análise

### 📍 Fluxo de Aquisição

```
Yahoo Finance
      ↓
data_fetching.py (fetch_data)
      ↓
data_manager.py (normaliza e valida)
      ↓
database.py (armazena em SQLite)
      ↓
market_data.db
```

### 🚀 Como Executar

```bash
# Atualizar dados para todo o universo
python scripts/update_market_data.py

# Ou programaticamente
from src.co_piloto_quant.data.data_manager import data_manager
df = data_manager.get_data("PETR4.SA")  # ticker específico
```

---

## 🔧 CAMADA 2: PROCESSAMENTO DE DADOS

Calcula indicadores técnicos e features para análise.

### 🎛️ Arquivos Principais

#### **2.1 `src/co_piloto_quant/feature_factory.py`** ⭐
- **O quê**: Fábrica central de features - orquestra todos os indicadores
- **Função principal**: `add_all_features(df)`
- **Responsabilidade**: Consolidar aplicação de TODAS as features em um único lugar
- **Como funciona**:
  - Recebe DataFrame com OHLCV
  - Aplica múltiplas famílias de indicadores
  - Retorna DataFrame enriquecido

#### **2.2 `src/co_piloto_quant/data/indicator_engine.py`**
- **O quê**: Motor genérico para cálculo de indicadores
- **Uso**: Aplicação padronizada de indicadores técnicos
- **Exemplo**:
  ```python
  engine = IndicatorEngine(df)
  engine.add_indicator('bollinger_bands', period=20)
  engine.add_indicator('ifr', period=14)
  engine.add_indicator('ema', period=50)
  df_result = engine.get_data()
  ```

#### **2.3 Módulos de Indicadores Técnicos** 
Localizados em `src/co_piloto_quant/indicators/`:

| Arquivo | Indicadores |
|---------|-----------|
| `bollinger_bands.py` | Bandas de Bollinger, desvio padrão móvel |
| `ifr_tpm.py` | Índice de Força Relativa (RSI) e variações |
| `stochastic_custom.py` | Oscilador Estocástico |
| `vwap_annual.py` | VWAP Annual (Price-Volume Analysis) |
| `system_tpm.py` | Sistema TPM customizado |
| `multi_bollinger_bands.py` | Múltiplas bandas com diferentes períodos |

#### **2.4 Indicadores Especiais** 
Localizados em `src/co_piloto_quant/indicators/special/`:

| Arquivo | O que Calcula | Propósito |
|---------|-------------|-----------|
| `hurst_exponent.py` | Expoente de Hurst | Detecta tendências vs. mean-reversion |
| `market_entropy.py` | Entropia de mercado | Mede ordem/caos do mercado |
| `half_life.py` | Half-life do processo OU | Tempo para mean-reversion |
| `fractal_dimension.py` | Dimensão fractal (FDI) | Complexidade do movimento de preço |
| `lempel_ziv.py` | Complexidade Lempel-Ziv | Compressibilidade da série |
| `frac_diff.py` | Diferenciação fracionária | Preserva memória enquanto remove tendência |

### 📊 Famílias de Indicadores

O `feature_factory.py` organiza indicadores em "famílias":

1. **Base Técnica** (`add_base_technical_indicators`)
   - Bollinger Bands
   - RSI (IFR)
   - Estocástico
   - EMAs (50, 200)

2. **Física de Mercado** (`add_market_physics_indicators`)
   - Hurst 72 períodos
   - Entropia 20 períodos
   - Half-Life 60 períodos
   - Dimensão Fractal
   - Complexidade Lempel-Ziv

3. **Volatilidade** (`add_volatility_indicators`)
   - Volatilidade móvel (20d)
   - Vol-of-Vol (volatilidade da volatilidade)

4. **Momentum** (`add_momentum_indicators`)
   - MACD
   - Rate of Change (ROC)

5. **Retornos** (`add_forward_return_targets`)
   - Retorno futuro 5d
   - Retorno futuro 10d
   - Retorno futuro 20d

### 🔄 Fluxo de Processamento

```
market_data.db (dados brutos OHLCV)
      ↓
data_processing.py (carrega e limpa)
      ↓
feature_factory.py (add_all_features)
      ↓
  ├─→ indicator_engine.py (técnicos básicos)
  ├─→ hurst_exponent.py (física)
  ├─→ market_entropy.py (física)
  ├─→ volatility (vol, vol-of-vol)
  ├─→ momentum (MACD, ROC)
  └─→ targets (retornos futuros)
      ↓
DataFrame enriquecido com 50+ features
```

### 💾 Saídas do Processamento

- **CSV**: `data/processed/` (dados processados)
- **Parquet ML-Ready**: `data/ml_ready/` (otimizado para ML)
- **Relatórios**: `data/reports/` (estatísticas)

### 🚀 Como Usar

```python
from src.co_piloto_quant.feature_factory import add_all_features
import pandas as pd

# Carregar dados
df = pd.read_csv('data/raw/PETR4_SA.csv')

# Adicionar todas as features
df_enriched = add_all_features(df)

# Salvar resultado
df_enriched.to_csv('data/processed/PETR4_SA_features.csv')
```

---

## 📈 CAMADA 3: VISUALIZAÇÃO E ANÁLISE

Exibe resultados de análise e backtests em dashboards interativos.

### 📱 Dashboard Principal

#### **`scripts/run_dashboard.py`** ⭐
- **O quê**: Dashboard Streamlit interativo
- **Linguagem**: Python + Streamlit + Plotly
- **Características**:
  - Seletor de ativo por ticker
  - Múltiplas abas de análise
  - Gráficos interativos (zoom, pan)
  - Análise de trades históricos
  - Estatísticas de performance

**Como executar**:
```bash
streamlit run scripts/run_dashboard.py
```

**Funcionalidades**:
1. **Análise Técnica Visual**: Preço + Bollinger Bands + Indicadores
2. **DNA do Ativo**: Estatísticas de comportamento histórico
3. **Backtest Forensics**: Análise de trades passados
4. **Tabelas de Dados**: Dados brutos para inspeção

### 📊 Scripts de Visualização Especializados

#### **`scripts/visualize_indicator.py`**
- Plota indicadores customizados
- Suporta múltiplos gráficos lado a lado
- Usa Plotly para interatividade

#### **`scripts/simulaVwap.py`**
- Análise de VWAP por faixas de preço
- Heatmaps de performance
- Métricas de regime de preço

### 📉 Scripts de Backtesting e Análise

| Script | Propósito |
|--------|----------|
| `run_backtest.py` | Backtest de estratégia com otimização de parâmetros |
| `walk_forward_validation.py` | Validação walk-forward (treinar/testar em janelas) |
| `walk_forward_from_stress.py` | Walk-forward após teste de stress |
| `stress_test_monte_carlo.py` | Monte Carlo para análise de risco |
| `app_backtest.py` | Interface web para backtests |
| `forensic_analysis.py` | Análise forense de operações |

### 🏥 Health Check e Monitoramento

#### **`scripts/health_check.py`**
- Verifica integridade do banco de dados
- Valida últimos downloads
- Confirma disponibilidade de ativos

```bash
python scripts/health_check.py
```

### 🚀 Como Usar a Visualização

```bash
# Dashboard principal
streamlit run scripts/run_dashboard.py

# Visualizar indicador específico
python scripts/visualize_indicator.py --ticker PETR4.SA

# Correr backtest
python scripts/run_backtest.py --ticker PETR4.SA
```

---

## 🔌 INTEGRAÇÕES E FLUXO COMPLETO

### 🌊 Fluxo End-to-End

```mermaid
┌─────────────────────────────────────────────────────────────┐
│               VISÃO GERAL DO SISTEMA                         │
└─────────────────────────────────────────────────────────────┘

1. AQUISIÇÃO
   ↓
   └─→ update_market_data.py
       └─→ data_fetching.py (Yahoo Finance)
           └─→ database.py (SQLite)

2. PROCESSAMENTO
   ↓
   └─→ build_ml_dataset.py OU scripts de análise
       └─→ data_processing.py
           └─→ feature_factory.py
               └─→ indicator_engine.py + indicadores especiais
                   └─→ data/processed/ + data/ml_ready/

3. ANÁLISE
   ↓
   ├─→ build_dna_b3.py (calcula características dos ativos)
   ├─→ detect_toxicity.py (detecta movimentos anormais)
   └─→ lab_vwap_*.py (análises de regime de preço)

4. VISUALIZAÇÃO
   ↓
   └─→ run_dashboard.py
       ├─→ Gráficos técnicos (Plotly)
       ├─→ Métricas (Streamlit)
       └─→ Tabelas interativas
```

### 🔄 Ciclo de Atualização Recomendado

```bash
# Diariamente, após mercado fechar:

# 1. Baixar novos dados
python scripts/update_market_data.py

# 2. Verificar saúde
python scripts/health_check.py

# 3. Reconstruir dataset ML (se houver mudanças)
python scripts/build_ml_dataset.py

# 4. Recalcular DNA (características dos ativos)
python scripts/build_dna_b3.py

# 5. Visualizar resultados
streamlit run scripts/run_dashboard.py
```

---

## 📚 ESTRUTURA DE PASTAS EXPLICADA

```
co-piloto-quant/
│
├── src/co_piloto_quant/          ← CÓDIGO-FONTE (a "Caixa de Ferramentas")
│   ├── data/                      ← Módulo de Aquisição
│   │   ├── data_fetching.py      (baixa dados)
│   │   ├── data_manager.py       (orquestra cache)
│   │   ├── database.py           (acesso SQLite)
│   │   ├── data_processing.py    (limpeza)
│   │   ├── indicator_engine.py   (motor de indicadores)
│   │   └── market_data.db        (banco de dados)
│   │
│   ├── indicators/                ← Módulo de Indicadores
│   │   ├── bollinger_bands.py
│   │   ├── ifr_tpm.py
│   │   ├── stochastic_custom.py
│   │   ├── vwap_annual.py
│   │   ├── system_tpm.py
│   │   └── special/
│   │       ├── hurst_exponent.py
│   │       ├── market_entropy.py
│   │       ├── half_life.py
│   │       ├── fractal_dimension.py
│   │       ├── lempel_ziv.py
│   │       └── frac_diff.py
│   │
│   ├── feature_factory.py         ← ORQUESTRADOR CENTRAL
│   ├── universe.py                (lista de ativos)
│   ├── pricing.py                 (Black-Scholes, gregas)
│   └── risk_regime.py             (validação de regimes)
│
├── scripts/                        ← "MANUAL DE INSTRUÇÕES"
│   ├── update_market_data.py      (👈 COMECE AQUI: baixa dados)
│   ├── build_ml_dataset.py        (👈 DEPOIS: calcula features)
│   ├── build_dna_b3.py            (👈 DEPOIS: análise de ativos)
│   ├── run_dashboard.py           (👈 VISUALIZAR: dashboard web)
│   ├── run_backtest.py            (testa estratégias)
│   ├── walk_forward_validation.py (validação em janelas)
│   ├── stress_test_monte_carlo.py (análise de risco)
│   ├── health_check.py            (verifica sistema)
│   └── [20+ outros scripts]
│
├── data/
│   ├── raw/                       (dados brutos baixados)
│   ├── processed/                 (dados processados)
│   ├── ml_ready/                  (parquets para ML)
│   └── results/                   (outputs de análises)
│
├── models/                        (modelos treinados)
│   ├── market_brain_rf.joblib
│   ├── features_list.joblib
│   └── feature_importance.joblib
│
├── tests/                         ← TESTES AUTOMATIZADOS
│   ├── test_core_functions.py
│   └── test_main.py
│
└── docs/
    ├── DATA_FLOW.md              (este arquivo!)
    ├── workflow_instrucoes.md
    └── scanner_logic.md
```

---

## 🎓 GUIA DE USO PARA INICIANTES

### Primeiro Contato

1. **Instalar dependências**:
   ```bash
   pip install -e .
   ```

2. **Baixar dados iniciais**:
   ```bash
   python scripts/update_market_data.py
   ```

3. **Verificar se tudo funcionou**:
   ```bash
   python scripts/health_check.py
   ```

4. **Visualizar um ativo**:
   ```bash
   python scripts/visualize_indicator.py --ticker PETR4.SA
   ```

5. **Abrir dashboard**:
   ```bash
   streamlit run scripts/run_dashboard.py
   ```

### Adicionar Novo Indicador

1. Criar arquivo em `src/co_piloto_quant/indicators/`:
   ```python
   # novo_indicador.py
   def calculate_novo_indicador(df, params):
       # seu código
       return df
   ```

2. Adicionar à `feature_factory.py`:
   ```python
   def add_novo_indicador(df):
       from .indicators.novo_indicador import calculate_novo_indicador
       df['novo_ind'] = calculate_novo_indicador(df, params)
       return df
   ```

3. Chamar em `add_all_features()`:
   ```python
   def add_all_features(df):
       df = add_base_technical_indicators(df)
       df = add_novo_indicador(df)  # ← NOVO
       ...
   ```

---

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| `ModuleNotFoundError` | Execute `pip install -e .` no diretório raiz |
| Sem dados baixados | Rode `python scripts/update_market_data.py` |
| Dashboard não abre | Verifique: `pip install streamlit plotly` |
| Lentidão ao processar | Use `--ticker` para processar um ativo por vez |
| Erros de memória | Reduza horizonte histórico em `data_fetching.py` |

---

## 📞 Resumo de Arquivos Críticos

| Arquivo | Função | Status |
|---------|--------|--------|
| `src/co_piloto_quant/data/data_fetching.py` | Baixa dados | Core ✅ |
| `src/co_piloto_quant/feature_factory.py` | Calcula indicadores | Core ✅ |
| `scripts/run_dashboard.py` | Visualiza análises | Core ✅ |
| `scripts/update_market_data.py` | Atualiza DB | Útil 🔧 |
| `scripts/build_ml_dataset.py` | Prepara ML | Opcional 📊 |
| `src/co_piloto_quant/universe.py` | Define ativos | Core ✅ |
| `src/co_piloto_quant/data/database.py` | Armazena dados | Core ✅ |

---

## 🤖 Ajuda de Agentes IA

Para entender o que agentes de IA podem fazer para ajudar no desenvolvimento, manutenção e expansão deste sistema, consulte:

📖 **[CAPACIDADES_AGENTE_IA.md](CAPACIDADES_AGENTE_IA.md)** - Guia completo sobre capacidades de agentes de IA neste projeto

---

**Última atualização**: 8 de fevereiro de 2026  
**Versão do Projeto**: 0.1.0

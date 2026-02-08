# 🎯 EXEMPLO VISUAL - O QUE VOCÊ VAI VER

Após executar `start-all.bat`, você verá:

## 🖥️ Terminal 1 - API Backend

```
======================================== 
🚀 Co-Piloto Quant API v2.0
======================================== 
📦 Parquet: C:\...\co-piloto-quant\data\processed
📊 Results: C:\...\co-piloto-quant\data\results
🌐 URL: http://localhost:8000
📖 Docs: http://localhost:8000/docs
======================================== 
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
✅ 74 ações encontradas em C:\...\data\processed
```

---

## 🌐 Terminal 2 - Frontend React

```
Compiled successfully!

You can now view copiloto-quant-frontend in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.1.10:3000

Note that the development build is not optimized.
To create a production build, use npm run build.

webpack compiled successfully
```

---

## 🌐 Navegador - Dashboard

### Header (Topo)
```
┌──────────────────────────────────────────────────────┐
│ 📊 Co-piloto Quant Dashboard                        │
│ Análise Quantitativa de Preços em Tempo Real        │
└──────────────────────────────────────────────────────┘
```

### Seletor de Ações
```
┌──────────────────────────────────────────────────────┐
│ Selecione uma Ação: [PETR4 ▼]                      │
│                                                      │
│ Opções disponíveis:                                  │
│   ABEV3, ALOS3, ASAI3, AURE3, AZUL4                 │
│   B3SA3, BBAS3, BBDC3, BBDC4, BBSE3                 │
│   PETR3, PETR4, VALE3, WEGE3                        │
│   ... (70+ ações)                                    │
└──────────────────────────────────────────────────────┘
```

### KPI Cards (4 Cards em Destaque)
```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ 📈       │ │ 💰       │ │ ✓        │ │ 📊       │
│ Preço    │ │ Retorno  │ │ Taxa de  │ │ Volati-  │
│ Atual    │ │ Médio    │ │ Acerto   │ │ lidade   │
│          │ │          │ │          │ │          │
│ R$ 28.45 │ │ +0.82%   │ │ 51.0%    │ │ 3.74%    │
│ ▲ +1.2%  │ │          │ │          │ │          │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
  (verde)      (azul)       (azul)       (roxo)
```

### Abas de Navegação
```
┌──────────────────────────────────────────────────────┐
│ [📈 Preço] [📊 Métricas VWAP] [💰 Retornos]        │
└──────────────────────────────────────────────────────┘
```

---

## 📈 Aba 1: Preço

### Gráfico Principal (Área)
```
┌──────────────────────────────────────────────────────┐
│ 📈 Gráfico de Preço - Últimos 30 dias               │
│ Min: R$ 27.80  |  Max: R$ 29.10  |  Atual: R$ 28.45 │
│                                                      │
│  30 ┤                              ╭─╮              │
│  29 ┤                     ╭────╮  ╭╯  ╰╮            │
│  28 ┤        ╭───╮    ╭──╯      ╰─╯     ╰─╮        │
│  27 ┤   ╭───╯     ╰───╯                    ╰─      │
│  26 ┤ ──╯                                           │
│     └───┬───┬───┬───┬───┬───┬───┬───┬───┬───       │
│       01/01  05/01  10/01  15/01  20/01  25/01     │
│                                                      │
│ Área preenchida em azul (gradiente)                 │
└──────────────────────────────────────────────────────┘
```

### Gráfico de Volume
```
┌──────────────────────────────────────────────────────┐
│ 📊 Volume de Negociação                             │
│                                                      │
│ 2M ┤     ▂   ▅   ▁       ▄       ▂                  │
│ 1M ┤   ▅ █ ▇ █ ▃ █   ▂ ▆ █   ▁ ▅ █                  │
│    └───┬───┬───┬───┬───┬───┬───┬───┬───             │
│      01/01    10/01    20/01    30/01               │
└──────────────────────────────────────────────────────┘
```

---

## 📊 Aba 2: Métricas VWAP

### Gráfico 1: Retorno Médio por Z-Score
```
┌──────────────────────────────────────────────────────┐
│ Retorno Médio por Z-Score                           │
│                                                      │
│  3% ┤   ██                                          │
│  2% ┤   ██                                          │
│  1% ┤   ██  ▆▆              ▆▆                      │
│  0% ┤  ─────────██──────────────██──                │
│ -1% ┤           ██              ██  ▆▆              │
│ -2% ┤                               ██              │
│     └─────┬─────┬─────┬─────┬─────┬─────           │
│         Muito  Barato Neutro Caro Muito            │
│         Barato                     Caro             │
│                                                      │
│ Cores: Verde = positivo, Vermelho = negativo        │
└──────────────────────────────────────────────────────┘
```

### Gráfico 2: Taxa de Acerto
```
┌──────────────────────────────────────────────────────┐
│ Taxa de Acerto                                      │
│                                                      │
│ 90% ┤  ██                                           │
│ 70% ┤  ██                                           │
│ 50% ┤  ██  ██──────██──────██──────                 │
│ 30% ┤                          ██                    │
│ 10% ┤                                               │
│     └─────┬─────┬─────┬─────┬─────┬─────           │
│         Muito  Barato Neutro Caro Muito            │
│         Barato                     Caro             │
└──────────────────────────────────────────────────────┘
```

### Scatter Plot: Volatilidade vs Taxa de Acerto
```
┌──────────────────────────────────────────────────────┐
│ 📊 Análise VWAP - Volatilidade vs Taxa de Acerto   │
│                                                      │
│ Taxa                                                 │
│ 90% ┤  ●                                            │
│ 70% ┤                                               │
│ 50% ┤      ●   ●   ●●●   ●   ●                      │
│ 30% ┤                          ●                     │
│ 10% ┤                                               │
│     └────┬────┬────┬────┬────┬────                  │
│        0.02  0.03  0.04  0.05                       │
│              Volatilidade                            │
│                                                      │
│ Cada ponto = uma faixa de preço                     │
└──────────────────────────────────────────────────────┘
```

### Métricas Resumidas
```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Volatilidade │ │ Taxa Acerto  │ │ Retorno      │
│ Média        │ │ Média        │ │ Médio        │
│              │ │              │ │              │
│   3.21%      │ │   50.45%     │ │   0.82%      │
└──────────────┘ └──────────────┘ └──────────────┘
```

---

## 💰 Aba 3: Retornos

### Gráfico Combinado (Barras + Linha)
```
┌──────────────────────────────────────────────────────┐
│ 💰 Análise de Retornos                              │
│                                                      │
│  3% ┤   ██                      ●───                │
│  2% ┤   ██              ●───●                       │
│  1% ┤   ██  ▆▆      ●───────●  ▆▆                  │
│  0% ┤  ─────────██──────────────────██──            │
│ -1% ┤       ●   ██      ●       ●   ██  ▆▆          │
│ -2% ┤                   ●               ██          │
│     └─────┬─────┬─────┬─────┬─────┬─────           │
│         Muito  Barato Neutro Caro Muito            │
│         Barato                     Caro             │
│                                                      │
│ Azul = Ret. Médio | Roxo = Ret. Mediano             │
│ Verde ● = Índice Sharpe (linha)                    │
└──────────────────────────────────────────────────────┘
```

### Tabela Resumo
```
┌────────────────┬──────┬────────┬────────┬────────┐
│ Faixa de Preço │ Qtd. │ Ret.   │ Ret.   │ Sharpe │
│                │      │ Médio  │ Median │        │
├────────────────┼──────┼────────┼────────┼────────┤
│ Muito Barato   │   7  │ +2.14% │ +1.67% │ +59.4  │
│ Barato         │ 108  │ +0.33% │ +0.19% │ +12.3  │
│ Leve Desc      │ 203  │ -0.25% │ -0.45% │  -9.6  │
│ Neutro         │ 200  │ +0.82% │ +0.07% │ +21.9  │
│ Leve Premio    │ 289  │ +0.18% │ -0.07% │  +7.0  │
│ Caro           │  96  │ -1.16% │ -1.18% │ -34.7  │
│ Muito Caro     │  16  │ -0.26% │ +0.69% │  -5.1  │
└────────────────┴──────┴────────┴────────┴────────┘
```

### Cards de Destaque
```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Melhor       │ │ Pior         │ │ Total de     │
│ Retorno      │ │ Retorno      │ │ Observações  │
│ Médio        │ │ Médio        │ │              │
│              │ │              │ │              │
│  +2.14%      │ │  -1.16%      │ │    919       │
│  (verde)     │ │  (vermelho)  │ │    (azul)    │
└──────────────┘ └──────────────┘ └──────────────┘
```

---

## 🎨 Paleta de Cores

```
Fundo Principal:  #0f172a → #1e293b (gradiente escuro)
Primária (Azul):  #3b82f6 (destaque, links, gráficos)
Sucesso (Verde):  #22c55e (retornos positivos)
Erro (Vermelho):  #ef4444 (retornos negativos)
Roxo:             #8b5cf6 (volume, secundário)
Laranja:          #f59e0b (alertas, warnings)
Texto Claro:      #e2e8f0
Texto Médio:      #cbd5e1
Texto Suave:      #94a3b8
```

---

## 📱 Design Responsivo

### Desktop (1920px)
```
┌────────────────────────────────────────┐
│              Header                     │
├────────────────────────────────────────┤
│ [Seletor]                              │
├─────────┬─────────┬─────────┬─────────┤
│  KPI 1  │  KPI 2  │  KPI 3  │  KPI 4  │
├────────────────────────────────────────┤
│ [Aba1] [Aba2] [Aba3]                  │
├──────────────────┬─────────────────────┤
│   Gráfico 1      │    Gráfico 2       │
├──────────────────┴─────────────────────┤
│           Tabela/Métricas              │
└────────────────────────────────────────┘
```

### Mobile (375px)
```
┌──────────────┐
│   Header     │
├──────────────┤
│  [Seletor]   │
├──────────────┤
│    KPI 1     │
├──────────────┤
│    KPI 2     │
├──────────────┤
│    KPI 3     │
├──────────────┤
│    KPI 4     │
├──────────────┤
│ [Abas]       │
├──────────────┤
│  Gráfico 1   │
├──────────────┤
│  Gráfico 2   │
├──────────────┤
│   Tabela     │
└──────────────┘
```

---

## ⚡ Interatividade

### Hover (Mouse sobre elemento)
- Cards: Elevam 5px + sombra
- Botões: Mudam cor + background
- Gráficos: Tooltip com valores

### Click
- Seletor: Dropdown com busca
- Abas: Transição suave 0.3s
- Gráfico: Zoom/Pan (futuro)

### Animações
- Fade in: 0.3s (ao trocar aba)
- Slide up: Cards ao carregar
- Pulse: Indicador de loading

---

## 🔄 Atualização em Tempo Real

### Fluxo:
```
1. Usuário seleciona ação
   ↓
2. Frontend faz 4 requests paralelos:
   - GET /api/stocks/{stock}/price-history
   - GET /api/stocks/{stock}/metrics?horizon=5d
   - GET /api/stocks/{stock}/vwap?period=global
   - GET /api/stocks/{stock}/returns?horizon=5d
   ↓
3. API lê do Parquet/CSV (< 100ms)
   ↓
4. Frontend renderiza:
   - KPI Cards atualizam
   - Gráficos redesenham
   - Tabelas populam
   ↓
5. Pronto em 1-2 segundos!
```

---

## ✨ Recursos Visuais

### Gradientes
```css
background: linear-gradient(135deg, 
  #0f172a 0%,    /* Azul escuro */
  #1e293b 100%   /* Azul médio */
);
```

### Sombras
```css
box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);  /* Header */
box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);  /* Cards */
```

### Borders
```css
border: 1px solid rgba(59, 130, 246, 0.2);  /* Azul suave */
border-radius: 0.75rem;                      /* Arredondado */
```

### Backdrop Blur
```css
backdrop-filter: blur(10px);  /* Efeito vidro fosco */
```

---

**Isso é o que você vai ver! 🎉**

Execute `start-all.bat` e confira você mesmo!

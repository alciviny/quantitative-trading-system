# Guia de Instalação e Uso - Frontend React

## 🚀 Inicialização Rápida

### Windows
1. Duplo-clique em `setup.bat`
2. Aguarde a instalação das dependências
3. O navegador abrirá automaticamente em `http://localhost:3000`

### macOS/Linux
```bash
chmod +x setup.sh
./setup.sh
```

## 📋 Requisitos

- **Node.js 16+** ([Download](https://nodejs.org/))
- **npm** (incluso com Node.js)

## 🛠️ Instalação Manual

```bash
cd frontend-react
npm install
npm start
```

## 📊 O que você vai ver

O dashboard exibe:

✅ **Seletor de Ações** - Escolha qualquer ação do índice B3
✅ **KPI Cards** - Preço atual, retorno médio, taxa de acerto, volatilidade
✅ **Gráfico de Preço** - Últimos 30 dias com área preenchida
✅ **Volume de Negociação** - Visualização de volume em gráfico de área
✅ **Análise VWAP** - Scatter plot com volatilidade vs taxa de acerto
✅ **Métricas** - Retorno médio e taxa de acerto por faixa de preço
✅ **Análise de Retornos** - Tabela comparativa com Índice Sharpe

## 🔗 Integração com API Backend

Para conectar com sua API Python, crie um arquivo `.env` na pasta `frontend-react`:

```
REACT_APP_API_URL=http://localhost:8000/api
```

Depois crie os endpoints esperados em sua aplicação Python.

## 🎨 Customização

### Mudar cores
Edite `src/App.css` e altere os valores de `background` e cores

### Adicionar mais gráficos
Crie novos componentes em `src/components/charts/`

### Mudar horizonte de preço
Em `src/components/charts/PriceChart.js`, altere `data.slice(-30)` para o número de dias desejado

## 🐛 Troubleshooting

### npm: comando não encontrado
→ Instale Node.js de https://nodejs.org/

### Porta 3000 já está em uso
```bash
npm start -- --port 3001
```

### CORS error
→ Configure CORS na sua API Python:
```python
from flask_cors import CORS
CORS(app)
```

## 📱 Responsividade

O dashboard foi desenvolvido para funcionar perfeitamente em:
- 📺 Desktop (1920px+)
- 💻 Laptop (1024px)
- 📱 Tablet (768px)
- 📲 Mobile (320px+)

## 🚀 Build para Produção

```bash
npm run build
```

Cria pasta `build/` com arquivos otimizados para produção.

## 📞 Suporte

Consulte `README.md` para mais informações técnicas.

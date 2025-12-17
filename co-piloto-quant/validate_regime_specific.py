#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_regime_specific.py
Valida ideia de sistemas específicos por regime
"""

import pandas as pd
import numpy as np

print("\n" + "="*80)
print("🎯 VALIDAÇÃO: SISTEMAS ESPECÍFICOS POR REGIME")
print("="*80)

# Lê dados
df = pd.read_csv('walk_forward_results.csv')

# Stress test original para comparação
stress_test_data = {
    'BULL_CALM': {'trades': 74, 'avg_return': 0.028445, 'win_rate': 0.486486},
    'SIDEWAYS_VOLATILE': {'trades': 12, 'avg_return': 0.026750, 'win_rate': 0.583333},
    'SIDEWAYS_CALM': {'trades': 52, 'avg_return': 0.005449, 'win_rate': 0.269231},
    'BULL_VOLATILE': {'trades': 19, 'avg_return': 0.000156, 'win_rate': 0.210526},
}

print("\n📊 ANÁLISE POR REGIME (Walk-Forward)\n")

results_summary = []

for regime in sorted(df['regime'].unique()):
    regime_df = df[df['regime'] == regime]
    
    train_df = regime_df[regime_df['phase'] == 'TRAIN']
    test_df = regime_df[regime_df['phase'] == 'TEST']
    
    train_count = len(train_df)
    test_count = len(test_df)
    
    train_avg = train_df['return'].mean() if train_count > 0 else 0
    train_wr = (train_df['return'] > 0).mean() if train_count > 0 else 0
    
    test_avg = test_df['return'].mean() if test_count > 0 else 0
    test_wr = (test_df['return'] > 0).mean() if test_count > 0 else 0
    
    # Degradação
    if train_avg != 0:
        degradation = ((test_avg - train_avg) / abs(train_avg)) * 100
    else:
        degradation = 0
    
    # Profit factor
    gains = train_df[train_df['return'] > 0]['return'].sum()
    losses = abs(train_df[train_df['return'] < 0]['return'].sum())
    pf = gains / losses if losses > 0 else (float('inf') if gains > 0 else 0)
    
    print(f"📌 {regime}")
    print(f"   {'─'*75}")
    print(f"   TREINO:     {train_count:3} trades | {train_avg:8.4f} ret | {train_wr:6.1%} WR | PF: {pf:.2f}x")
    print(f"   TESTE:      {test_count:3} trades | {test_avg:8.4f} ret | {test_wr:6.1%} WR")
    print(f"   DEGRADAÇÃO: {degradation:7.1f}%")
    
    # Comparação com stress test
    if regime in stress_test_data:
        st_data = stress_test_data[regime]
        print(f"   STRESS TEST: {st_data['trades']:3} trades | {st_data['avg_return']:.4f} ret | {st_data['win_rate']:.1%} WR")
    
    # Viabilidade
    print(f"   ", end="")
    if train_count > 0:
        viability = []
        
        if train_avg > 0.01:  # >1% é bom
            viability.append("✅ Retorno positivo")
        elif train_avg > 0:
            viability.append("⚠️  Retorno pequeno")
        else:
            viability.append("❌ Retorno negativo")
        
        if train_wr > 0.50:
            viability.append("✅ Win rate bom")
        elif train_wr > 0.40:
            viability.append("⚠️  Win rate mediano")
        else:
            viability.append("❌ Win rate baixo")
        
        if abs(degradation) < 30:
            viability.append("✅ Consistente")
        elif abs(degradation) < 50:
            viability.append("⚠️  Degradação moderada")
        else:
            viability.append("❌ Overfitted")
        
        if pf > 1.5:
            viability.append("✅ Profit factor bom")
        elif pf > 1.0:
            viability.append("⚠️  Profit factor aceitável")
        else:
            viability.append("❌ Profit factor ruim")
        
        if train_count > 30:
            viability.append("✅ N amostral OK")
        else:
            viability.append("⚠️  Poucas amostras")
        
        print(" | ".join(viability))
    else:
        print("❌ Sem trades de treino")
    
    print()
    
    # Salva resumo
    results_summary.append({
        'regime': regime,
        'train_trades': train_count,
        'test_trades': test_count,
        'train_ret': train_avg,
        'test_ret': test_avg,
        'train_wr': train_wr,
        'test_wr': test_wr,
        'degradation': degradation,
        'profit_factor': pf
    })

print("\n" + "="*80)
print("📋 RANKING: QUAL REGIME ESCOLHER?")
print("="*80)

# Scoring
for item in results_summary:
    score = 0
    details = []
    
    if item['train_ret'] > 0.01:
        score += 3
        details.append("Retorno excelente")
    elif item['train_ret'] > 0:
        score += 1
        details.append("Retorno positivo")
    
    if item['train_wr'] > 0.50:
        score += 2
        details.append("WR > 50%")
    elif item['train_wr'] > 0.40:
        score += 1
        details.append("WR aceitável")
    
    if abs(item['degradation']) < 30:
        score += 2
        details.append("Consistente WF")
    
    if item['profit_factor'] > 1.5:
        score += 2
        details.append("PF excelente")
    elif item['profit_factor'] > 1.0:
        score += 1
        details.append("PF aceitável")
    
    if item['train_trades'] > 30:
        score += 1
        details.append("Bom N amostral")
    
    item['score'] = score
    item['details'] = details

# Ordena por score
results_summary.sort(key=lambda x: x['score'], reverse=True)

for rank, item in enumerate(results_summary, 1):
    print(f"\n{rank}. {item['regime']:20} | Score: {item['score']}/12")
    print(f"   {item['train_trades']:3} trades TRAIN | {item['train_ret']:.4f} ret | {item['profit_factor']:.2f} PF")
    print(f"   {item['test_trades']:3} trades TEST")
    if item['details']:
        print(f"   Pontos: {', '.join(item['details'])}")
    
    # Recomendação
    if item['score'] >= 8:
        print(f"   ✅ VIÁVEL! Criar sistema dedicado para {item['regime']}")
    elif item['score'] >= 5:
        print(f"   ⚠️  QUESTIONÁVEL - Testar mais antes de usar")
    else:
        print(f"   ❌ NÃO RECOMENDADO")

print("\n" + "="*80)
print("💡 CONCLUSÃO")
print("="*80)

best = results_summary[0] if results_summary else None
if best and best['score'] >= 5:
    print(f"""
Sua ideia de criar sistemas por regime é VÁLIDA!

Recomendação:
1. ✅ Crie um sistema dedicado para {best['regime']}
   - Melhor performance: {best['train_ret']*100:.2f}% retorno
   - Profit Factor: {best['profit_factor']:.2f}x

2. ⚠️ Para os outros regimes:
   - Descarte ou melhore os parâmetros
   - Não use um único sistema para todos os regimes
   
3. 🎯 Próximo passo:
   - Otimize parâmetros APENAS para {best['regime']}
   - Teste com dados mais longos de {best['regime']}
   - Implemente filtro de regime para desativar em outros mercados
""")
else:
    print("""
Nenhum regime mostrou performance suficiente.

Você precisa:
1. ❌ Revisar os parâmetros da estratégia
2. ❌ Considerar indicadores diferentes
3. ❌ Aumentar o período de lookback (>12 meses)
4. ❌ Testar em dados mais antigos
""")

print("="*80)

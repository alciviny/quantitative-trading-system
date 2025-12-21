import os
import shutil
from pathlib import Path

# Configuração
PROJECT_ROOT = Path(__file__).parent
LEGACY_DIR = PROJECT_ROOT / "_LEGACY_BACKUP"
CO_PILOTO_DIR = PROJECT_ROOT / "co-piloto-quant"

# Lista explícita de arquivos e pastas para mover para maior segurança
# Paths são relativos ao diretório 'co-piloto-quant'
FILES_TO_MOVE = [
    # Scripts de análise e debug na raiz de co-piloto-quant
    "analyze_atr.py",
    "analyze_bull_calm.py",
    "analyze_parameters.py",
    "analyze_winning_regimes.py",
    "check_dates.py",
    "compare_stress_vs_wf.py",
    "debug_monte_carlo.py",
    "debug_trades.py",
    "deep_analysis.py",
    "extract_regime_subset.py",
    "find_best_regimes.py",
    "monte_carlo_on_subset.py",
    "monte_carlo_with_position_sizing.py",
    "optimize_targets.py",
    "pareto_analysis.py",
    "quick_analysis.py",
    "quick_debug.py",
    "test_parameter_sweep.py",
    "validate_data_integrity.py",
    "validate_regime_specific.py",
    "what_it_takes.py",
    
    # Scripts de teste descartáveis em scripts/
    "scripts/test_dry_run.py",
    "scripts/test_mt5.py",
    "scripts/test_refactoring.py",
    "scripts/teste_infra.py",

    # Arquivos de resultados (CSV/TXT) na raiz de co-piloto-quant
    "atr_multiplier_comparison.csv",
    "bull_volatile_subset.csv",
    "mc_dynamic_sizing_bull_volatile.csv",
    "momentum_all_regimes_results.csv",
    "momentum_BEAR_VOLATILE_results.csv",
    "momentum_BULL_VOLATILE_results.csv",
    "monte_carlo_bull_volatile.csv",
    "relatorio_final_bull_volatile.txt",
    "sanity_report.csv",
    "swing_bear_calm_atr_2.0.csv",
    "swing_bear_calm_atr_2.5.csv",
    "swing_bear_calm_atr_3.0.csv",
    "swing_bear_calm_atr_3.5.csv",
    "swing_bear_calm_results.csv",
    "swing_strategy_results.csv",
    "walk_forward_extended_results.csv",
    "walk_forward_optimized_results.csv",
    "walk_forward_results.csv",
]

def safe_cleanup():
    """Move arquivos e pastas legadas para um diretório de backup."""
    print(f"🧹 Iniciando limpeza do projeto em: {CO_PILOTO_DIR}")
    print(f"📦 Itens movidos irão para: {LEGACY_DIR}")
    
    if not LEGACY_DIR.exists():
        LEGACY_DIR.mkdir()

    moved_count = 0

    for item_path_str in FILES_TO_MOVE:
        source_path = CO_PILOTO_DIR / item_path_str
        dest_path = LEGACY_DIR / source_path.name

        if source_path.exists():
            try:
                print(f" -> Movendo: {'co-piloto-quant/' + item_path_str}")
                shutil.move(str(source_path), str(dest_path))
                moved_count += 1
            except Exception as e:
                print(f" ❌ Erro ao mover {source_path.name}: {e}")
        else:
            print(f" ⚠️  Aviso: Item não encontrado, pulando: {source_path}")

    print("-" * 50)
    if moved_count > 0:
        print(f"✅ Limpeza concluída. {moved_count} itens movidos para '{LEGACY_DIR.name}'.")
        print("Verifique a pasta de backup. Se tudo estiver ok, você pode deletá-la manualmente.")
    else:
        print("✅ Nenhum item legado encontrado para mover.")

if __name__ == "__main__":
    safe_cleanup()

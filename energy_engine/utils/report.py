import pandas as pd
from energy_engine.utils.log import log

def save_report(report_rows, output_path):
    """Salva um relatório comparativo de métricas em CSV."""
    df_report = pd.DataFrame(report_rows)
    df_report.to_csv(output_path, index=False)
    log(f'Relatório comparativo salvo em {output_path}')
    log(df_report)
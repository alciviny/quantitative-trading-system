
import pandas as pd
from .multi_bollinger_bands import multi_bollinger_bands
from .on_balance_true_range import on_balance_true_range
from .williams_ad import williams_ad
from .names import IndicatorNames

def calculate_system_tpm(
    data: pd.DataFrame, 
    indicator: str = 'obtr', 
    period: int = 200, 
    deviations: list = [0.45, 1.0, 1.5, 2.0]
) -> pd.DataFrame:
    """
    Calcula o "System TPM", que consiste em aplicar as Bandas de Bollinger Múltiplas
    sobre um indicador base (OBTR ou Williams A/D), usando a nomenclatura padronizada.

    Args:
        data (pd.DataFrame): O DataFrame contendo os dados de preço (OHLC).
        indicator (str, optional): O indicador base a ser usado. 
                                   Pode ser 'obtr' ou 'wad'. Default é 'obtr'.
        period (int, optional): O período para as bandas. Default é 200.
        deviations (list, optional): A lista de desvios para as bandas. 
                                      Default é [0.45, 1.0, 1.5, 2.0].

    Returns:
        pd.DataFrame: Um DataFrame contendo o indicador base e suas respectivas
                      bandas de Bollinger múltiplas, com nomes padronizados.
    """
    if indicator not in [IndicatorNames.obtr(), IndicatorNames.wad()]:
        raise ValueError(f"O indicador deve ser '{IndicatorNames.obtr()}' ou '{IndicatorNames.wad()}'.")

    # Calcula o indicador base (as funções já usam IndicatorNames)
    if indicator == IndicatorNames.obtr():
        indicator_series = on_balance_true_range(data)[IndicatorNames.obtr()]
    elif indicator == IndicatorNames.wad():
        indicator_series = williams_ad(data) # Retorna uma série com o nome correto

    # Calcula as bandas de Bollinger múltiplas sobre o indicador
    bb_df = multi_bollinger_bands(
        data=indicator_series,
        period=period,
        deviations=deviations
    )

    # Renomeia as colunas do bb_df para o padrão do sistema usando IndicatorNames
    new_column_names = {}
    for col_name in bb_df.columns:
        if 'middle' in col_name:
            new_column_names[col_name] = IndicatorNames.tpm_band(indicator, period, 'middle')
        elif 'upper' in col_name or 'lower' in col_name:
            try:
                parts = col_name.split('_')
                band_type = parts[0]
                dev_str = parts[-1]
                dev = float(dev_str.replace('_', '.'))
                new_column_names[col_name] = IndicatorNames.tpm_band(indicator, period, band_type, dev)
            except (IndexError, ValueError) as e:
                # Ignora colunas que não seguem o padrão esperado
                print(f"Aviso: não foi possível parsear a coluna '{col_name}' em calculate_system_tpm. Erro: {e}")
                continue
    
    bb_df = bb_df.rename(columns=new_column_names)

    # Combina o indicador original com suas bandas
    result_df = pd.concat([indicator_series.to_frame(), bb_df], axis=1)

    return result_df

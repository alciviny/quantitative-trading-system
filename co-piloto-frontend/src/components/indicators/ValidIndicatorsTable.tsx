import React from 'react';

export interface ValidIndicatorAsset {
  ticker: string;
  close: number;
  indicators: Record<string, number>;
}

interface Props {
  assets: ValidIndicatorAsset[];
  requiredIndicators: string[];
}

/**
 * Exibe apenas ativos que possuem todos os indicadores obrigatórios e fechamento válido.
 */
export const ValidIndicatorsTable: React.FC<Props> = ({ assets, requiredIndicators }) => {
  // Filtra ativos que têm todos os indicadores obrigatórios e fechamento
  const validAssets = assets.filter(asset => {
    if (typeof asset.close !== 'number' || isNaN(asset.close)) return false;
    return requiredIndicators.every(ind =>
      typeof asset.indicators[ind] === 'number' && !isNaN(asset.indicators[ind])
    );
  });

  if (validAssets.length === 0) {
    return <div className="p-4 text-gray-500">Nenhum ativo com todos os indicadores disponíveis.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border text-xs">
        <thead>
          <tr>
            <th className="border px-2 py-1">Ticker</th>
            <th className="border px-2 py-1">Fechamento</th>
            {requiredIndicators.map(ind => (
              <th key={ind} className="border px-2 py-1">{ind.replace(/_/g, ' ')}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {validAssets.map(asset => (
            <tr key={asset.ticker}>
              <td className="border px-2 py-1 font-mono">{asset.ticker}</td>
              <td className="border px-2 py-1">{asset.close.toFixed(2)}</td>
              {requiredIndicators.map(ind => (
                <td key={ind} className="border px-2 py-1">{asset.indicators[ind]?.toFixed(3)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

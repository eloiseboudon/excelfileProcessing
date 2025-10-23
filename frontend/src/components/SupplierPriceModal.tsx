import React, { useEffect, useMemo, useState } from 'react';

interface SupplierCalculationDetails {
  price?: number;
  tcp?: number;
  marge45?: number;
  marge?: number;
  margePercent?: number | null;
  prixhtTcpMarge45?: number;
  prixhtMarge45?: number;
  prixhtMax?: number;
  stock?: number;
  updatedAt?: string | null;
}

interface SupplierPriceModalProps {
  prices?: Record<string, number | undefined>;
  stocks?: Record<string, number | undefined>;
  calculations?: Record<string, SupplierCalculationDetails>;
  currentMargin?: number;
  currentMarginPercent?: number | null;
  baseCost: number;
  recommendedPrice?: number;
  onUpdateMargin: (margin: number, marginPercent: number | null) => Promise<void>;
  onClose: () => void;
}

const numberFormatter = new Intl.NumberFormat('fr-FR', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const formatCurrency = (value?: number | null) =>
  typeof value === 'number' && Number.isFinite(value)
    ? `${numberFormatter.format(value)} €`
    : '—';

const formatPercent = (value?: number | null) =>
  typeof value === 'number' && Number.isFinite(value)
    ? `${numberFormatter.format(value)} %`
    : '—';

const formatPlainNumber = (value?: number | null) =>
  typeof value === 'number' && Number.isFinite(value)
    ? numberFormatter.format(value)
    : '—';

const formatDate = (value?: string | null) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('fr-FR');
};

const parseInputNumber = (value: string) => {
  if (!value.trim()) {
    return NaN;
  }
  const normalized = value.replace(',', '.');
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : NaN;
};

function SupplierPriceModal({
  prices = {},
  stocks = {},
  calculations = {},
  currentMargin = 0,
  currentMarginPercent = null,
  baseCost,
  recommendedPrice,
  onUpdateMargin,
  onClose,
}: SupplierPriceModalProps) {
  const supplierSet = useMemo(
    () =>
      new Set<string>([
        ...Object.keys(prices || {}),
        ...Object.keys(stocks || {}),
        ...Object.keys(calculations || {}),
      ]),
    [prices, stocks, calculations]
  );
  const suppliers = useMemo(
    () => Array.from(supplierSet).sort((a, b) => a.localeCompare(b)),
    [supplierSet]
  );

  const [marginEuro, setMarginEuro] = useState(() => currentMargin.toFixed(2));
  const [marginPercent, setMarginPercent] = useState(() => {
    if (typeof currentMarginPercent === 'number' && Number.isFinite(currentMarginPercent)) {
      return currentMarginPercent.toFixed(2);
    }
    if (baseCost) {
      return ((currentMargin / baseCost) * 100).toFixed(2);
    }
    return '';
  });
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setMarginEuro(currentMargin.toFixed(2));
    if (typeof currentMarginPercent === 'number' && Number.isFinite(currentMarginPercent)) {
      setMarginPercent(currentMarginPercent.toFixed(2));
    } else if (baseCost) {
      setMarginPercent(((currentMargin / baseCost) * 100).toFixed(2));
    } else {
      setMarginPercent('');
    }
  }, [currentMargin, currentMarginPercent, baseCost]);

  const computedMarginEuro = parseInputNumber(marginEuro);
  const computedRecommendedPrice = Number.isNaN(computedMarginEuro)
    ? recommendedPrice ?? baseCost
    : Number(((baseCost || 0) + computedMarginEuro).toFixed(2));

  const handleEuroChange = (value: string) => {
    setMarginEuro(value);
    const parsed = parseInputNumber(value);
    if (!Number.isNaN(parsed) && baseCost) {
      setMarginPercent(((parsed / baseCost) * 100).toFixed(2));
    }
  };

  const handlePercentChange = (value: string) => {
    setMarginPercent(value);
    const parsed = parseInputNumber(value);
    if (!Number.isNaN(parsed) && baseCost) {
      setMarginEuro((baseCost * (parsed / 100)).toFixed(2));
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (isSaving) return;

    const marginValue = parseInputNumber(marginEuro);
    if (Number.isNaN(marginValue)) {
      setError('Veuillez saisir une marge en euros valide.');
      return;
    }

    let percentValue: number | null = null;
    const percentParsed = parseInputNumber(marginPercent);
    if (!Number.isNaN(percentParsed)) {
      percentValue = percentParsed;
    } else if (baseCost) {
      percentValue = Number(((marginValue / baseCost) * 100).toFixed(4));
    }

    setError(null);
    setIsSaving(true);
    try {
      await onUpdateMargin(marginValue, percentValue);
    } catch {
      setError("Erreur lors de l'enregistrement de la marge.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-zinc-900 p-6 rounded-lg border border-zinc-700 w-full max-w-5xl mx-4">
        <h2 className="text-xl font-semibold mb-4">
          Dernières données calculées par fournisseur
        </h2>

        <form onSubmit={handleSubmit} className="mb-6 space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">Marge (€)</span>
              <input
                type="number"
                step="0.01"
                value={marginEuro}
                onChange={(e) => handleEuroChange(e.target.value)}
                className="rounded border border-zinc-600 bg-zinc-800 px-3 py-2"
              />
            </label>
            <label className="flex flex-col text-sm">
              <span className="mb-1 font-medium">Marge (%)</span>
              <input
                type="number"
                step="0.01"
                value={marginPercent}
                onChange={(e) => handlePercentChange(e.target.value)}
                className="rounded border border-zinc-600 bg-zinc-800 px-3 py-2"
                disabled={!baseCost}
              />
              {!baseCost && (
                <span className="mt-1 text-xs text-zinc-400">
                  Impossible de calculer le pourcentage : prix d&apos;achat ou TCP manquant.
                </span>
              )}
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-sm text-zinc-300">
            <span>Base (PA + TCP)&nbsp;: {formatCurrency(baseCost)}</span>
            <span>Prix de vente HT recalculé&nbsp;: {formatCurrency(computedRecommendedPrice)}</span>
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <div className="flex justify-end">
            <button type="submit" className="btn btn-primary" disabled={isSaving}>
              {isSaving ? 'Enregistrement…' : 'Mettre à jour la marge'}
            </button>
          </div>
        </form>

        {suppliers.length ? (
          <div className="overflow-auto max-h-[60vh]">
            <table className="table mb-4 min-w-full">
              <thead>
                <tr>
                  <th>Fournisseur</th>
                  <th>Prix achat</th>
                  <th>Prix HT max</th>
                  <th>TCP</th>
                  <th>Marge (€)</th>
                  <th>Marge (%)</th>
                  <th>Stock</th>
                  <th>Mise à jour</th>
                </tr>
              </thead>
              <tbody>
                {suppliers.map((s) => (
                  <tr key={s}>
                    <td>{s}</td>
                    <td>{formatCurrency(calculations[s]?.price ?? prices[s])}</td>
                    <td>{formatCurrency(calculations[s]?.prixhtMax)}</td>
                    <td>{formatCurrency(calculations[s]?.tcp)}</td>
                    <td>{formatCurrency(calculations[s]?.marge)}</td>
                    <td>{formatPercent(calculations[s]?.margePercent)}</td>
                    <td>{formatPlainNumber(calculations[s]?.stock ?? stocks?.[s])}</td>
                    <td>{formatDate(calculations[s]?.updatedAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>Aucun prix disponible.</p>
        )}
        <div className="text-right space-x-2">
          <button onClick={onClose} className="btn btn-secondary" type="button">
            Fermer
          </button>
        </div>
      </div>
    </div>
  );
}

export default SupplierPriceModal;

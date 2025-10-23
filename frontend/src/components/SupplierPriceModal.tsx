import React from 'react';

interface SupplierCalculationDetails {
  price?: number;
  tcp?: number;
  marge45?: number;
  marge?: number;
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
  onClose: () => void;
}

function SupplierPriceModal({
  prices = {},
  stocks = {},
  calculations = {},
  onClose,
}: SupplierPriceModalProps) {
  const supplierSet = new Set<string>([
    ...Object.keys(prices || {}),
    ...Object.keys(stocks || {}),
    ...Object.keys(calculations || {}),
  ]);
  const suppliers = Array.from(supplierSet).sort((a, b) => a.localeCompare(b));
  const formatNumber = (value?: number | null) =>
    typeof value === 'number' && Number.isFinite(value)
      ? value.toLocaleString('fr-FR', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      : '—';

  const formatDate = (value?: string | null) => {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '—';
    return date.toLocaleString('fr-FR');
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-zinc-900 p-6 rounded-lg border border-zinc-700 w-full max-w-5xl mx-4">
        <h2 className="text-xl font-semibold mb-4">
          Dernières données calculées par fournisseur
        </h2>
        {suppliers.length ? (
          <div className="overflow-auto max-h-[70vh]">
            <table className="table mb-4 min-w-full">
              <thead>
                <tr>
                  <th>Fournisseur</th>
                  <th>Prix achat</th>
                  <th>Prix HT max</th>
                  <th>TCP</th>
                  <th>Marge</th>
                  <th>Stock</th>
                  <th>Mise à jour</th>
                </tr>
              </thead>
              <tbody>
                {suppliers.map((s) => (
                  <tr key={s}>
                    <td>{s}</td>
                    <td>{formatNumber(calculations[s]?.price ?? prices[s])}</td>
                    <td>
                      {formatNumber(
                        calculations[s]?.prixhtMax ?? calculations[s]?.prixhtMarge45 ?? undefined
                      )}
                    </td>
                    <td>{formatNumber(calculations[s]?.tcp)}</td>
                    <td>{formatNumber(calculations[s]?.marge)}</td>
                    <td>{formatNumber(calculations[s]?.stock ?? stocks?.[s])}</td>
                    <td>{formatDate(calculations[s]?.updatedAt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>Aucun prix disponible.</p>
        )}
        <div className="text-right">
          <button onClick={onClose} className="btn btn-primary">
            Fermer
          </button>
        </div>
      </div>
    </div>
  );
}

export default SupplierPriceModal;

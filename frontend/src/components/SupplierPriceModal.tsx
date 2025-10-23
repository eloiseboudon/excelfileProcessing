import React from 'react';

interface SupplierPriceModalProps {
  prices: Record<string, number | undefined>;
  stocks?: Record<string, number | undefined>;
  onClose: () => void;
}

function SupplierPriceModal({ prices, stocks, onClose }: SupplierPriceModalProps) {
  const supplierSet = new Set<string>([
    ...Object.keys(prices || {}),
    ...Object.keys(stocks || {}),
  ]);
  const suppliers = Array.from(supplierSet).sort((a, b) => a.localeCompare(b));
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-zinc-900 p-6 rounded-lg border border-zinc-700 w-96">
        <h2 className="text-xl font-semibold mb-4">
          Prix de vente moyen et stock par fournisseur
        </h2>
        {suppliers.length ? (
          <table className="table mb-4">
            <thead>
              <tr>
                <th>Fournisseur</th>
                <th>Prix</th>
                <th>Stock</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((s) => (
                <tr key={s}>
                  <td>{s}</td>
                  <td>{prices[s] ?? '—'}</td>
                  <td>{stocks?.[s] ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
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

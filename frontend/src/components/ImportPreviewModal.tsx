import React from 'react';

interface PreviewRow {
  [key: string]: string | number | null;
}

interface ImportPreviewModalProps {
  rows: PreviewRow[];
  onClose: () => void;
}

function ImportPreviewModal({ rows, onClose }: ImportPreviewModalProps) {
  const headers = rows.length > 0 ? Object.keys(rows[0]) : [];
  return (
    <div className="fixed inset-0 bg-[var(--color-bg-overlay)] flex items-center justify-center z-50">
      <div className="bg-[var(--color-bg-surface)] p-6 rounded-lg border border-[var(--color-border-default)] max-w-4xl w-5/6">
        <h2 className="text-xl font-semibold mb-4">Prévisualisation de l'import</h2>
        {rows.length > 0 ? (
          <div className="overflow-auto max-h-[60vh] mb-4">
            <table className="table">
              <thead>
                <tr>
                  {headers.map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, idx) => (
                  <tr key={idx}>
                    {headers.map((h) => (
                      <td key={h}>{(r as any)[h]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>Aucune donnée de prévisualisation.</p>
        )}
        <div className="text-right">
          <button onClick={onClose} className="btn btn-primary">Fermer</button>
        </div>
      </div>
    </div>
  );
}

export default ImportPreviewModal;

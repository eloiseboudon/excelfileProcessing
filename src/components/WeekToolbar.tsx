import React, { useCallback, useMemo, useState } from 'react';
import { Download } from 'lucide-react';
import { exportCalculations, refreshProduction, refreshProductionByWeek } from '../api';
import { getCurrentTimestamp, getCurrentWeekYear } from '../utils/date';

function WeekToolbar() {
  const [message, setMessage] = useState<string | null>(null);

  const getStartOfWeek = (date: Date) => {
    const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
    const day = (d.getUTCDay() + 6) % 7;
    d.setUTCDate(d.getUTCDate() - day);
    d.setUTCHours(0, 0, 0, 0);
    return d;
  };

  const getISOWeek = (date: Date) => {
    const tmp = new Date(date);
    tmp.setDate(tmp.getDate() + 4 - (tmp.getDay() || 7));
    const yearStart = new Date(Date.UTC(tmp.getFullYear(), 0, 1));
    return Math.ceil(((tmp.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  };

  const weekOptions = useMemo(() => {
    const today = new Date();
    const start = getStartOfWeek(today);
    return Array.from({ length: 4 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() - i * 7);
      return { label: `Semaine ${getISOWeek(d)}`, value: d.toISOString() };
    });
  }, []);

  const handleDownload = useCallback(async () => {
    setMessage(null);
    try {
      const { blob, filename } = await exportCalculations();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || `product_calculates_${getCurrentTimestamp()}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch {
      setMessage('Erreur lors du téléchargement');
    }
  }, []);

  const handleRefresh = useCallback(async () => {
    setMessage(null);
    try {
      await refreshProduction();
      setMessage('Données de prod mises à jour');
    } catch {
      setMessage("Erreur lors du rafraîchissement des données de prod");
    }
  }, []);

  const handleRefreshWeek = useCallback(async (weekStart: Date) => {
    setMessage(null);
    try {
      await refreshProductionByWeek([weekStart]);
      setMessage('Semaine mise à jour');
    } catch {
      setMessage("Erreur lors du rafraîchissement des données de la semaine");
    }
  }, []);

  return (
    <div className="mb-4">
      <div className="flex flex-col sm:flex-row sm:justify-between items-center gap-4">
        <div className="flex items-center gap-4">
          <span className="text-zinc-400">Semaine en cours : {getCurrentWeekYear()}</span>
          <button
            onClick={handleDownload}
            className="px-4 py-2 bg-[#B8860B] text-black rounded-lg flex items-center space-x-2 hover:bg-[#B8860B]/90 font-semibold"
          >
            <Download className="w-5 h-5" />
            <span>Télécharger</span>
          </button>
        </div>
        <div className="flex flex-col items-end gap-2">
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-[#B8860B] text-black rounded-lg hover:bg-[#B8860B]/90 font-semibold"
          >
            Tout rafraîchir
          </button>
          <select
            defaultValue=""
            onChange={async (e) => {
              if (e.target.value) {
                await handleRefreshWeek(new Date(e.target.value));
                e.target.value = '';
              }
            }}
            className="px-4 py-2 bg-[#B8860B] text-black rounded-lg hover:bg-[#B8860B]/90 font-semibold cursor-pointer"
          >
            <option value="">Rafraîchir une semaine</option>
            {weekOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      {message && (
        <p className="text-center text-sm text-zinc-400 mt-2">{message}</p>
      )}
    </div>
  );
}

export default WeekToolbar;

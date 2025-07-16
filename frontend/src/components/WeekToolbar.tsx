import { useCallback, useState } from 'react';
import { exportCalculations } from '../api';
import { getCurrentTimestamp, getCurrentWeekYear } from '../utils/date';

function WeekToolbar() {
  const [message, setMessage] = useState<string | null>(null);
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
      setMessage('Le téléchargement du fichier a échoué. Veuillez réessayer.');
    }
  }, []);

  return (
    <div className="mb-4">
      <div className="flex flex-col sm:flex-row sm:justify-between items-center gap-4">
        <div className="flex items-center gap-4">
          <span className="text-zinc-400">Semaine en cours : {getCurrentWeekYear()}</span>
          {/* <button
            onClick={handleDownload}
            className="px-4 py-2 bg-[#B8860B] text-black rounded-lg flex items-center space-x-2 hover:bg-[#B8860B]/90 font-semibold"
          >
            <Download className="w-5 h-5" />
            <span>Télécharger</span>
          </button> */}
        </div>
      </div>
      {message && (
        <p className="text-center text-sm text-zinc-400 mt-2">{message}</p>
      )}
    </div>
  );
}

export default WeekToolbar;

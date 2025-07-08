import React, { useState } from 'react';
import { ArrowLeft, Download } from 'lucide-react';
import { exportCalculations } from '../api';
import { getCurrentWeekYear } from '../utils/date';

interface FormattingPageProps {
  onBack: () => void;
}

function FormattingPage({ onBack }: FormattingPageProps) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const blob = await exportCalculations();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `product_calculates_${getCurrentWeekYear()}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error downloading file:', err);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <div className="flex items-center justify-between mb-8">
        <button
          onClick={onBack}
          className="flex items-center space-x-2 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Retour à l'étape 1</span>
        </button>
      </div>
      <h1 className="text-4xl font-bold text-center mb-2">Étape 2 - Téléchargement</h1>
      <p className="text-center text-zinc-400 mb-12">Semaine {getCurrentWeekYear()}</p>
      <div className="flex justify-center">
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="px-8 py-4 bg-[#B8860B] text-black rounded-lg flex items-center space-x-2 hover:bg-[#B8860B]/90 transition-colors font-semibold disabled:opacity-50"
        >
          <Download className="w-6 h-6" />
          <span>Télécharger fichier</span>
        </button>
      </div>
    </div>
  );
}

export default FormattingPage;

import {
  ArrowRight,
  ChevronRight,
  Download,
  FileDown,
  FileUp,
  Loader2,
} from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';
import {
  calculateProducts,
  createImport,
  fetchImportPreview,
  fetchLastImport,
  fetchSuppliers,
  verifyImport
} from '../api';
import { useNotification } from './NotificationProvider';
import ImportPreviewModal from './ImportPreviewModal';
import { getCurrentTimestamp, getCurrentWeekYear, getWeekYear } from '../utils/date';


interface ProcessingPageProps {
  onNext: () => void;
}

interface Supplier {
  id: number;
  name: string;
  email?: string;
  phone?: string;
  address?: string;
}

interface ImportZoneProps {
  supplier: Supplier;
  file: File | null;
  lastImportDate?: string | null;
  onFileChange: (id: number, file: File | null) => void;
}

function ImportZone({ supplier, file, lastImportDate, onFileChange }: ImportZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [previewRows, setPreviewRows] = useState<any[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const notify = useNotification();

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const droppedFile = e.dataTransfer.files[0];
      if (
        droppedFile?.type ===
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
        droppedFile?.type === 'application/vnd.ms-excel'
      ) {
        onFileChange(supplier.id, droppedFile);
        previewFile(droppedFile);
      }
    },
    [supplier.id, onFileChange]
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0];
      if (selectedFile) {
        onFileChange(supplier.id, selectedFile);
        previewFile(selectedFile);
      }
    },
    [supplier.id, onFileChange]
  );

  const previewFile = useCallback(
    async (f: File) => {
      setPreviewLoading(true);
      try {
        const res = await fetchImportPreview(f, supplier.id);
        setPreviewRows(res.preview || []);
        setShowPreview(true);
      } catch (err) {
        console.error('preview error', err);
        notify('Erreur lors de la prévisualisation du fichier', 'error');
      } finally {
        setPreviewLoading(false);
      }
    },
    [supplier.id]
  );

  return (
    <div className="card p-8">
      <h2 className="text-xl font-semibold mb-6">Import de {supplier.name}</h2>
      {lastImportDate && (
        <p className="text-sm text-zinc-400 mb-2">
          Dernier import : {getWeekYear(new Date(lastImportDate))} -{' '}
          {new Date(lastImportDate).toLocaleDateString('fr-FR',
            {
              year: 'numeric',
              month: '2-digit',
              day: '2-digit',
            }
          )} </p>
      )}
      <div
        className={`border-2 border-dashed rounded-xl p-8 transition-all duration-200 ${isDragging ? 'border-[#B8860B] bg-black/50' : 'border-zinc-700 hover:border-[#B8860B]/50'
          }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="flex flex-col items-center justify-center space-y-4">
          <FileUp className="w-12 h-12 text-[#B8860B]" />
          <p className="text-lg text-zinc-300">Glissez votre fichier Excel ici ou</p>
          <label className="btn btn-primary cursor-pointer">
            Sélectionnez un fichier
            <input type="file" className="hidden" accept=".xlsx,.xls" onChange={handleFileChange} />
          </label>
        </div>
      </div>
      {file && (
        <>
          <div className="mt-4 flex items-center space-x-3 p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
            <FileDown className="w-6 h-6 text-[#B8860B]" />
            <span className="text-zinc-300 truncate flex-1">{file.name}</span>
            <button onClick={() => previewFile(file)} className="btn btn-secondary ml-auto">Prévisualiser</button>
          </div>
          {previewLoading && (
            <p className="text-sm text-zinc-400 mt-2">Chargement de la prévisualisation...</p>
          )}
        </>
      )}
      {showPreview && (
        <ImportPreviewModal rows={previewRows} onClose={() => setShowPreview(false)} />
      )}
    </div>
  );
}

function ProcessingPage({ onNext }: ProcessingPageProps) {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [files, setFiles] = useState<Record<number, File | null>>({});
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedFile, setProcessedFile] = useState<string | null>(null);
  const [processedFileName, setProcessedFileName] = useState<string>('');
  const [lastImports, setLastImports] = useState<Record<number, string | null>>({});
  const [error, setError] = useState<string | null>(null);
  const notify = useNotification();



  const refreshLastImports = useCallback(async () => {
    const entries = await Promise.all(
      suppliers.map(async (s) => {
        try {
          const data = await fetchLastImport(s.id);
          const date = (data as any).import_date || null;
          return [s.id, date] as [number, string | null];
        } catch {
          return [s.id, null] as [number, string | null];
        }
      })
    );
    setLastImports(Object.fromEntries(entries));
  }, [suppliers]);


  const handleFileChange = useCallback(
    (id: number, file: File | null) => {
      setFiles((prev) => ({ ...prev, [id]: file }));
      setProcessedFile(null);
      setError(null);
    },
    []
  );

  const processAll = useCallback(async () => {
    setIsProcessing(true);
    setError(null);

    try {
      for (const f of suppliers) {
        const file = files[f.id];
        if (file) {
          try {
            const check = await verifyImport(f.id);
            if (check.status === 'error') {
              const confirmOverride = window.confirm(
                `Un import a déjà été réalisé cette semaine pour ${f.name}. Voulez-vous écraser les données ?`
              );
              if (!confirmOverride) {
                continue;
              }
            }
          } catch {
            // ignore verification errors and proceed
          }
          const res = await createImport(file, f.id);
          notify(`Import de ${f.name} réussi (${res.new} lignes)`, 'success');
        }
      }

      const calc = await calculateProducts();
      notify(`Calculs terminés (${calc.created} enregistrements)`, 'success');

      await refreshLastImports();

    } catch (err) {
      console.error('Error processing files:', err);
      setError(
        err instanceof Error
          ? err.message
          : 'Le traitement des fichiers a échoué. Veuillez vérifier les fichiers et réessayer.'
      );
      notify('Erreur lors du traitement des fichiers', 'error');
      setProcessedFile(null);
    } finally {
      setIsProcessing(false);
    }
  }, [files, suppliers, refreshLastImports]);

  useEffect(() => {
    fetchSuppliers()
      .then(setSuppliers)
      .catch(() => { });
  }, []);

  useEffect(() => {
    if (suppliers.length > 0) {
      refreshLastImports();
    }
  }, [suppliers, refreshLastImports]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-4xl font-bold text-center mb-2">Étape 1 - Calculs et Traitement</h1>
      <p className="text-center text-[#B8860B] mb-4">Traitez vos fichiers Excel avec calculs TCP et marges</p>
      <p className="text-center text-zinc-400 mb-4">Semaine en cours : {getCurrentWeekYear()}</p>
      <div className="flex justify-center mb-8">
        <button
          onClick={() => {
            if (!processedFile) return;
            const link = document.createElement('a');
            link.href = processedFile;
            link.download =
              processedFileName || `product_calculates_${getCurrentTimestamp()}.xlsx`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          }}
          className="btn btn-primary px-6 py-3 flex items-center space-x-2"
        >
          <Download className="w-5 h-5" />
          <span>Télécharger</span>
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {suppliers.map((f) => (
          <ImportZone
            key={f.id}
            supplier={f}
            file={files[f.id] || null}
            lastImportDate={lastImports[f.id]}
            onFileChange={handleFileChange}
          />
        ))}
      </div>

      <div className="mt-8 flex flex-col items-center space-y-4">
        <button
          onClick={processAll}
          disabled={isProcessing}
          className="btn btn-primary px-6 py-3 flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Traitement...</span>
            </>
          ) : (
            <>
              <ArrowRight className="w-5 h-5" />
              <span>Traiter</span>
            </>
          )}
        </button>

        {error && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg w-full text-center">
            <p className="text-red-500">{error}</p>
          </div>
        )}

        <div className="space-y-4 flex flex-col items-center">
          {processedFile && (
            <button
              onClick={onNext}
              className="btn bg-green-600 hover:bg-green-700 text-white px-8 py-4 text-lg"
            >
              <span>Passer à l'étape 2 - Mise en forme</span>
              <ChevronRight className="w-6 h-6" />
            </button>
          )}
        </div>
      </div>

      <div className="mt-8 text-center text-sm text-zinc-500">
        <p>Formats supportés: .xlsx, .xls</p>
        <p className="mt-2">Marques traitées: Apple, Samsung, Xiaomi, JBL, Google, Honor, Nothing, TCL, XO</p>
        <p className="mt-2">Exclusions: Mac, Backbone, Bulk, OH25B, Soundbar</p>
        <p className="mt-2 text-[#B8860B]">✅ Nettoyage automatique des données et suppression des doublons</p>
      </div>
    </div>
  );
}

export default ProcessingPage;

import React, { useState, useCallback, useEffect } from 'react';
import { FileUp, FileDown, ArrowRight, Loader2, Download, ChevronRight } from 'lucide-react';
import { createProduct, fetchProducts, createImport, calculateProducts, exportCalculations } from '../api';
import { getCurrentWeekYear } from '../utils/date';

interface ProcessingPageProps {
  onNext: () => void;
}

function ProcessingPage({ onNext }: ProcessingPageProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedFile, setProcessedFile] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [productsCount, setProductsCount] = useState(0);

  useEffect(() => {
    fetchProducts()
      .then((list) => setProductsCount(list.length))
      .catch(() => {});
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
        droppedFile?.type === 'application/vnd.ms-excel') {
      setFile(droppedFile);
      setProcessedFile(null);
      setError(null);
    }
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setProcessedFile(null);
      setError(null);
    }
  }, []);


  const handleProcess = useCallback(async () => {
    if (!file) return;

    setIsProcessing(true);
    setError(null);

    try {
      await createImport(file);
      await createProduct();
      await calculateProducts();
      const list = await fetchProducts();
      setProductsCount(list.length);

      const blob = await exportCalculations();
      setProcessedFile(URL.createObjectURL(blob));
    } catch (error) {
      console.error('Error processing file:', error);
      setError(error instanceof Error ? error.message : 'Une erreur est survenue lors du traitement du fichier');
      setProcessedFile(null);
    } finally {
      setIsProcessing(false);
    }
  }, [file]);

  const handleDownload = useCallback(() => {
    if (!processedFile) return;

    const link = document.createElement('a');
    link.href = processedFile;
    link.download = 'product_calculates.xlsx';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [processedFile]);

  // Utilitaire semaine/année

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-4xl font-bold text-center mb-2">
        Étape 1 - Calculs et Traitement
      </h1>
      <p className="text-center text-[#B8860B] mb-4">
        Traitez vos fichiers Excel avec calculs TCP et marges
      </p>
      <p className="text-center text-zinc-400 mb-12">
        Semaine {getCurrentWeekYear()}
      </p>
      <p className="text-center text-sm text-zinc-500 mb-8">
        Produits en base : {productsCount}
      </p>
      
      <div className="bg-zinc-900 rounded-2xl shadow-2xl p-8 border border-[#B8860B]/20">
        <div 
          className={`border-2 border-dashed rounded-xl p-8 transition-all duration-200 ${
            isDragging 
              ? 'border-[#B8860B] bg-black/50' 
              : 'border-zinc-700 hover:border-[#B8860B]/50'
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="flex flex-col items-center justify-center space-y-4">
            <FileUp className="w-12 h-12 text-[#B8860B]" />
            <p className="text-lg text-zinc-300">
              Glissez votre fichier Excel ici ou
            </p>
            <label className="px-6 py-3 bg-[#B8860B] text-black rounded-lg cursor-pointer hover:bg-[#B8860B]/90 transition-colors font-semibold">
              Sélectionnez un fichier
              <input
                type="file"
                className="hidden"
                accept=".xlsx,.xls"
                onChange={handleFileChange}
              />
            </label>
          </div>
        </div>

        {file && (
          <div className="mt-8 space-y-4">
            <div className="flex items-center justify-between p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
              <div className="flex items-center space-x-3">
                <FileDown className="w-6 h-6 text-[#B8860B]" />
                <span className="text-zinc-300">{file.name}</span>
              </div>
              <button
                onClick={handleProcess}
                disabled={isProcessing}
                className="px-6 py-3 bg-[#B8860B] text-black rounded-lg flex items-center space-x-2 hover:bg-[#B8860B]/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
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
            </div>

            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-red-500">{error}</p>
              </div>
            )}

            {processedFile && (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-[#B8860B]/10 rounded-lg border border-[#B8860B]/30">
                  <div className="flex items-center space-x-3">
                    <FileDown className="w-6 h-6 text-[#B8860B]" />
                    <span className="text-[#B8860B]">Fichier traité avec succès</span>
                  </div>
                  <button
                    onClick={handleDownload}
                    className="px-6 py-3 bg-[#B8860B] text-black rounded-lg flex items-center space-x-2 hover:bg-[#B8860B]/90 transition-colors font-semibold"
                  >
                    <Download className="w-5 h-5" />
                    <span>Télécharger</span>
                  </button>
                </div>

                <div className="flex justify-center">
                  <button
                    onClick={onNext}
                    className="px-8 py-4 bg-green-600 text-white rounded-lg flex items-center space-x-2 hover:bg-green-700 transition-colors font-semibold text-lg"
                  >
                    <span>Passer à l'étape 2 - Mise en forme</span>
                    <ChevronRight className="w-6 h-6" />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="mt-8 text-center text-sm text-zinc-500">
          <p>Formats supportés: .xlsx, .xls</p>
          <p className="mt-2">Marques traitées: Apple, Samsung, Xiaomi, JBL, Google, Honor, Nothing, TCL, XO</p>
          <p className="mt-2">Exclusions: Mac, Backbone, Bulk, OH25B, Soundbar</p>
          <p className="mt-2 text-[#B8860B]">✅ Nettoyage automatique des données et suppression des doublons</p>
        </div>
      </div>
    </div>
  );
}

export default ProcessingPage;
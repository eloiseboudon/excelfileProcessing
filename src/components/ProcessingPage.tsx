import React, { useState, useCallback } from 'react';
import { FileUp, FileDown, ArrowRight, Loader2, Download, ChevronRight } from 'lucide-react';
import * as XLSX from 'xlsx';

interface ProcessingPageProps {
  onNext: () => void;
}

function ProcessingPage({ onNext }: ProcessingPageProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedFile, setProcessedFile] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  // Fonction pour nettoyer les noms de produits
  const cleanProductName = (name: string): string => {
    if (!name || typeof name !== 'string') return '';
    
    let cleanedName = name;
    
    // Supprimer "Region East" et "Region West"
    cleanedName = cleanedName.replace(/Region\s+(East|West)/gi, '');
    
    // Appliquer les remplacements existants
    const replacements: Record<string, string> = {
      'Dual Sim': 'DS',
      'GB RAM ': '/',
      ' - ': ' ',
      'Tablet Apple': 'Apple',
      'Tablet Honor': 'Honor',
      'Tablet Samsung': 'Samsung',
      'Tablet Xiaomi': 'Xiaomi',
      'Watch Apple': 'Apple',
      'Watch Samsung': 'Samsung',
      'Watch Xiaomi': 'Xiaomi',
      'Watch Google': 'Google' // Nouveau nettoyage ajouté
    };
    
    Object.entries(replacements).forEach(([key, value]) => {
      cleanedName = cleanedName.replace(new RegExp(key, 'g'), value);
    });
    
    // Nettoyer les espaces multiples et les espaces en début/fin
    cleanedName = cleanedName
      .replace(/\s+/g, ' ')  // Remplacer les espaces multiples par un seul espace
      .trim();               // Supprimer les espaces en début et fin
    
    return cleanedName;
  };

  // Fonction pour vérifier si un produit doit être exclu
  const shouldExcludeProduct = (name: string): boolean => {
    const excludeTerms = ['Mac', 'Backbone', 'Bulk', 'OH25B', 'Soundbar'];
    const nameLower = name.toLowerCase();
    return excludeTerms.some(term => nameLower.includes(term.toLowerCase()));
  };

  // Fonction pour gérer les doublons (garder le prix le plus bas)
  const removeDuplicates = (products: any[]): any[] => {
    const productMap = new Map<string, any>();
    
    products.forEach(product => {
      const cleanName = product['Nom produit'];
      const currentPrice = product['Prix HT d\'achat'];
      
      if (productMap.has(cleanName)) {
        // Si le produit existe déjà, garder celui avec le prix le plus bas
        const existingProduct = productMap.get(cleanName);
        if (currentPrice < existingProduct['Prix HT d\'achat']) {
          productMap.set(cleanName, product);
        }
      } else {
        // Nouveau produit, l'ajouter
        productMap.set(cleanName, product);
      }
    });
    
    return Array.from(productMap.values());
  };

  const handleProcess = useCallback(async () => {
    if (!file) return;

    setIsProcessing(true);
    setError(null);
    
    try {
      // Lire le fichier Excel
      const data = await file.arrayBuffer();
      const workbook = XLSX.read(data);
      const worksheet = workbook.Sheets[workbook.SheetNames[0]];
      const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as any[][];

      // Créer un nouveau tableau avec les colonnes 2 et 4
      const processedData = jsonData.slice(1)
        .map((row: any[]) => {
          const nomProduit = cleanProductName(String(row[1] || ''));
          const prixAchat = Number(row[3] || 0);
          
          // Ignorer les lignes vides ou avec des noms vides après nettoyage
          if (!nomProduit || prixAchat <= 0) return null;
          
          // Exclure les produits indésirables
          if (shouldExcludeProduct(nomProduit)) return null;
          
          return {
            'Nom produit': nomProduit,
            'Prix HT d\'achat': prixAchat
          };
        })
        .filter(row => row !== null); // Supprimer les lignes nulles

      // Filtrer les marques (ajout de "TCL" et "XO")
      const marques = ['Apple', 'Xiaomi', 'Samsung', 'JBL', 'Google', 'Honor', 'Nothing', 'TCL', 'XO'];
      const filteredRows = processedData.filter(row => 
        marques.some(marque => 
          row['Nom produit'].toLowerCase().includes(marque.toLowerCase())
        )
      );

      // Supprimer les doublons (garder le prix le plus bas)
      const uniqueRows = removeDuplicates(filteredRows);

      // Calculer TCP et marges
      const finalData = uniqueRows.map(row => {
        const prixAchat = row['Prix HT d\'achat'];
        let tcp = 0;
        const nomProduit = row['Nom produit'].toUpperCase();

        if (nomProduit.includes('32GB')) tcp = 10;
        else if (nomProduit.includes('64GB')) tcp = 12;
        else if (['128GB', '256GB', '512GB', '1TB'].some(size => nomProduit.includes(size))) tcp = 14;

        const marge45 = prixAchat * 0.045;
        const prixAvecTCPEtMarge = prixAchat + tcp + marge45;

        // Calculer le prix avec marge
        let prixAvecMarge = prixAchat;
        const seuils = [15, 29, 49, 79, 99, 129, 149, 179, 209, 299, 499, 799, 999];
        const marges = [1.25, 1.22, 1.20, 1.18, 1.15, 1.11, 1.10, 1.09, 1.09, 1.08, 1.08, 1.07, 1.07, 1.06];

        for (let i = 0; i < seuils.length; i++) {
          if (prixAchat <= seuils[i]) {
            prixAvecMarge = prixAchat * marges[i];
            break;
          }
        }
        if (prixAchat > seuils[seuils.length - 1]) {
          prixAvecMarge = prixAchat * 1.06;
        }

        // Calculer le prix maximum arrondi au supérieur (VALEUR, pas formule)
        const prixMax = Math.ceil(Math.max(prixAvecTCPEtMarge, prixAvecMarge));

        return {
          'Nom produit': row['Nom produit'],
          'Prix HT d\'achat': Number(prixAchat.toFixed(2)),
          'TCP': Number(tcp.toFixed(2)),
          'Marge de 4,5%': Number(marge45.toFixed(2)),
          'Prix HT avec TCP et marge': Number(prixAvecTCPEtMarge.toFixed(2)),
          'Prix HT avec Marge': Number(prixAvecMarge.toFixed(2)),
          'Prix HT Maximum': prixMax // VALEUR CALCULÉE, pas formule
        };
      });

      // Créer un nouveau workbook
      const newWorkbook = XLSX.utils.book_new();
      const newWorksheet = XLSX.utils.json_to_sheet(finalData);

      // Définir les largeurs de colonnes
      newWorksheet['!cols'] = [
        { wch: 50 }, // Nom produit
        { wch: 15 }, // Prix HT d'achat
        { wch: 8 },  // TCP
        { wch: 15 }, // Marge de 4,5%
        { wch: 25 }, // Prix HT avec TCP et marge
        { wch: 18 }, // Prix HT avec Marge
        { wch: 15 }  // Prix HT Maximum
      ];

      // Ajouter la note en bas du fichier
      const lastRow = finalData.length + 2; // +2 pour laisser une ligne vide
      const noteText = "Tarif HT TCP incluse / hors DEEE de 2,56€ HT par pièce / FRANCO 1000€ HT ou 20€ de frais de port";
      
      // Ajouter la note dans la première colonne
      const cellAddress = XLSX.utils.encode_cell({ r: lastRow, c: 0 });
      newWorksheet[cellAddress] = { t: 's', v: noteText };
      
      // Étendre la plage pour inclure la note
      const range = XLSX.utils.decode_range(newWorksheet['!ref'] || 'A1');
      range.e.r = Math.max(range.e.r, lastRow);
      newWorksheet['!ref'] = XLSX.utils.encode_range(range);

      XLSX.utils.book_append_sheet(newWorkbook, newWorksheet, 'Processed');

      // Convertir en blob
      const excelBuffer = XLSX.write(newWorkbook, { 
        bookType: 'xlsx', 
        type: 'array',
        cellStyles: true,
        sheetStubs: false
      });
      const blob = new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
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
    if (!processedFile || !file) return;

    const link = document.createElement('a');
    link.href = processedFile;
    link.download = `processed_${file.name}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [processedFile, file]);

  // Fonction pour obtenir la semaine et l'année actuelles
  const getCurrentWeekAndYear = () => {
    const now = new Date();
    const year = now.getFullYear();
    
    // Calculer le numéro de semaine ISO
    const startOfYear = new Date(year, 0, 1);
    const pastDaysOfYear = (now.getTime() - startOfYear.getTime()) / 86400000;
    const weekNumber = Math.ceil((pastDaysOfYear + startOfYear.getDay() + 1) / 7);
    
    return `S${weekNumber}-${year}`;
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-4xl font-bold text-center mb-2">
        Étape 1 - Calculs et Traitement
      </h1>
      <p className="text-center text-[#B8860B] mb-4">
        Traitez vos fichiers Excel avec calculs TCP et marges
      </p>
      <p className="text-center text-zinc-400 mb-12">
        Semaine {getCurrentWeekAndYear()}
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
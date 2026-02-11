import React, { useState, useCallback } from 'react';
import { FileUp, FileDown, ArrowLeft, Loader2, Download, Globe, Eye } from 'lucide-react';
import * as XLSX from 'xlsx';
import SearchControls from './SearchControls';
import { createImport } from '../api';
import { useNotification } from './NotificationProvider';
import { determineBrand, generatePricingHtml } from '../utils/html';
import { getCurrentWeekYear } from '../utils/date';
import WeekToolbar from './WeekToolbar';

interface FormattingPageProps {
  onBack: () => void;
}

interface Product {
  name: string;
  price: number;
  brand: string;
}

function FormattingPage({ onBack }: FormattingPageProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [formattedFile, setFormattedFile] = useState<string | null>(null);
  const [htmlFile, setHtmlFile] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [previewData, setPreviewData] = useState<Product[]>([]);

  // États pour la recherche et les filtres
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedBrand, setSelectedBrand] = useState<string>('all');
  const [minPrice, setMinPrice] = useState(0);
  const [maxPrice, setMaxPrice] = useState(2000);
  const [priceRange, setPriceRange] = useState({ min: 0, max: 2000 });


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
      setFormattedFile(null);
      setHtmlFile(null);
      setError(null);
    }
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setFormattedFile(null);
      setHtmlFile(null);
      setError(null);
    }
  }, []);

  // Utilitaire semaine/année

  const notify = useNotification();

  const handleFormat = useCallback(async () => {
    if (!file) return;

    setIsProcessing(true);
    setError(null);

    try {
      const res = await createImport(file);
      if ('new' in res) {
        notify(`Import réussi (${res.new} lignes)`, 'success');
      } else {
        notify('Import réussi', 'success');
      }
      // Lire le fichier Excel
      const data = await file.arrayBuffer();
      const workbook = XLSX.read(data);
      const worksheet = workbook.Sheets[workbook.SheetNames[0]];
      const jsonData = XLSX.utils.sheet_to_json(worksheet) as any[];

      // Extraire les données du fichier traité (nom + prix de la colonne 7 "Prix HT Maximum")
      const productsFromFile = jsonData
        .map(row => {
          const name = row['Nom produit'];
          const price = row['Prix HT Maximum'] || 0;

          if (!name || typeof name !== 'string' || name.trim() === '' || price <= 0) {
            return null;
          }

          return {
            name: name.trim(),
            price: Number(price)
          };
        })
        .filter(product => product !== null);

      const allProductsWithPrices = [...productsFromFile];

      // Créer les données pour la prévisualisation
      const previewProducts: Product[] = allProductsWithPrices.map(product => ({
        name: product.name,
        price: product.price,
        brand: determineBrand(product.name)
      }));

      setPreviewData(previewProducts);

      // Calculer la plage de prix réelle
      // à voir si création table ProductCalculate ou si calcul côté front, stockage ?
      const prices = previewProducts.map(p => p.price);
      const minPriceValue = Math.min(...prices);
      const maxPriceValue = Math.max(...prices);
      setPriceRange({ min: minPriceValue, max: maxPriceValue });
      setMinPrice(minPriceValue);
      setMaxPrice(maxPriceValue);

      // Grouper par marque pour l'Excel et le HTML (avec noms ET prix)
      const productsByBrand: Record<string, Array<{name: string, price: number}>> = {};
      allProductsWithPrices.forEach(product => {
        const brand = determineBrand(product.name);
        if (!productsByBrand[brand]) {
          productsByBrand[brand] = [];
        }
        productsByBrand[brand].push({
          name: product.name,
          price: product.price
        });
      });

      // Trier les marques et les produits
      const sortedBrands = Object.keys(productsByBrand).sort();
      sortedBrands.forEach(brand => {
        productsByBrand[brand].sort((a, b) => a.name.localeCompare(b.name));
      });

      // Créer le fichier Excel avec mise en forme ET PRIX
      const newWorkbook = XLSX.utils.book_new();
      const currentWeekYear = getCurrentWeekYear();

      // Préparer les données pour Excel avec 2 colonnes : Nom et Prix
      const excelData: (string | number)[][] = [];

      // Ajouter le lien boutique en haut
      excelData.push(['Boutique en ligne: https://shop.ajtpro.com/shop', '']);
      excelData.push(['', '']); // Ligne vide

      // Ajouter le titre
      excelData.push([`AJT PRO - Grille Tarifaire ${currentWeekYear}`, '']);
      excelData.push(['', '']); // Ligne vide

      // Ajouter les en-têtes de colonnes
      excelData.push(['PRODUIT', 'PRIX HT']);
      excelData.push(['', '']); // Ligne vide

      // Ajouter les produits groupés par marque AVEC PRIX
      sortedBrands.forEach(brand => {
        excelData.push([`=== ${brand} ===`, '']); // En-tête de marque
        productsByBrand[brand].forEach(product => {
          excelData.push([product.name, `${product.price}€`]);
        });
        excelData.push(['', '']); // Ligne vide entre les marques
      });

      // Ajouter la note tarifaire
      excelData.push(['Tarif HT TCP incluse / hors DEEE de 2,56€ HT par pièce / FRANCO 1000€ HT ou 20€ de frais de port', '']);
      excelData.push(['', '']); // Ligne vide

      // Ajouter le lien boutique en bas
      excelData.push(['Boutique en ligne: https://shop.ajtpro.com/shop', '']);

      // Créer la feuille Excel
      const formattedWorksheet = XLSX.utils.aoa_to_sheet(excelData);

      // Définir les largeurs de colonnes
      formattedWorksheet['!cols'] = [
        { wch: 70 }, // Colonne produit
        { wch: 15 }  // Colonne prix
      ];

      // Appliquer des styles
      const range = XLSX.utils.decode_range(formattedWorksheet['!ref'] || 'A1');

      for (let row = 0; row <= range.e.r; row++) {
        for (let col = 0; col <= 1; col++) {
          const cellAddress = XLSX.utils.encode_cell({ r: row, c: col });
          const cell = formattedWorksheet[cellAddress];

          if (cell && cell.v) {
            const cellValue = String(cell.v);

            // Style pour les liens boutique
            if (cellValue.includes('https://shop.ajtpro.com/shop')) {
              cell.s = {
                font: { bold: true, color: { rgb: "0066CC" } },
                alignment: { horizontal: "center" }
              };
            }
            // Style pour le titre principal
            else if (cellValue.includes('AJT PRO - Grille Tarifaire')) {
              cell.s = {
                font: { bold: true, size: 16, color: { rgb: "B8860B" } },
                alignment: { horizontal: "center" }
              };
            }
            // Style pour les en-têtes de colonnes
            else if (cellValue === 'PRODUIT' || cellValue === 'PRIX HT') {
              cell.s = {
                font: { bold: true, color: { rgb: "FFFFFF" } },
                fill: { fgColor: { rgb: "333333" } },
                alignment: { horizontal: "center" },
                border: {
                  top: { style: "thin", color: { rgb: "000000" } },
                  bottom: { style: "thin", color: { rgb: "000000" } },
                  left: { style: "thin", color: { rgb: "000000" } },
                  right: { style: "thin", color: { rgb: "000000" } }
                }
              };
            }
            // Style pour les en-têtes de marque
            else if (cellValue.startsWith('===') && cellValue.endsWith('===')) {
              cell.s = {
                font: { bold: true, color: { rgb: "FFFFFF" } },
                fill: { fgColor: { rgb: "B8860B" } },
                alignment: { horizontal: "center" },
                border: {
                  top: { style: "thin", color: { rgb: "000000" } },
                  bottom: { style: "thin", color: { rgb: "000000" } },
                  left: { style: "thin", color: { rgb: "000000" } },
                  right: { style: "thin", color: { rgb: "000000" } }
                }
              };
            }
            // Style pour la note tarifaire
            else if (cellValue.includes('Tarif HT TCP incluse')) {
              cell.s = {
                font: { bold: true, italic: true, color: { rgb: "B8860B" } },
                fill: { fgColor: { rgb: "FFF8DC" } },
                alignment: { horizontal: "center", wrapText: true },
                border: {
                  top: { style: "medium", color: { rgb: "B8860B" } },
                  bottom: { style: "medium", color: { rgb: "B8860B" } },
                  left: { style: "medium", color: { rgb: "B8860B" } },
                  right: { style: "medium", color: { rgb: "B8860B" } }
                }
              };
            }
            // Style pour les prix
            else if (cellValue.includes('€') && col === 1) {
              cell.s = {
                font: { bold: true, color: { rgb: "B8860B" } },
                alignment: { horizontal: "right" },
                border: {
                  top: { style: "thin", color: { rgb: "E0E0E0" } },
                  bottom: { style: "thin", color: { rgb: "E0E0E0" } },
                  left: { style: "thin", color: { rgb: "E0E0E0" } },
                  right: { style: "thin", color: { rgb: "E0E0E0" } }
                }
              };
            }
            // Style pour les produits
            else if (cellValue.trim() !== '' && !cellValue.includes('===') && col === 0) {
              cell.s = {
                alignment: { horizontal: "left" },
                border: {
                  top: { style: "thin", color: { rgb: "E0E0E0" } },
                  bottom: { style: "thin", color: { rgb: "E0E0E0" } },
                  left: { style: "thin", color: { rgb: "E0E0E0" } },
                  right: { style: "thin", color: { rgb: "E0E0E0" } }
                }
              };
            }
          }
        }
      }

      XLSX.utils.book_append_sheet(newWorkbook, formattedWorksheet, 'Grille Tarifaire');

      // Convertir en blob
      const excelBuffer = XLSX.write(newWorkbook, {
        bookType: 'xlsx',
        type: 'array',
        cellStyles: true,
        sheetStubs: false
      });
      const excelBlob = new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      setFormattedFile(URL.createObjectURL(excelBlob));

      // Créer le fichier HTML avec les vrais prix
      const htmlContent = generatePricingHtml(productsByBrand, sortedBrands, previewProducts, getCurrentWeekYear());
      const htmlBlob = new Blob([htmlContent], { type: 'text/html' });
      setHtmlFile(URL.createObjectURL(htmlBlob));

    } catch (error) {
      console.error('Error formatting file:', error);
      const message =
        error instanceof Error
          ? error.message
          : 'Impossible de formater le fichier. Veuillez vérifier le fichier et réessayer.';
      setError(message);
      notify(message, 'error');
      setFormattedFile(null);
      setHtmlFile(null);
    } finally {
      setIsProcessing(false);
    }
  }, [file]);

  const handleDownloadExcel = useCallback(() => {
    if (!formattedFile || !file) return;

    const link = document.createElement('a');
    link.href = formattedFile;
    link.download = `grille_tarifaire_${getCurrentWeekYear()}_${file.name}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [formattedFile, file]);

  const handleDownloadHtml = useCallback(() => {
    if (!htmlFile || !file) return;

    const link = document.createElement('a');
    link.href = htmlFile;
    link.download = `grille_tarifaire_${getCurrentWeekYear()}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [htmlFile, file]);

  // Filtrer les produits pour la prévisualisation
  const filteredProducts = previewData.filter(product => {
    const matchesSearch = product.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesBrand = selectedBrand === 'all' || product.brand === selectedBrand;
    const matchesPrice = product.price >= minPrice && product.price <= maxPrice;

    return matchesSearch && matchesBrand && matchesPrice;
  });

  // Obtenir les marques uniques
  const uniqueBrands = Array.from(new Set(previewData.map(p => p.brand))).sort();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
      <WeekToolbar />
      <div className="flex items-center justify-between mb-8">
        <button
          onClick={onBack}
          className="btn btn-secondary"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Retour à l'étape 1</span>
        </button>

      </div>

      <h1 className="text-4xl font-bold text-center mb-2">
        Étape 2 - Mise en Forme
      </h1>
      <p className="text-center text-[#B8860B] mb-4">
        Générez vos fichiers Excel formatés et pages web
      </p>


      <div className="card p-8">
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
              Glissez votre fichier traité de l'étape 1 ici ou
            </p>
            <label className="btn btn-primary cursor-pointer">
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
                onClick={handleFormat}
                disabled={isProcessing}
                className="btn btn-primary px-6 py-3 flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Formatage...</span>
                  </>
                ) : (
                  <>
                    <Globe className="w-5 h-5" />
                    <span>Formater</span>
                  </>
                )}
              </button>
            </div>

            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-red-500">{error}</p>
              </div>
            )}

            {formattedFile && htmlFile && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="flex items-center justify-between p-4 bg-[#B8860B]/10 rounded-lg border border-[#B8860B]/30">
                    <div className="flex items-center space-x-3">
                      <FileDown className="w-6 h-6 text-[#B8860B]" />
                      <span className="text-[#B8860B]">Excel formaté</span>
                    </div>
                    <button
                      onClick={handleDownloadExcel}
                      className="btn btn-primary"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-4 bg-green-500/10 rounded-lg border border-green-500/30">
                    <div className="flex items-center space-x-3">
                      <Globe className="w-6 h-6 text-green-500" />
                      <span className="text-green-500">Page web</span>
                    </div>
                    <button
                      onClick={handleDownloadHtml}
                      className="btn bg-green-600 hover:bg-green-700 text-white"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="flex items-center justify-between p-4 bg-blue-500/10 rounded-lg border border-blue-500/30">
                    <div className="flex items-center space-x-3">
                      <Eye className="w-6 h-6 text-blue-500" />
                      <span className="text-blue-500">Prévisualiser</span>
                    </div>
                    <button
                      onClick={() => setShowPreview(!showPreview)}
                      className="btn bg-blue-600 hover:bg-blue-700 text-white"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {showPreview && (
                  <div className="mt-8 p-6 bg-zinc-800/50 rounded-lg border border-zinc-700">
                    <h3 className="text-xl font-semibold text-white mb-6">Prévisualisation de la grille tarifaire</h3>

                    <SearchControls
                      searchTerm={searchTerm}
                      onSearchChange={setSearchTerm}
                      minPrice={minPrice}
                      maxPrice={maxPrice}
                      onPriceRangeChange={(min, max) => {
                        setMinPrice(min);
                        setMaxPrice(max);
                      }}
                      allProducts={previewData}
                      priceRange={priceRange}
                    />

                    {/* Filtres de marques */}
                    <div className="mb-6">
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => setSelectedBrand('all')}
                          className={`btn font-medium ${
                            selectedBrand === 'all'
                              ? 'btn-primary'
                              : 'btn-secondary'
                          }`}
                        >
                          Toutes ({previewData.length})
                        </button>
                        {uniqueBrands.map(brand => {
                          const count = previewData.filter(p => p.brand === brand).length;
                          return (
                            <button
                              key={brand}
                              onClick={() => setSelectedBrand(brand)}
                              className={`btn font-medium ${
                                selectedBrand === brand
                                  ? 'btn-primary'
                                  : 'btn-secondary'
                              }`}
                            >
                              {brand} ({count})
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Statistiques */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                      <div className="bg-zinc-700 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-[#B8860B]">{previewData.length}</div>
                        <div className="text-sm text-zinc-400">Total produits</div>
                      </div>
                      <div className="bg-zinc-700 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-[#B8860B]">{filteredProducts.length}</div>
                        <div className="text-sm text-zinc-400">Affichés</div>
                      </div>
                      <div className="bg-zinc-700 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-[#B8860B]">
                          {filteredProducts.length > 0 ? Math.round(filteredProducts.reduce((sum, p) => sum + p.price, 0) / filteredProducts.length) : 0}€
                        </div>
                        <div className="text-sm text-zinc-400">Prix moyen</div>
                      </div>
                      <div className="bg-zinc-700 rounded-lg p-4 text-center">
                        <div className="text-2xl font-bold text-[#B8860B]">{uniqueBrands.length}</div>
                        <div className="text-sm text-zinc-400">Marques</div>
                      </div>
                    </div>

                    {/* Grille de produits */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-96 overflow-y-auto">
                      {filteredProducts.map((product, index) => (
                        <div key={index} className="bg-zinc-700 rounded-lg p-4 border border-zinc-600 hover:border-[#B8860B]/50 transition-colors">
                          <div className="font-medium text-white mb-2 line-clamp-2">{product.name}</div>
                          <div className="flex items-center justify-between">
                            <div className="inline-block px-2 py-1 bg-[#B8860B]/20 text-[#B8860B] rounded text-sm">
                              {product.brand}
                            </div>
                            <div className="text-[#B8860B] font-bold text-lg">
                              {product.price}€
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {filteredProducts.length === 0 && (
                      <div className="text-center py-12">
                        <div className="text-6xl mb-4">🔍</div>
                        <p className="text-zinc-400 text-lg">Aucun produit trouvé</p>
                        <p className="text-zinc-500 text-sm mt-2">Essayez de modifier vos critères de recherche</p>
                      </div>
                    )}

                    {/* Note tarifaire */}
                    <div className="mt-6 p-4 bg-[#B8860B]/10 border border-[#B8860B]/30 rounded-lg text-center">
                      <p className="text-[#B8860B] font-medium">
                        📋 Tarif HT TCP incluse / hors DEEE de 2,56€ HT par pièce / FRANCO 1000€ HT ou 20€ de frais de port
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="mt-8 text-center text-sm text-zinc-500">
          <p>Formats supportés: .xlsx, .xls</p>
          <p className="mt-2 text-[#B8860B]">✅ Organisation par marque avec mise en forme professionnelle</p>
        </div>
      </div>

    </div>
  );
}

export default FormattingPage;

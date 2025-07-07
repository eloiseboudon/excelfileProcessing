import React, { useState, useCallback } from 'react';
import { FileUp, FileDown, ArrowLeft, Loader2, Download, Globe, Settings, ShoppingCart, Eye } from 'lucide-react';
import * as XLSX from 'xlsx';
import HotwavAdmin from './HotwavAdmin';
import AccessoriesAdmin from './AccessoriesAdmin';
import SearchControls from './SearchControls';
import { useLocalStorage } from '../hooks/useLocalStorage';

interface FormattingPageProps {
  onBack: () => void;
}

interface Product {
  name: string;
  price: number;
  brand: string;
}

interface HotwavProduct {
  nom: string;
  prix: number;
}

interface Accessory {
  nom: string;
  prix: number;
  marque: string;
}

function FormattingPage({ onBack }: FormattingPageProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [formattedFile, setFormattedFile] = useState<string | null>(null);
  const [htmlFile, setHtmlFile] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showHotwavAdmin, setShowHotwavAdmin] = useState(false);
  const [showAccessoriesAdmin, setShowAccessoriesAdmin] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [previewData, setPreviewData] = useState<Product[]>([]);

  // États pour la recherche et les filtres
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedBrand, setSelectedBrand] = useState<string>('all');
  const [minPrice, setMinPrice] = useState(0);
  const [maxPrice, setMaxPrice] = useState(2000);
  const [priceRange, setPriceRange] = useState({ min: 0, max: 2000 });

  // Stockage local pour les produits Hotwav et accessoires
  const [hotwavProducts, setHotwavProducts] = useLocalStorage<HotwavProduct[]>('hotwav_products', [
    { nom: 'Hotwav Note 20 4G DS 8/128Gb Black', prix: 125 },
    { nom: 'Hotwav Note 20 4G DS 8/128Gb Blue', prix: 125 },
    { nom: 'Hotwav Note 20 4G DS 8/128Gb Green', prix: 125 },
    { nom: 'Hotwav Cyber 15 4G DS 8/256Gb Black', prix: 145 },
    { nom: 'Hotwav Cyber 15 4G DS 8/256Gb Blue', prix: 145 },
    { nom: 'Hotwav Cyber 15 4G DS 8/256Gb Green', prix: 145 }
  ]);

  const [accessories, setAccessories] = useLocalStorage<Accessory[]>('accessories', [
    { nom: 'Coque iPhone 15 Pro Max Transparente', prix: 15, marque: 'Apple' },
    { nom: 'Protecteur d\'écran iPhone 15 Pro Max', prix: 12, marque: 'Apple' },
    { nom: 'Chargeur USB-C 20W', prix: 25, marque: 'Apple' },
    { nom: 'Coque Galaxy S24 Ultra Silicone', prix: 18, marque: 'Samsung' },
    { nom: 'Écouteurs Galaxy Buds3', prix: 89, marque: 'Samsung' },
    { nom: 'Coque Xiaomi 14 Pro Transparente', prix: 14, marque: 'Xiaomi' },
    { nom: 'Enceinte JBL Clip 4', prix: 45, marque: 'JBL' },
    { nom: 'Casque JBL Tune 770NC', prix: 89, marque: 'JBL' }
  ]);

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

  const handleFormat = useCallback(async () => {
    if (!file) return;

    setIsProcessing(true);
    setError(null);
    
    try {
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

      // Ajouter les produits Hotwav et accessoires avec leurs prix
      const hotwavProductsWithPrices = hotwavProducts.map(product => ({
        name: product.nom,
        price: product.prix
      }));

      const accessoriesWithPrices = accessories.map(accessory => ({
        name: accessory.nom,
        price: accessory.prix
      }));

      // Combiner tous les produits avec leurs prix
      const allProductsWithPrices = [...productsFromFile, ...hotwavProductsWithPrices, ...accessoriesWithPrices];

      // Fonction pour déterminer la marque
      const getBrandFromName = (name: string): string => {
        const brands = ['Apple', 'Samsung', 'Xiaomi', 'Hotwav', 'JBL', 'Google', 'Honor', 'Nothing', 'TCL', 'XO'];
        const nameLower = name.toLowerCase();
        
        for (const brand of brands) {
          if (nameLower.includes(brand.toLowerCase())) {
            return brand;
          }
        }
        return 'Autre';
      };

      // Créer les données pour la prévisualisation avec les vrais prix
      const previewProducts: Product[] = allProductsWithPrices.map(product => ({
        name: product.name,
        price: product.price,
        brand: getBrandFromName(product.name)
      }));

      setPreviewData(previewProducts);

      // Calculer la plage de prix réelle
      const prices = previewProducts.map(p => p.price);
      const minPriceValue = Math.min(...prices);
      const maxPriceValue = Math.max(...prices);
      setPriceRange({ min: minPriceValue, max: maxPriceValue });
      setMinPrice(minPriceValue);
      setMaxPrice(maxPriceValue);

      // Grouper par marque pour l'Excel et le HTML (avec noms ET prix)
      const productsByBrand: Record<string, Array<{name: string, price: number}>> = {};
      allProductsWithPrices.forEach(product => {
        const brand = getBrandFromName(product.name);
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
      const currentWeekYear = getCurrentWeekAndYear();
      
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
      const htmlContent = generateHtmlContent(productsByBrand, sortedBrands, previewProducts);
      const htmlBlob = new Blob([htmlContent], { type: 'text/html' });
      setHtmlFile(URL.createObjectURL(htmlBlob));

    } catch (error) {
      console.error('Error formatting file:', error);
      setError(error instanceof Error ? error.message : 'Une erreur est survenue lors du formatage du fichier');
      setFormattedFile(null);
      setHtmlFile(null);
    } finally {
      setIsProcessing(false);
    }
  }, [file, hotwavProducts, accessories]);

  const getBrandFromName = (name: string): string => {
    const brands = ['Apple', 'Samsung', 'Xiaomi', 'Hotwav', 'JBL', 'Google', 'Honor', 'Nothing', 'TCL', 'XO'];
    const nameLower = name.toLowerCase();
    
    for (const brand of brands) {
      if (nameLower.includes(brand.toLowerCase())) {
        return brand;
      }
    }
    return 'Autre';
  };

  const generateHtmlContent = (productsByBrand: Record<string, Array<{name: string, price: number}>>, sortedBrands: string[], productsWithPrices: Product[]): string => {
    const currentWeekYear = getCurrentWeekAndYear();
    const totalProducts = Object.values(productsByBrand).reduce((sum, products) => sum + products.length, 0);
    
    return `
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AJT PRO - Grille Tarifaire ${currentWeekYear}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: linear-gradient(135deg, #B8860B 0%, #DAA520 100%);
            border-radius: 20px;
            color: black;
        }
        
        .header h1 {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.2rem;
            opacity: 0.8;
        }
        
        .shop-link {
            background: rgba(184, 134, 11, 0.1);
            border: 1px solid rgba(184, 134, 11, 0.3);
            border-radius: 15px;
            padding: 15px;
            text-align: center;
            margin-bottom: 30px;
        }
        
        .shop-link a {
            color: #B8860B;
            text-decoration: none;
            font-weight: 600;
            font-size: 1.1rem;
        }
        
        .shop-link a:hover {
            text-decoration: underline;
        }
        
        .search-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(184, 134, 11, 0.3);
        }
        
        .search-input {
            width: 100%;
            padding: 15px 20px;
            font-size: 1.1rem;
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            background: rgba(0, 0, 0, 0.3);
            color: white;
            transition: all 0.3s ease;
            margin-bottom: 20px;
        }
        
        .search-input:focus {
            outline: none;
            border-color: #B8860B;
            box-shadow: 0 0 20px rgba(184, 134, 11, 0.3);
        }
        
        .search-input::placeholder {
            color: rgba(255, 255, 255, 0.5);
        }
        
        .brand-filters {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .brand-btn {
            padding: 10px 20px;
            border: 2px solid rgba(255, 255, 255, 0.2);
            border-radius: 25px;
            background: rgba(0, 0, 0, 0.3);
            color: white;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500;
        }
        
        .brand-btn:hover, .brand-btn.active {
            background: #B8860B;
            border-color: #B8860B;
            color: black;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(184, 134, 11, 0.4);
        }
        
        .brands-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
        }
        
        .brand-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(184, 134, 11, 0.3);
            backdrop-filter: blur(10px);
        }
        
        .brand-header {
            background: linear-gradient(135deg, #B8860B 0%, #DAA520 100%);
            color: black;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
            font-weight: bold;
            font-size: 1.2rem;
        }
        
        .products-list {
            space-y: 10px;
        }
        
        .product-item {
            padding: 12px 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            border-left: 3px solid #B8860B;
            margin-bottom: 8px;
            transition: all 0.3s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .product-item:hover {
            background: rgba(184, 134, 11, 0.1);
            transform: translateX(5px);
        }
        
        .product-name {
            flex: 1;
        }
        
        .product-price {
            color: #B8860B;
            font-weight: bold;
            font-size: 1.1rem;
            margin-left: 15px;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: rgba(184, 134, 11, 0.1);
            border: 1px solid rgba(184, 134, 11, 0.3);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: #B8860B;
            margin-bottom: 5px;
        }
        
        .stat-label {
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9rem;
        }
        
        .footer-note {
            background: rgba(184, 134, 11, 0.1);
            border: 1px solid rgba(184, 134, 11, 0.3);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            margin-top: 40px;
            color: #B8860B;
            font-weight: 500;
        }
        
        .hidden {
            display: none;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 2rem;
            }
            
            .brands-grid {
                grid-template-columns: 1fr;
            }
            
            .stats {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .product-item {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .product-price {
                margin-left: 0;
                margin-top: 5px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="shop-link">
            <a href="https://shop.ajtpro.com/shop" target="_blank">🛒 Visitez notre boutique en ligne</a>
        </div>
        
        <div class="header">
            <h1>🏆 AJT PRO - Grille Tarifaire</h1>
            <p>Semaine ${currentWeekYear} • ${totalProducts} produits disponibles</p>
        </div>
        
        <div class="search-section">
            <input 
                type="text" 
                id="searchInput" 
                class="search-input" 
                placeholder="🔍 Rechercher un produit..."
            >
            
            <div class="brand-filters">
                <button class="brand-btn active" onclick="filterByBrand('all')">Toutes les marques</button>
                ${sortedBrands.map(brand => 
                    `<button class="brand-btn" onclick="filterByBrand('${brand}')">${brand} (${productsByBrand[brand].length})</button>`
                ).join('')}
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">${totalProducts}</div>
                <div class="stat-label">Produits total</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="visibleProducts">${totalProducts}</div>
                <div class="stat-label">Produits affichés</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${sortedBrands.length}</div>
                <div class="stat-label">Marques</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${Math.round(productsWithPrices.reduce((sum, p) => sum + p.price, 0) / productsWithPrices.length)}€</div>
                <div class="stat-label">Prix moyen</div>
            </div>
        </div>
        
        <div class="brands-grid" id="brandsGrid">
            ${sortedBrands.map(brand => `
                <div class="brand-section" data-brand="${brand.toLowerCase()}">
                    <div class="brand-header">${brand} (${productsByBrand[brand].length} produits)</div>
                    <div class="products-list">
                        ${productsByBrand[brand].map(product => `
                            <div class="product-item" data-name="${product.name.toLowerCase()}">
                                <span class="product-name">${product.name}</span>
                                <span class="product-price">${product.price}€</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `).join('')}
        </div>
        
        <div class="footer-note">
            📋 Tarif HT TCP incluse / hors DEEE de 2,56€ HT par pièce / FRANCO 1000€ HT ou 20€ de frais de port
        </div>
        
        <div class="shop-link">
            <a href="https://shop.ajtpro.com/shop" target="_blank">🛒 Visitez notre boutique en ligne</a>
        </div>
    </div>
    
    <script>
        let currentBrandFilter = 'all';
        let currentSearchTerm = '';
        
        const searchInput = document.getElementById('searchInput');
        const brandsGrid = document.getElementById('brandsGrid');
        const visibleProductsCount = document.getElementById('visibleProducts');
        
        searchInput.addEventListener('input', function() {
            currentSearchTerm = this.value.toLowerCase();
            filterProducts();
        });
        
        function filterByBrand(brand) {
            currentBrandFilter = brand;
            
            // Mettre à jour les boutons actifs
            document.querySelectorAll('.brand-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            filterProducts();
        }
        
        function filterProducts() {
            const brandSections = document.querySelectorAll('.brand-section');
            let visibleCount = 0;
            
            brandSections.forEach(section => {
                const brand = section.dataset.brand;
                const products = section.querySelectorAll('.product-item');
                
                let sectionHasVisibleProducts = false;
                
                products.forEach(product => {
                    const name = product.dataset.name;
                    
                    const matchesSearch = name.includes(currentSearchTerm);
                    const matchesBrand = currentBrandFilter === 'all' || brand === currentBrandFilter.toLowerCase();
                    
                    if (matchesSearch && matchesBrand) {
                        product.style.display = 'flex';
                        sectionHasVisibleProducts = true;
                        visibleCount++;
                    } else {
                        product.style.display = 'none';
                    }
                });
                
                // Afficher/masquer la section entière
                if (sectionHasVisibleProducts && (currentBrandFilter === 'all' || brand === currentBrandFilter.toLowerCase())) {
                    section.style.display = 'block';
                } else {
                    section.style.display = 'none';
                }
            });
            
            visibleProductsCount.textContent = visibleCount;
        }
    </script>
</body>
</html>`;
  };

  const handleDownloadExcel = useCallback(() => {
    if (!formattedFile || !file) return;

    const link = document.createElement('a');
    link.href = formattedFile;
    link.download = `grille_tarifaire_${getCurrentWeekAndYear()}_${file.name}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [formattedFile, file]);

  const handleDownloadHtml = useCallback(() => {
    if (!htmlFile || !file) return;

    const link = document.createElement('a');
    link.href = htmlFile;
    link.download = `grille_tarifaire_${getCurrentWeekAndYear()}.html`;
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
    <div className="max-w-6xl mx-auto px-4 py-12">
      <div className="flex items-center justify-between mb-8">
        <button
          onClick={onBack}
          className="flex items-center space-x-2 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Retour à l'étape 1</span>
        </button>
        
        <div className="flex space-x-4">
          <button
            onClick={() => setShowHotwavAdmin(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-[#B8860B] text-black rounded-lg hover:bg-[#B8860B]/90 transition-colors font-semibold"
          >
            <Settings className="w-5 h-5" />
            <span>Admin Hotwav</span>
          </button>
          
          <button
            onClick={() => setShowAccessoriesAdmin(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-semibold"
          >
            <ShoppingCart className="w-5 h-5" />
            <span>Admin Accessoires</span>
          </button>
        </div>
      </div>

      <h1 className="text-4xl font-bold text-center mb-2">
        Étape 2 - Mise en Forme
      </h1>
      <p className="text-center text-[#B8860B] mb-4">
        Générez vos fichiers Excel formatés et pages web
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
              Glissez votre fichier traité de l'étape 1 ici ou
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
                onClick={handleFormat}
                disabled={isProcessing}
                className="px-6 py-3 bg-[#B8860B] text-black rounded-lg flex items-center space-x-2 hover:bg-[#B8860B]/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
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
                      className="px-4 py-2 bg-[#B8860B] text-black rounded-lg flex items-center space-x-2 hover:bg-[#B8860B]/90 transition-colors font-semibold"
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
                      className="px-4 py-2 bg-green-600 text-white rounded-lg flex items-center space-x-2 hover:bg-green-700 transition-colors font-semibold"
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
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg flex items-center space-x-2 hover:bg-blue-700 transition-colors font-semibold"
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
                          className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                            selectedBrand === 'all'
                              ? 'bg-[#B8860B] text-black'
                              : 'bg-zinc-700 text-white hover:bg-zinc-600'
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
                              className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                                selectedBrand === brand
                                  ? 'bg-[#B8860B] text-black'
                                  : 'bg-zinc-700 text-white hover:bg-zinc-600'
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
          <p className="mt-2">Produits Hotwav: {hotwavProducts.length} • Accessoires: {accessories.length}</p>
          <p className="mt-2 text-[#B8860B]">✅ Organisation par marque avec mise en forme professionnelle</p>
        </div>
      </div>

      {/* Modals */}
      <HotwavAdmin
        isVisible={showHotwavAdmin}
        onClose={() => setShowHotwavAdmin(false)}
        onSave={setHotwavProducts}
        initialProducts={hotwavProducts}
      />

      <AccessoriesAdmin
        isVisible={showAccessoriesAdmin}
        onClose={() => setShowAccessoriesAdmin(false)}
        onSave={setAccessories}
        initialAccessories={accessories}
      />
    </div>
  );
}

export default FormattingPage;
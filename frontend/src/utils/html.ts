export function determineBrand(name: string): string {
  const brands = ['Apple', 'Samsung', 'Xiaomi', 'Hotwav', 'JBL', 'Google', 'Honor', 'Nothing', 'TCL', 'XO'];
  const lower = name.toLowerCase();
  for (const brand of brands) {
    if (lower.includes(brand.toLowerCase())) {
      return brand;
    }
  }
  return 'Autre';
}

export function generatePricingHtml(
  productsByBrand: Record<string, Array<{ name: string; price: number }>>,
  sortedBrands: string[],
  productsWithPrices: Array<{ name: string; price: number }>,
  weekYear: string
): string {
  const total = Object.values(productsByBrand).reduce((s, p) => s + p.length, 0);
  return `
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AJT PRO - Grille Tarifaire ${weekYear}</title>
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
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: linear-gradient(135deg, #B8860B 0%, #DAA520 100%);
            border-radius: 20px;
            color: black;
        }
        .shop-link { text-align: center; margin-bottom: 20px; }
        .shop-link a {
            color: #B8860B;
            text-decoration: none;
            font-weight: bold;
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
        .product-item {
            padding: 12px 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            border-left: 3px solid #B8860B;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .product-price { color: #B8860B; font-weight: bold; margin-left: 15px; }
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
    </style>
</head>
<body>
    <div class="container">
        <div class="shop-link">
            <a href="https://shop.ajtpro.com/shop" target="_blank">🛒 Visitez notre boutique en ligne</a>
        </div>
        <div class="header">
            <h1>🏆 AJT PRO - Grille Tarifaire</h1>
            <p>Semaine ${weekYear} • ${total} produits disponibles</p>
        </div>
        <div class="brands-grid" id="brandsGrid">
            ${sortedBrands
              .map(
                b => `
                <div class="brand-section" data-brand="${b.toLowerCase()}">
                    <div class="brand-header">${b} (${productsByBrand[b].length} produits)</div>
                    <div class="products-list">
                        ${productsByBrand[b]
                          .map(p => `
                            <div class="product-item" data-name="${p.name.toLowerCase()}">
                                <span class="product-name">${p.name}</span>
                                <span class="product-price">${p.price}€</span>
                            </div>
                        `)
                          .join('')}
                    </div>
                </div>
            `)
              .join('')}
        </div>
        <div class="footer-note">
            📋 Tarif HT TCP incluse / hors DEEE de 2,56€ HT par pièce / FRANCO 1000€ HT ou 20€ de frais de port
        </div>
        <div class="shop-link">
            <a href="https://shop.ajtpro.com/shop" target="_blank">🛒 Visitez notre boutique en ligne</a>
        </div>
    </div>
</body>
</html>`;
}

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from models import (
    db,
    Product,
    TempImport,
    Reference,
    Fournisseur,
    BrandParameter,
    ColorReference,
    MemoryReference,
    TypeReference,
    ColorTransco,
    ProductCalculate,
)
import pandas as pd
import os
import math
from io import BytesIO

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

    @app.route('/')
    def index():
        return {'message': 'Hello World'}
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://eloise@localhost:5432/ajtpro"
    )
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route('/fournisseurs', methods=['GET'])
    def list_fournisseurs():
        fournisseurs = Fournisseur.query.all()
        result = [
            {
                'id': f.id,
                'name': f.name,
                'email': f.email,
                'phone': f.phone,
                'address': f.address,
            }
            for f in fournisseurs
        ]
        return jsonify(result)


    @app.route('/import', methods=['POST'])
    def create_import():
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        fournisseur_id = request.form.get('id_fournisseur')
        if fournisseur_id is not None:
            try:
                fournisseur_id = int(fournisseur_id)
            except ValueError:
                fournisseur_id = None

        # Clean previous temporary data
        TempImport.query.delete()
        db.session.commit()

        df = pd.read_excel(file)
        count_new = 0
        count_update = 0
        for _, row in df.iterrows():
            # Cast EAN to string to keep the exact value regardless of
            # how pandas interpreted the column (float, int, etc.).
            ean_value = None
            if pd.notnull(row.get('ean')):
                # remove any decimal part introduced by Excel or pandas
                ean_value = str(int(row.get('ean')))
                temp = TempImport(
                    description=row.get('description'),
                    quantity=row.get('quantity', None),
                    selling_price=row.get('sellingprice', None),
                    ean=ean_value,
                    id_fournisseur=fournisseur_id
                )
            db.session.add(temp)

            # Create reference if it does not already exist
            ref = Reference.query.filter_by(ean=ean_value).first()
            if ref:
                ref.description = row.get('description')
                ref.quantity = row.get('quantity', None)
                ref.selling_price = row.get('sellingprice', None)
                ref.id_fournisseur = fournisseur_id
                count_update += 1
            else:
                ref = Reference(
                    description=row.get('description'),
                    quantity=row.get('quantity', None),
                    selling_price=row.get('sellingprice', None),
                    ean=ean_value,
                    id_fournisseur=fournisseur_id
                )
                count_new += 1
                db.session.add(ref)

        db.session.commit()
        return jsonify({'status': 'success', 'new': count_new, 'updated': count_update})

    @app.route('/products', methods=['GET'])
    def list_products():
        products = Product.query.all()
        result = [
            {
                'id': p.id,
                'description': p.description,
                'name': p.name,
                'brand': p.brand.brand if p.brand else None,
                'price': p.price,
                'memory': p.memory_reference.memory if p.memory_reference else None,
                'color': p.color_reference.color if p.color_reference else None,
                'type': p.type_reference.type if p.type_reference else None,
                'reference': {
                    'id': p.reference.id if p.reference else None,
                    'description': p.reference.description if p.reference else None
                } if p.reference else None
            }
            for p in products
        ]
        return jsonify(result)

    @app.route('/populate_products', methods=['POST'])
    def populate_products_from_reference():
        references = Reference.query.all()
        brands = BrandParameter.query.all()
        colors = ColorReference.query.all()
        memories = MemoryReference.query.all()
        types = TypeReference.query.all()
        color_transcos = ColorTransco.query.all()

        created = 0
        updated = 0
        for ref in references:
            description_lower = ref.description.lower() if ref.description else ""

            brand_id = None
            for b in brands:
                if b.brand.lower() in description_lower:
                    brand_id = b.id
                    break

            color_id = None
            for c in colors:
                if c.color.lower() in description_lower:
                    color_id = c.id
                    break
            if not color_id:
                for ct in color_transcos:
                    if ct.color_source.lower() in description_lower:
                        color_id = ct.id_color_target
                        break

            memory_id = None
            for m in memories:
                if m.memory.lower() in description_lower:
                    memory_id = m.id
                    break

            type_id = None
            for t in types:
                if t.type.lower() in description_lower:
                    type_id = t.id
                    break

            existing = Product.query.filter_by(id_reference=ref.id).first()
            if existing:
                existing.description = ref.description
                existing.name = ref.description
                existing.price = ref.selling_price
                existing.id_brand = brand_id
                existing.id_color = color_id
                existing.id_memory = memory_id
                existing.id_type = type_id
                updated += 1
            else:
                product = Product(
                    id_reference=ref.id,
                    description=ref.description,
                    name=ref.description,
                    price=ref.selling_price,
                    id_brand=brand_id,
                    id_color=color_id,
                    id_memory=memory_id,
                    id_type=type_id,
                )
                db.session.add(product)
                created += 1
        db.session.commit()
        return jsonify({'status': 'success', 'created': created, 'updated': updated})

    @app.route('/calculate_products', methods=['POST'])
    def calculate_products():
        ProductCalculate.query.delete()
        db.session.commit()
        products = Product.query.all()
        created = 0
        for p in products:
            price = p.price or 0
            memory = p.memory_reference.memory.upper() if p.memory_reference else ''
            tcp = 0
            if memory == '32GB':
                tcp = 10
            elif memory == '64GB':
                tcp = 12
            elif memory in ['128GB', '256GB', '512GB', '1TB']:
                tcp = 14
            margin45 = price * 0.045
            price_with_tcp = price + tcp + margin45
            thresholds = [15, 29, 49, 79, 99, 129, 149, 179, 209, 299, 499, 799, 999]
            margins = [1.25, 1.22, 1.20, 1.18, 1.15, 1.11, 1.10, 1.09, 1.09, 1.08, 1.08, 1.07, 1.07, 1.06]
            price_with_margin = price
            for i, t in enumerate(thresholds):
                if price <= t:
                    price_with_margin = price * margins[i]
                    break
            if price > thresholds[-1]:
                price_with_margin = price * 1.06
            max_price = math.ceil(max(price_with_tcp, price_with_margin))
            calc = ProductCalculate(
                id_product=p.id,
                tcp=round(tcp, 2),
                marge4_5=round(margin45, 2),
                prixht_tcp_marge4_5=round(price_with_tcp, 2),
                prixht_marge4_5=round(price_with_margin, 2),
                prixht_max=max_price,
            )
            db.session.add(calc)
            created += 1
        db.session.commit()
        return jsonify({'status': 'success', 'created': created})

    @app.route('/export_calculates', methods=['GET'])
    def export_calculates():
        calcs = ProductCalculate.query.join(Product).all()
        rows = []
        for c in calcs:
            rows.append({
                'Nom produit': c.product.name if c.product else '',
                "Prix HT d'achat": c.product.price if c.product else 0,
                'TCP': c.tcp,
                'Marge de 4,5%': c.marge4_5,
                'Prix HT avec TCP et marge': c.prixht_tcp_marge4_5,
                'Prix HT avec Marge': c.prixht_marge4_5,
                'Prix HT Maximum': c.prixht_max,
            })
        df = pd.DataFrame(rows)
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name='product_calculates.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)


from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from models import (
    db,
    Product,
    TemporaryImport,
    ProductReference,
    Supplier,
    Brand,
    Color,
    MemoryOption,
    DeviceType,
    ColorTranslation,
    ProductCalculation,
    ImportHistory,
)
import pandas as pd
import os
import math
from io import BytesIO
from datetime import datetime, timezone

def create_app():
    # Load environment variables from a local .env file if present
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)

    app = Flask(__name__)

    frontend_origin = os.getenv("FRONTEND_URL")
    if not frontend_origin:
        raise RuntimeError("FRONTEND_URL environment variable is not set")
    CORS(app, resources={r"/*": {"origins": frontend_origin}}, expose_headers=["Content-Disposition"])

    @app.route('/')
    def index():
        return {'message': 'Hello World'}
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route('/suppliers', methods=['GET'])
    def list_suppliers():
        suppliers = Supplier.query.all()
        result = [
            {
                'id': s.id,
                'name': s.name,
                'email': s.email,
                'phone': s.phone,
                'address': s.address,
            }
            for s in suppliers
        ]
        return jsonify(result)

    @app.route('/import_history', methods=['GET'])
    def list_import_history():
        histories = ImportHistory.query.order_by(ImportHistory.import_date.desc()).all()
        result = [
            {
                'id': h.id,
                'filename': h.filename,
                'supplier_id': h.supplier_id,
                'product_count': h.product_count,
                'import_date': h.import_date.isoformat(),
            }
            for h in histories
        ]
        return jsonify(result)


    @app.route('/import', methods=['POST'])
    def create_import():
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        supplier_id = request.form.get('supplier_id')
        if supplier_id is not None:
            try:
                supplier_id = int(supplier_id)
            except ValueError:
                supplier_id = None

        # Clean previous temporary data
        TemporaryImport.query.delete()
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
                temp = TemporaryImport(
                    description=row.get('description'),
                    quantity=row.get('quantity', None),
                    selling_price=row.get('sellingprice', None),
                    ean=ean_value,
                    supplier_id=supplier_id
                )
            db.session.add(temp)

            # Create reference if it does not already exist for this supplier
            ref = ProductReference.query.filter_by(ean=ean_value, supplier_id=supplier_id).first()
            if ref:
                ref.description = row.get('description')
                ref.quantity = row.get('quantity', None)
                ref.selling_price = row.get('sellingprice', None)
                ref.supplier_id = supplier_id
                count_update += 1
            else:
                ref = ProductReference(
                    description=row.get('description'),
                    quantity=row.get('quantity', None),
                    selling_price=row.get('sellingprice', None),
                    ean=ean_value,
                    supplier_id=supplier_id
                )
                count_new += 1
                db.session.add(ref)

        history = ImportHistory(
            filename=file.filename,
            supplier_id=supplier_id,
            product_count=len(df)
        )
        db.session.add(history)

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
                'memory': p.memory.memory if p.memory else None,
                'color': p.color.color if p.color else None,
                'type': p.type.type if p.type else None,
                'reference': {
                    'id': p.reference.id if p.reference else None,
                    'description': p.reference.description if p.reference else None
                } if p.reference else None
            }
            for p in products
        ]
        return jsonify(result)

    @app.route('/supplier_last_import/{id}', methods=['GET'])
    def supplier_last_import(id):
        histories = ImportHistory.query.filter_by(supplier_id=id).order_by(ImportHistory.import_date.desc()).first()
        result = [
            {
                'id': h.id,
                'filename': h.filename,
                'supplier_id': h.supplier_id,
                'product_count': h.product_count,
                'import_date': h.import_date.isoformat(),
            }
            for h in histories
        ]
        return jsonify(result)

    @app.route('/product_calculations/count', methods=['GET'])
    def count_product_calculations():
        count = ProductCalculation.query.count()
        return jsonify({'count': count})

    @app.route('/populate_products', methods=['POST'])
    def populate_products_from_reference():
        references = ProductReference.query.all()
        brands = Brand.query.all()
        colors = Color.query.all()
        memories = MemoryOption.query.all()
        types = DeviceType.query.all()
        color_transcos = ColorTranslation.query.all()

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
                        color_id = ct.color_target_id
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

            existing = Product.query.filter_by(
                reference_id=ref.id,
                supplier_id=ref.supplier_id,
            ).first()
            if existing:
                existing.description = ref.description
                existing.name = ref.description
                existing.price = ref.selling_price
                existing.brand_id = brand_id
                existing.color_id = color_id
                existing.memory_id = memory_id
                existing.type_id = type_id
                existing.supplier_id = ref.supplier_id
                updated += 1
            else:
                product = Product(
                    reference_id=ref.id,
                    description=ref.description,
                    name=ref.description,
                    price=ref.selling_price,
                    brand_id=brand_id,
                    color_id=color_id,
                    memory_id=memory_id,
                    type_id=type_id,
                    supplier_id=ref.supplier_id,
                )
                db.session.add(product)
                created += 1
        db.session.commit()
        return jsonify({'status': 'success', 'created': created, 'updated': updated})

    @app.route('/calculate_products', methods=['POST'])
    def calculate_products():
        ProductCalculation.query.delete()
        db.session.commit()
        products = Product.query.all()
        created = 0
        for p in products:
            price = p.price or 0
            memory = p.memory.memory.upper() if p.memory else ''
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
            calc = ProductCalculation(
                product_id=p.id,
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
        calcs = ProductCalculation.query.join(Product).all()
        rows = []
        for c in calcs:
            p = c.product
            rows.append({
                'id': p.id if p else None,
                'reference_id': p.reference_id if p else None,
                'name': p.name if p else None,
                'description': p.description if p else None,
                'brand': p.brand.brand if p.brand else None,
                'price': p.price if p else None,
                'memory': p.memory.memory if p.memory else None,
                'color': p.color.color if p.color else None,
                'type': p.type.type if p.type else None,
                'supplier': p.supplier.name if p.supplier else None,
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
        filename = f"product_calculates_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    return app


if __name__ == '__main__':
    app = create_app()
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5001"))
    app.run(host=host, port=port)


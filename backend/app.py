from flask import Flask, request, jsonify
from flask_cors import CORS
from models import (
    db,
    Product,
    TempImport,
    Reference,
    BrandParameter,
    ColorReference,
    MemoryReference,
    TypeReference,
)
import pandas as pd
import os

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


    @app.route('/import', methods=['POST'])
    def create_import():
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        # Clean previous temporary data
        TempImport.query.delete()
        db.session.commit()

        df = pd.read_excel(file)
        count = 0
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
                    ean=ean_value
                )
            db.session.add(temp)

            # Create reference if it does not already exist
            ref = Reference.query.filter_by(ean=ean_value).first()
            if ref:
                ref.name = row.get('description')
                ref.quantity = row.get('quantity', None)
                ref.selling_price = row.get('sellingprice', None)
            else:
                ref = Reference(
                    name=row.get('description'),
                    quantity=row.get('quantity', None),
                    selling_price=row.get('sellingprice', None),
                    ean=ean_value
                )
                db.session.add(ref)
            count += 1

        db.session.commit()
        return jsonify({'status': 'success', 'count': count})

    @app.route('/products', methods=['GET'])
    def list_products():
        products = Product.query.all()
        result = [
            {
                'id': p.id,
                'name': p.name,
                'brand': p.brand.brand if p.brand else None,
                'price': p.price,
                'memory': p.memory_reference.memory if p.memory_reference else None,
                'color': p.color_reference.color if p.color_reference else None,
                'type': p.type_reference.type_name if p.type_reference else None,
                'reference': {
                    'id': p.reference.id if p.reference else None,
                    'name': p.reference.name if p.reference else None
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

        created = 0
        updated = 0
        for ref in references:
            name_lower = ref.name.lower() if ref.name else ""

            brand_id = None
            for b in brands:
                if b.brand.lower() in name_lower:
                    brand_id = b.id
                    break

            color_id = None
            for c in colors:
                if c.color.lower() in name_lower:
                    color_id = c.id
                    break

            memory_id = None
            for m in memories:
                if m.memory.lower() in name_lower:
                    memory_id = m.id
                    break

            type_id = None
            for t in types:
                if t.type_name.lower() in name_lower:
                    type_id = t.id
                    break

            existing = Product.query.filter_by(id_reference=ref.id).first()
            if existing:
                existing.name = ref.name
                existing.price = ref.selling_price
                existing.id_brand = brand_id
                existing.id_color = color_id
                existing.id_memory = memory_id
                existing.id_type = type_id
                updated += 1
            else:
                product = Product(
                    id_reference=ref.id,
                    name=ref.name,
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

    # @app.route('/products', methods=['POST'])
    # def create_product():
    #     data = request.get_json()
    #     product = Product(
    #         name=data.get('name'),
    #         brand=data.get('brand',None),
    #         price=data.get('price'),
    #         memory=data.get('memory', None),
    #         color=data.get('color', None),  # Optional field   
    #         id_reference=data.get('reference_id', None)  # Optional field
    #     )
    #     db.session.add(product)
    #     db.session.commit()
    #     return jsonify({'id': product.id}), 201

    # @app.route('/upload', methods=['POST'])
    # def upload_excel():
    #     if 'file' not in request.files:
    #         return jsonify({'error': 'No file provided'}), 400
    #     file = request.files['file']
    #     df = pd.read_excel(file)
    #     for _, row in df.iterrows():
    #         product = Product(
    #             name=row.get('name'),
    #             brand=row.get('brand', None),  # Optional field
    #             price=row.get('price'),
    #             memory=row.get('memory', None),  # Optional field
    #             color=row.get('color', None),  # Optional field
    #             id_reference=row.get('reference_id', None)  # Optional field
    #         )
    #         db.session.add(product)
    #     db.session.commit()
    #     return jsonify({'status': 'success', 'count': len(df)})

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)


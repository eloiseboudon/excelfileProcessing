from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, Product, TempImport, Reference
import pandas as pd

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

    @app.route('/')
    def index():
        return {'message': 'Hello World'}
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
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
            temp = TempImport(
                description=row.get('description'),
                articlelno=row.get('articlelno', None),
                quantity=row.get('quantity', None),
                selling_prince=row.get('selling_prince', None),
                ean=row.get('ean')
            )
            db.session.add(temp)

            # Create reference if it does not already exist
            ref = Reference.query.filter_by(ean=row.get('ean')).first()
            if not ref:
                ref = Reference(
                    name=row.get('description'),
                    articlelno=row.get('articlelno', None),
                    quantity=row.get('quantity', None),
                    selling_prince=row.get('selling_prince', None),
                    ean=row.get('ean')
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
                'brand': p.brand,
                'price': p.price,
                'memory': p.memory,
                'color': p.color,
                'reference': {
                    'id': p.reference.id if p.reference else None,
                    'name': p.reference.name if p.reference else None
                } if p.reference else None
            }
            for p in products
        ]
        return jsonify(result)

    @app.route('/products', methods=['POST'])
    def create_product():
        data = request.get_json()
        product = Product(
            name=data.get('name'),
            brand=data.get('brand',None),
            price=data.get('price'),
            memory=data.get('memory', None),
            color=data.get('color', None),  # Optional field   
            reference_id=data.get('reference_id', None)  # Optional field
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({'id': product.id}), 201

    @app.route('/upload', methods=['POST'])
    def upload_excel():
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['file']
        df = pd.read_excel(file)
        for _, row in df.iterrows():
            product = Product(
                name=row.get('name'),
                brand=row.get('brand', None),  # Optional field
                price=row.get('price'),
                memory=row.get('memory', None),  # Optional field
                color=row.get('color', None),  # Optional field
                reference_id=row.get('reference_id', None)  # Optional field    
            )
            db.session.add(product)
        db.session.commit()
        return jsonify({'status': 'success', 'count': len(df)})

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)


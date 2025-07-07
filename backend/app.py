from flask import Flask, request, jsonify
from models import db, Product
import pandas as pd
from flask_cors import CORS

def create_app():
    app = Flask(__name__)

    # Enable Cross-Origin Resource Sharing
    CORS(app)

    @app.route('/')
    def index():
        return {'message': 'Hello World'}
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route('/products', methods=['GET'])
    def list_products():
        products = Product.query.all()
        result = [
            {
                'id': p.id,
                'name': p.name,
                'brand': p.brand,
                'price': p.price
            }
            for p in products
        ]
        return jsonify(result)

    @app.route('/products', methods=['POST'])
    def create_product():
        data = request.get_json()
        product = Product(
            name=data.get('name'),
            brand=data.get('brand'),
            price=data.get('price')
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
                brand=row.get('brand'),
                price=row.get('price')
            )
            db.session.add(product)
        db.session.commit()
        return jsonify({'status': 'success', 'count': len(df)})

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)

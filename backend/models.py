from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class TempImport(db.Model):
    __tablename__ = 'temp_imports'
    
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    articlelno = db.Column(db.String(50))
    quantity = db.Column(db.Float)
    selling_prince = db.Column(db.Float)
    ean = db.Column(db.Integer, unique=True, nullable=False)


class Reference(db.Model):
    __tablename__ = 'references'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False) 
    articlelno = db.Column(db.String(50))
    quantity = db.Column(db.Float)
    selling_prince = db.Column(db.Float)
    ean = db.Column(db.Integer, unique=True, nullable=False)

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    id_reference = db.Column(db.Integer, db.ForeignKey('references.id'), nullable=True)
    reference = db.relationship('Reference', backref=db.backref('products', lazy=True)) 
    name = db.Column(db.String(120), nullable=False)
    brand = db.Column(db.String(50), nullable=True)
    price = db.Column(db.Float)
    memory = db.Column(db.String(50), nullable=True)
    color = db.Column(db.String(50), nullable=True)
    
class ProductCalculate(db.Model):
    __tablename__ = 'product_calculates'

    id = db.Column(db.Integer, primary_key=True)
    id_product = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product = db.relationship('Product', backref=db.backref('calculates', lazy=True))
    TCP = db.Column(db.Float, nullable=False)
    marge4_5 = db.Column(db.Float, nullable=False)
    prixHT_TCP_marge4_5 = db.Column(db.Float, nullable=False)
    prixHT_marge4_5 = db.Column(db.Float, nullable=False)
    prixHT_max = db.Column(db.Float, nullable=False)

    

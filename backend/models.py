from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class TempImport(db.Model):
    __tablename__ = 'temp_imports'
    
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer)
    selling_price = db.Column(db.Float)
    ean = db.Column(db.String(20), unique=True, nullable=False)

class Reference(db.Model):
    __tablename__ = 'reference'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False) 
    quantity = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    ean = db.Column(db.String(20), unique=True, nullable=False)

class BrandParameter(db.Model):
    __tablename__ = 'brand_parameters'

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False)

class ColorReference(db.Model):
    __tablename__ = 'color_references'

    id = db.Column(db.Integer, primary_key=True)
    color = db.Column(db.String(50), nullable=False)

class MemoryReference(db.Model):
    __tablename__ = 'memory_references'

    id = db.Column(db.Integer, primary_key=True)
    memory = db.Column(db.String(50), nullable=False)

class TypeReference(db.Model):
    __tablename__ = 'type_references'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)

class ColorTransco(db.Model):
    __tablename__ = 'color_transco'

    id = db.Column(db.Integer, primary_key=True)
    color_source = db.Column(db.String(50), nullable=False)
    color_target = db.Column(db.String(50), nullable=False)
    id_color_target = db.Column(
        db.Integer, db.ForeignKey('color_references.id'), nullable=False
    )
    color_reference = db.relationship('ColorReference')

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    id_reference = db.Column(db.Integer, db.ForeignKey('reference.id'), nullable=True)
    reference = db.relationship('Reference', backref=db.backref('products', lazy=True)) 
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(120), nullable=False)
    
    id_brand = db.Column(db.Integer, db.ForeignKey('brand_parameters.id'), nullable=True)
    brand = db.relationship('BrandParameter', backref=db.backref('products', lazy=True))

    id_memory = db.Column(db.Integer, db.ForeignKey('memory_references.id'), nullable=True)
    memory_reference = db.relationship('MemoryReference', backref=db.backref('products', lazy=True))
    id_color = db.Column(db.Integer, db.ForeignKey('color_references.id'), nullable=True)
    color_reference = db.relationship('ColorReference', backref=db.backref('products', lazy=True))
    id_type = db.Column(db.Integer, db.ForeignKey('type_references.id'), nullable=True)
    type_reference = db.relationship('TypeReference', backref=db.backref('products', lazy=True))
                                                                 
    price = db.Column(db.Float)
    
class ProductCalculate(db.Model):
    __tablename__ = 'product_calculates'

    id = db.Column(db.Integer, primary_key=True)
    id_product = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product = db.relationship('Product', backref=db.backref('calculates', lazy=True))
    tcp = db.Column(db.Float, nullable=False)
    marge4_5 = db.Column(db.Float, nullable=False)
    prixht_tcp_marge4_5 = db.Column(db.Float, nullable=False)
    prixht_marge4_5 = db.Column(db.Float, nullable=False)
    prixht_max = db.Column(db.Float, nullable=False)




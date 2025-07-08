from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Supplier(db.Model):
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(200), nullable=True)

class TemporaryImport(db.Model):
    __tablename__ = 'temporary_imports'
    __table_args__ = (
        db.UniqueConstraint('ean', 'id_supplier', name='uix_temp_ean_supplier'),
    )

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer)
    selling_price = db.Column(db.Float)
    ean = db.Column(db.String(20), nullable=False)

    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    supplier = db.relationship('supplier', backref=db.backref('temporary_imports', lazy=True))

class Reference(db.Model):
    __tablename__ = 'reference'
    __table_args__ = (
        db.UniqueConstraint('ean', 'id_supplier', name='uix_reference_ean_supplier'),
    )

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    ean = db.Column(db.String(20), nullable=False)

    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    supplier = db.relationship('supplier', backref=db.backref('references', lazy=True))

class Brand(db.Model):
    __tablename__ = 'brand'

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False)

class Color(db.Model):
    __tablename__ = 'colors'

    id = db.Column(db.Integer, primary_key=True)
    color = db.Column(db.String(50), nullable=False)

class MemoryOption(db.Model):
    __tablename__ = 'memory_options'

    id = db.Column(db.Integer, primary_key=True)
    memory = db.Column(db.String(50), nullable=False)

class DeviceType(db.Model):
    __tablename__ = 'device_types'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)

class ColorTranslation(db.Model):
    __tablename__ = 'color_translations'

    id = db.Column(db.Integer, primary_key=True)
    color_source = db.Column(db.String(50), nullable=False)
    color_target = db.Column(db.String(50), nullable=False)
    color_target_id = db.Column(
        db.Integer, db.ForeignKey('color.id'), nullable=False
    )
    color_reference = db.relationship('Color', backref=db.backref('translations', lazy=True))

class Product(db.Model):
    __tablename__ = 'products'
    __table_args__ = (
        db.UniqueConstraint('id_reference', 'id_supplier', name='uix_product_reference_supplier'),
    )

    id = db.Column(db.Integer, primary_key=True)
    id_reference = db.Column(db.Integer, db.ForeignKey('reference.id'), nullable=True)
    reference = db.relationship('Reference', backref=db.backref('products', lazy=True)) 
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(120), nullable=False)

    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    supplier = db.relationship('supplier', backref=db.backref('products', lazy=True))
    
    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'), nullable=True)
    brand = db.relationship('Brand', backref=db.backref('products', lazy=True))

    memory_id = db.Column(db.Integer, db.ForeignKey('memory_options.id'), nullable=True)
    memory = db.relationship('MemoryOption', backref=db.backref('products', lazy=True))
    color_id = db.Column(db.Integer, db.ForeignKey('color.id'), nullable=True)
    color = db.relationship('Color', backref=db.backref('products', lazy=True))
    type_id = db.Column(db.Integer, db.ForeignKey('device_types.id'), nullable=True)
    type = db.relationship('DeviceType', backref=db.backref('products', lazy=True))
                                                                 
    price = db.Column(db.Float)
    
class ProductCalculatation(db.Model):
    __tablename__ = 'product_calculations'

    id = db.Column(db.Integer, primary_key=True)
    id_product = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product = db.relationship('Product', backref=db.backref('calculates', lazy=True))
    tcp = db.Column(db.Float, nullable=False)
    marge4_5 = db.Column(db.Float, nullable=False)
    prixht_tcp_marge4_5 = db.Column(db.Float, nullable=False)
    prixht_marge4_5 = db.Column(db.Float, nullable=False)
    prixht_max = db.Column(db.Float, nullable=False)


class ImportHistory(db.Model):
    __tablename__ = 'import_histories'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    id_supplier = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    supplier = db.relationship('supplier', backref=db.backref('imports', lazy=True))
    product_count = db.Column(db.Integer, nullable=False)
    import_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)




from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="user")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(200), nullable=True)


class TemporaryImport(db.Model):
    __tablename__ = "temporary_imports"
    __table_args__ = (
        db.UniqueConstraint("ean", "supplier_id", name="uix_temp_ean_supplier"),
    )

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=True)
    model = db.Column(db.String(200), nullable=True)
    quantity = db.Column(db.Integer)
    selling_price = db.Column(db.Float)
    ean = db.Column(db.String(20), nullable=True)

    # Champs pour stocker les valeurs extraites
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=True)
    memory_id = db.Column(db.Integer, db.ForeignKey("memory_options.id"), nullable=True)
    color_id = db.Column(db.Integer, db.ForeignKey("colors.id"), nullable=True)
    type_id = db.Column(db.Integer, db.ForeignKey("device_types.id"), nullable=True)

    # Relations
    brand = db.relationship("Brand", backref=db.backref("temporary_imports", lazy=True))
    memory = db.relationship(
        "MemoryOption", backref=db.backref("temporary_imports", lazy=True)
    )
    color = db.relationship("Color", backref=db.backref("temporary_imports", lazy=True))
    type = db.relationship(
        "DeviceType", backref=db.backref("temporary_imports", lazy=True)
    )

    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=True)
    supplier = db.relationship(
        "Supplier", backref=db.backref("temporary_imports", lazy=True)
    )


class Brand(db.Model):
    __tablename__ = "brands"

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False)


class Color(db.Model):
    __tablename__ = "colors"

    id = db.Column(db.Integer, primary_key=True)
    color = db.Column(db.String(50), nullable=False)


class MemoryOption(db.Model):
    __tablename__ = "memory_options"

    id = db.Column(db.Integer, primary_key=True)
    memory = db.Column(db.String(50), nullable=False)
    tcp_value = db.Column(db.Integer, nullable=False)


class DeviceType(db.Model):
    __tablename__ = "device_types"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)


class Exclusion(db.Model):
    __tablename__ = "exclusions"

    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(100), nullable=False, unique=True)


class ColorTranslation(db.Model):
    __tablename__ = "color_translations"

    id = db.Column(db.Integer, primary_key=True)
    color_source = db.Column(db.String(50), nullable=False)
    color_target = db.Column(db.String(50), nullable=False)
    color_target_id = db.Column(db.Integer, db.ForeignKey("colors.id"), nullable=False)


class BrandTranslation(db.Model):
    __tablename__ = "brand_translations"

    id = db.Column(db.Integer, primary_key=True)
    brand_source = db.Column(db.String(50), nullable=False)
    brand_target = db.Column(db.String(50), nullable=False)
    brand_target_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=False)


class MemoryTranslation(db.Model):
    __tablename__ = "memory_translations"

    id = db.Column(db.Integer, primary_key=True)
    memory_source = db.Column(db.String(50), nullable=False)
    memory_target = db.Column(db.String(50), nullable=False)
    memory_target_id = db.Column(
        db.Integer, db.ForeignKey("memory_options.id"), nullable=False
    )


class TypeTranslation(db.Model):
    __tablename__ = "type_translations"

    id = db.Column(db.Integer, primary_key=True)
    type_source = db.Column(db.String(50), nullable=False)
    type_target = db.Column(db.String(50), nullable=False)
    type_target_id = db.Column(
        db.Integer, db.ForeignKey("device_types.id"), nullable=False
    )


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)

    ean = db.Column(db.String(20), nullable=True)

    model = db.Column(db.String(120), nullable=True)
    # name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(120), nullable=False)

    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=True)
    brand = db.relationship("Brand", backref=db.backref("products", lazy=True))

    memory_id = db.Column(db.Integer, db.ForeignKey("memory_options.id"), nullable=True)
    memory = db.relationship("MemoryOption", backref=db.backref("products", lazy=True))
    color_id = db.Column(db.Integer, db.ForeignKey("colors.id"), nullable=True)
    color = db.relationship("Color", backref=db.backref("products", lazy=True))
    type_id = db.Column(db.Integer, db.ForeignKey("device_types.id"), nullable=True)
    type = db.relationship("DeviceType", backref=db.backref("products", lazy=True))

    recommended_price = db.Column(db.Float, nullable=True)


class ProductCalculation(db.Model):
    __tablename__ = "product_calculations"

    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    product = db.relationship("Product", backref=db.backref("calculates", lazy=True))

    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=True)
    supplier = db.relationship(
        "Supplier", backref=db.backref("product_calculations", lazy=True)
    )

    price = db.Column(db.Float, nullable=False)
    tcp = db.Column(db.Float, nullable=False)
    marge4_5 = db.Column(db.Float, nullable=False)
    prixht_tcp_marge4_5 = db.Column(db.Float, nullable=False)
    prixht_marge4_5 = db.Column(db.Float, nullable=False)
    prixht_max = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ImportHistory(db.Model):
    __tablename__ = "import_histories"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=True)
    supplier = db.relationship(
        "Supplier", backref=db.backref("import_histories", lazy=True)
    )
    product_count = db.Column(db.Integer, nullable=False)
    import_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class FormatImport(db.Model):
    __tablename__ = "format_imports"

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=True)
    supplier = db.relationship(
        "Supplier", backref=db.backref("format_imports", lazy=True)
    )
    column_name = db.Column(db.String(50), nullable=True)
    column_order = db.Column(db.Integer, nullable=True)


class GraphSetting(db.Model):
    __tablename__ = "graph_settings"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=True)
    visible = db.Column(db.Boolean, nullable=True, default=True)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="client")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

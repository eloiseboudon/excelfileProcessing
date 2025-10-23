from datetime import datetime
from enum import Enum

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

from sqlalchemy.dialects.postgresql import JSONB

db = SQLAlchemy()


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(200), nullable=True)


class AuthType(Enum):
    NONE = "none"
    API_KEY = "api_key"
    BASIC = "basic"
    OAUTH2 = "oauth2"


class PaginationType(Enum):
    NONE = "none"
    PAGE = "page"
    CURSOR = "cursor"
    LINK_HEADER = "link"
    OFFSET_LIMIT = "offset"


class SupplierAPI(db.Model):
    __tablename__ = "supplier_apis"

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    supplier = db.relationship("Supplier", backref=db.backref("apis", lazy=True))

    base_url = db.Column(db.String(255), nullable=False)
    auth_type = db.Column(
        db.Enum(
            AuthType,
            name="authtype",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=AuthType.NONE,
    )
    auth_config = db.Column(JSONB, nullable=True)
    default_headers = db.Column(JSONB, nullable=True)
    rate_limit_per_min = db.Column(db.Integer, nullable=True)


class ApiEndpoint(db.Model):
    __tablename__ = "api_endpoints"

    id = db.Column(db.Integer, primary_key=True)
    supplier_api_id = db.Column(
        db.Integer, db.ForeignKey("supplier_apis.id"), nullable=False
    )
    supplier_api = db.relationship(
        "SupplierAPI", backref=db.backref("endpoints", lazy=True)
    )

    name = db.Column(db.String(100), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    method = db.Column(db.String(10), nullable=False, default="GET")
    query_params = db.Column(JSONB, nullable=True)
    body_template = db.Column(JSONB, nullable=True)
    content_type = db.Column(db.String(50), nullable=False, default="application/json")

    pagination_type = db.Column(
        db.Enum(
            PaginationType,
            name="paginationtype",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=PaginationType.NONE,
    )
    pagination_config = db.Column(JSONB, nullable=True)
    items_path = db.Column(db.String(200), nullable=True)


class MappingVersion(db.Model):
    __tablename__ = "mapping_versions"

    id = db.Column(db.Integer, primary_key=True)
    supplier_api_id = db.Column(
        db.Integer, db.ForeignKey("supplier_apis.id"), nullable=False
    )
    supplier_api = db.relationship(
        "SupplierAPI", backref=db.backref("mappings", lazy=True)
    )
    version = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FieldMap(db.Model):
    __tablename__ = "field_maps"

    id = db.Column(db.Integer, primary_key=True)
    mapping_version_id = db.Column(
        db.Integer, db.ForeignKey("mapping_versions.id"), nullable=False
    )
    mapping_version = db.relationship(
        "MappingVersion", backref=db.backref("fields", lazy=True)
    )

    target_field = db.Column(db.String(100), nullable=False)
    source_path = db.Column(db.String(300), nullable=False)
    transform = db.Column(JSONB, nullable=True)


class ApiFetchJob(db.Model):
    __tablename__ = "api_fetch_jobs"

    id = db.Column(db.Integer, primary_key=True)
    supplier_api_id = db.Column(
        db.Integer, db.ForeignKey("supplier_apis.id"), nullable=False
    )
    endpoint_id = db.Column(db.Integer, db.ForeignKey("api_endpoints.id"), nullable=False)
    mapping_version_id = db.Column(
        db.Integer,
        db.ForeignKey("mapping_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="running")
    error_message = db.Column(db.Text, nullable=True)
    params_used = db.Column(JSONB, nullable=True)
    report_updated_products = db.Column(JSONB, nullable=True)
    report_database_missing_products = db.Column(JSONB, nullable=True)
    report_api_missing_products = db.Column(JSONB, nullable=True)
    report_api_raw_items = db.Column(JSONB, nullable=True)

    supplier_api = db.relationship("SupplierAPI")
    endpoint = db.relationship("ApiEndpoint")
    mapping_version = db.relationship("MappingVersion")


class RawIngest(db.Model):
    __tablename__ = "raw_ingests"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("api_fetch_jobs.id"), nullable=False)
    job = db.relationship("ApiFetchJob", backref=db.backref("raw_chunks", lazy=True))
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)
    http_status = db.Column(db.Integer, nullable=True)
    payload = db.Column(db.LargeBinary, nullable=False)
    content_type = db.Column(db.String(50), nullable=False)
    page_index = db.Column(db.Integer, nullable=True)
    cursor = db.Column(db.String(200), nullable=True)


class ParsedItem(db.Model):
    __tablename__ = "parsed_items"
    __table_args__ = (
        db.UniqueConstraint(
            "supplier_id", "ean", "part_number", "job_id", name="uix_parsed_supplier_ean_part_job"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("api_fetch_jobs.id"), nullable=False)
    job = db.relationship("ApiFetchJob", backref=db.backref("parsed_items", lazy=True))

    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    supplier = db.relationship("Supplier")

    ean = db.Column(db.String(20))
    part_number = db.Column(db.String(120))
    supplier_sku = db.Column(db.String(120))
    model = db.Column(db.String(250))
    description = db.Column(db.String(400))
    brand = db.Column(db.String(100))
    color = db.Column(db.String(50))
    memory = db.Column(db.String(50))
    ram = db.Column(db.String(50))
    norme = db.Column(db.String(50))
    device_type = db.Column(db.String(50))
    quantity = db.Column(db.Integer)
    purchase_price = db.Column(db.Float)
    currency = db.Column(db.String(3))
    recommended_price = db.Column(db.Float)
    updated_at = db.Column(db.DateTime)


class SupplierProductRef(db.Model):
    __tablename__ = "supplier_product_refs"
    __table_args__ = (
        db.UniqueConstraint(
            "supplier_id",
            "ean",
            "part_number",
            "supplier_sku",
            name="uix_supplier_ref",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)

    ean = db.Column(db.String(20), nullable=True)
    part_number = db.Column(db.String(120), nullable=True)
    supplier_sku = db.Column(db.String(120), nullable=True)

    last_seen_at = db.Column(db.DateTime, default=datetime.utcnow)

class TemporaryImport(db.Model):
    __tablename__ = "temporary_imports"
    __table_args__ = (
        db.UniqueConstraint("ean", "supplier_id", name="uix_temp_ean_supplier"),
    )

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=True)
    model = db.Column(db.String(250), nullable=True)
    quantity = db.Column(db.Integer)
    selling_price = db.Column(db.Float)
    ean = db.Column(db.String(20), nullable=True)
    part_number = db.Column(db.String(120), nullable=True)

    # Champs pour stocker les valeurs extraites
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=True)
    memory_id = db.Column(db.Integer, db.ForeignKey("memory_options.id"), nullable=True)
    color_id = db.Column(db.Integer, db.ForeignKey("colors.id"), nullable=True)
    type_id = db.Column(db.Integer, db.ForeignKey("device_types.id"), nullable=True)
    ram_id = db.Column(db.Integer, db.ForeignKey("ram_options.id"), nullable=True)
    norme_id = db.Column(db.Integer, db.ForeignKey("norme_options.id"), nullable=True)

    # Relations
    brand = db.relationship("Brand", backref=db.backref("temporary_imports", lazy=True))
    memory = db.relationship(
        "MemoryOption", backref=db.backref("temporary_imports", lazy=True)
    )
    color = db.relationship("Color", backref=db.backref("temporary_imports", lazy=True))
    type = db.relationship(
        "DeviceType", backref=db.backref("temporary_imports", lazy=True)
    )
    ram = db.relationship(
        "RAMOption", backref=db.backref("temporary_imports", lazy=True)
    )
    norme = db.relationship(
        "NormeOption", backref=db.backref("temporary_imports", lazy=True)
    )

    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=True)
    supplier = db.relationship(
        "Supplier", backref=db.backref("temporary_imports", lazy=True)
    )


class Brand(db.Model):
    __tablename__ = "brands"

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(50), nullable=False, unique=True)


class Color(db.Model):
    __tablename__ = "colors"

    id = db.Column(db.Integer, primary_key=True)
    color = db.Column(db.String(50), nullable=False, unique=True)


class MemoryOption(db.Model):
    __tablename__ = "memory_options"

    id = db.Column(db.Integer, primary_key=True)
    memory = db.Column(db.String(50), nullable=False, unique=True)
    tcp_value = db.Column(db.Integer, nullable=False)


class DeviceType(db.Model):
    __tablename__ = "device_types"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False, unique=True)


class Exclusion(db.Model):
    __tablename__ = "exclusions"

    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(100), nullable=False, unique=True)


class RAMOption(db.Model):
    __tablename__ = "ram_options"

    id = db.Column(db.Integer, primary_key=True)
    ram = db.Column(db.String(50), nullable=False, unique=True)


class NormeOption(db.Model):
    __tablename__ = "norme_options"

    id = db.Column(db.Integer, primary_key=True)
    norme = db.Column(db.String(50), nullable=False, unique=True)


class ColorTranslation(db.Model):
    __tablename__ = "color_translations"

    id = db.Column(db.Integer, primary_key=True)
    color_source = db.Column(db.String(50), nullable=False, unique=True)
    color_target = db.Column(db.String(50), nullable=False)
    color_target_id = db.Column(db.Integer, db.ForeignKey("colors.id"), nullable=False)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)

    ean = db.Column(db.String(20), nullable=True)
    part_number = db.Column(db.String(120), nullable=True)

    model = db.Column(db.String(250), nullable=True)
    description = db.Column(db.String(120), nullable=True)

    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=True)
    brand = db.relationship("Brand", backref=db.backref("products", lazy=True))

    memory_id = db.Column(db.Integer, db.ForeignKey("memory_options.id"), nullable=True)
    memory = db.relationship("MemoryOption", backref=db.backref("products", lazy=True))
    color_id = db.Column(db.Integer, db.ForeignKey("colors.id"), nullable=True)
    color = db.relationship("Color", backref=db.backref("products", lazy=True))
    type_id = db.Column(db.Integer, db.ForeignKey("device_types.id"), nullable=True)
    type = db.relationship("DeviceType", backref=db.backref("products", lazy=True))

    RAM_id = db.Column(db.Integer, db.ForeignKey("ram_options.id"), nullable=True)
    RAM = db.relationship("RAMOption", backref=db.backref("products", lazy=True))

    norme_id = db.Column(db.Integer, db.ForeignKey("norme_options.id"), nullable=True)
    norme = db.relationship("NormeOption", backref=db.backref("products", lazy=True))

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
    marge = db.Column(db.Float, nullable=True)
    prixht_tcp_marge4_5 = db.Column(db.Float, nullable=False)
    prixht_marge4_5 = db.Column(db.Float, nullable=False)
    prixht_max = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    stock = db.Column(db.Integer, nullable=True)


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
    username = db.Column(db.String(80), unique=True, nullable=True)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="client")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

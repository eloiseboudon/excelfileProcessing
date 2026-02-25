from datetime import datetime, timezone
from enum import Enum

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from werkzeug.security import check_password_hash, generate_password_hash

from utils.crypto import decrypt_value, encrypt_value

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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


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
    endpoint_id = db.Column(
        db.Integer, db.ForeignKey("api_endpoints.id"), nullable=False
    )
    mapping_version_id = db.Column(
        db.Integer,
        db.ForeignKey("mapping_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
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
    fetched_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    http_status = db.Column(db.Integer, nullable=True)
    payload = db.Column(db.LargeBinary, nullable=False)
    content_type = db.Column(db.String(50), nullable=False)
    page_index = db.Column(db.Integer, nullable=True)
    cursor = db.Column(db.String(200), nullable=True)


class ParsedItem(db.Model):
    __tablename__ = "parsed_items"
    __table_args__ = (
        db.UniqueConstraint(
            "supplier_id",
            "ean",
            "part_number",
            "job_id",
            name="uix_parsed_supplier_ean_part_job",
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
            "normalized_label",
            name="uix_supplier_ref_label",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)

    normalized_label = db.Column(db.String(300), nullable=True)
    ean = db.Column(db.String(20), nullable=True)
    part_number = db.Column(db.String(120), nullable=True)
    supplier_sku = db.Column(db.String(120), nullable=True)

    last_seen_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class SupplierCatalog(db.Model):
    __tablename__ = "supplier_catalog"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=True)
    model = db.Column(db.String(250), nullable=True)
    quantity = db.Column(db.Integer)
    selling_price = db.Column(db.Float)
    ean = db.Column(db.String(20), nullable=True)
    part_number = db.Column(db.String(120), nullable=True)
    supplier_sku = db.Column(db.String(120), nullable=True)

    # Champs pour stocker les valeurs extraites
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=True)
    memory_id = db.Column(db.Integer, db.ForeignKey("memory_options.id"), nullable=True)
    color_id = db.Column(db.Integer, db.ForeignKey("colors.id"), nullable=True)
    type_id = db.Column(db.Integer, db.ForeignKey("device_types.id"), nullable=True)
    ram_id = db.Column(db.Integer, db.ForeignKey("ram_options.id"), nullable=True)
    norme_id = db.Column(db.Integer, db.ForeignKey("norme_options.id"), nullable=True)

    # Relations
    brand = db.relationship("Brand", backref=db.backref("supplier_catalog", lazy=True))
    memory = db.relationship(
        "MemoryOption", backref=db.backref("supplier_catalog", lazy=True)
    )
    color = db.relationship("Color", backref=db.backref("supplier_catalog", lazy=True))
    type = db.relationship(
        "DeviceType", backref=db.backref("supplier_catalog", lazy=True)
    )
    ram = db.relationship(
        "RAMOption", backref=db.backref("supplier_catalog", lazy=True)
    )
    norme = db.relationship(
        "NormeOption", backref=db.backref("supplier_catalog", lazy=True)
    )

    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=True)
    supplier = db.relationship(
        "Supplier", backref=db.backref("supplier_catalog", lazy=True)
    )
    region = db.Column(db.String(30), nullable=True)


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

    model = db.Column(db.String(500), nullable=True)
    description = db.Column(db.String(500), nullable=True)

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
    region = db.Column(db.String(30), nullable=True)


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
    marge_percent = db.Column(db.Float, nullable=True)
    prixht_tcp_marge4_5 = db.Column(db.Float, nullable=False)
    prixht_marge4_5 = db.Column(db.Float, nullable=False)
    prixht_max = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
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
    import_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


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


class InternalProduct(db.Model):
    __tablename__ = "internal_products"

    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    odoo_id = db.Column(db.String(200), nullable=False)

    product = db.relationship(
        "Product", backref=db.backref("internal_products", lazy=True)
    )


class OdooConfig(db.Model):
    __tablename__ = "odoo_configs"

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False)
    database = db.Column(db.String(100), nullable=False)
    login = db.Column(db.String(100), nullable=False)
    _encrypted_password = db.Column("password", db.String(500), nullable=False)
    auto_sync_enabled = db.Column(db.Boolean, default=False)
    auto_sync_interval_minutes = db.Column(db.Integer, default=1440)
    last_auto_sync_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    @property
    def password(self):
        """Decrypt and return the plaintext password."""
        return decrypt_value(self._encrypted_password)

    @password.setter
    def password(self, plaintext):
        """Encrypt and store the password."""
        self._encrypted_password = encrypt_value(plaintext)


class OdooSyncJob(db.Model):
    __tablename__ = "odoo_sync_jobs"

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="running")
    trigger = db.Column(db.String(20), default="manual")
    error_message = db.Column(db.Text, nullable=True)
    total_odoo_products = db.Column(db.Integer, default=0)
    created_count = db.Column(db.Integer, default=0)
    updated_count = db.Column(db.Integer, default=0)
    unchanged_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    report_created = db.Column(JSONB, nullable=True)
    report_updated = db.Column(JSONB, nullable=True)
    report_unchanged = db.Column(JSONB, nullable=True)
    report_errors = db.Column(JSONB, nullable=True)
    deleted_count = db.Column(db.Integer, default=0)
    report_deleted = db.Column(JSONB, nullable=True)


class ModelReference(db.Model):
    __tablename__ = "model_references"

    id = db.Column(db.Integer, primary_key=True)
    manufacturer_code = db.Column(db.String(50), nullable=False, unique=True)
    commercial_name = db.Column(db.String(100), nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=True)
    brand = db.relationship("Brand", backref=db.backref("model_references", lazy=True))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class LabelCache(db.Model):
    __tablename__ = "label_cache"
    __table_args__ = (
        db.UniqueConstraint("supplier_id", "normalized_label", name="uix_label_cache"),
    )

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    supplier = db.relationship("Supplier", backref=db.backref("label_cache", lazy=True))
    normalized_label = db.Column(db.String(300), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    product = db.relationship("Product", backref=db.backref("label_cache", lazy=True))
    match_score = db.Column(db.Integer, nullable=True)
    match_source = db.Column(db.String(20), nullable=False)
    extracted_attributes = db.Column(JSONB, nullable=True)
    match_reasoning = db.Column(JSONB, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    action = db.Column(db.String(100), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    details = db.Column(JSONB, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)

    user = db.relationship("User", lazy="select")


class NightlyConfig(db.Model):
    __tablename__ = "nightly_config"

    id = db.Column(db.Integer, primary_key=True)
    enabled = db.Column(db.Boolean, default=False, nullable=False)
    run_hour = db.Column(db.Integer, default=2, nullable=False)
    run_minute = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class NightlyJob(db.Model):
    __tablename__ = "nightly_jobs"

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    status = db.Column(db.String(20), default="running", nullable=False)
    odoo_synced = db.Column(db.Integer, nullable=True)
    suppliers_synced = db.Column(db.Integer, nullable=True)
    matching_submitted = db.Column(db.Integer, nullable=True)
    email_sent = db.Column(db.Boolean, default=False, nullable=False)
    error_message = db.Column(db.Text, nullable=True)


class NightlyEmailRecipient(db.Model):
    __tablename__ = "nightly_email_recipients"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)


class PendingMatch(db.Model):
    __tablename__ = "pending_matches"

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=False)
    supplier = db.relationship("Supplier", backref=db.backref("pending_matches", lazy=True))
    temporary_import_id = db.Column(
        db.Integer, db.ForeignKey("supplier_catalog.id"), nullable=True
    )
    source_label = db.Column(db.String(300), nullable=False)
    extracted_attributes = db.Column(JSONB, nullable=False)
    candidates = db.Column(JSONB, nullable=False)
    status = db.Column(db.String(20), default="pending")
    resolved_product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime, nullable=True)

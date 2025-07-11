import math
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pandas as pd
from dotenv import load_dotenv
from flasgger import Swagger
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from models import (
    Brand,
    Color,
    ColorTranslation,
    DeviceType,
    Exclusion,
    ImportHistory,
    MemoryOption,
    Product,
    ProductCalculation,
    ProductReference,
    Supplier,
    TemporaryImport,
    db,
)


def create_app():
    # Load environment variables from a local .env file if present
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(env_path)

    app = Flask(__name__)
    Swagger(app, template_file="swagger_template.yml")

    frontend_origin = os.getenv("FRONTEND_URL", "*")
    origins = (
        [o.strip() for o in frontend_origin.split(",")] if frontend_origin else "*"
    )
    CORS(
        app,
        resources={r"/*": {"origins": origins}},
        expose_headers=["Content-Disposition"],
    )

    @app.route("/")
    def index():
        return {"message": "Hello World"}

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route("/product_calculation", methods=["GET"])
    def list_product_calculations():
        calculations = ProductCalculation.query.join(Product).all()
        result = [
            {
                "id": c.id,
                "product_id": c.product_id,
                "name": c.product.name if c.product else None,
                "description": c.product.description if c.product else None,
                "brand": (
                    c.product.brand.brand if c.product and c.product.brand else None
                ),
                "price": c.price,
                "memory": (
                    c.product.memory.memory if c.product and c.product.memory else None
                ),
                "color": (
                    c.product.color.color if c.product and c.product.color else None
                ),
                "type": c.product.type.type if c.product and c.product.type else None,
                "tcp": c.tcp,
                "marge4_5": c.marge4_5,
                "prixht_tcp_marge4_5": c.prixht_tcp_marge4_5,
                "prixht_marge4_5": c.prixht_marge4_5,
                "prixht_max": c.prixht_max,
                "date": c.date.strftime("%D") if c.date else None,
                "week": (
                    "S" + c.date.strftime("%W") + "-" + c.date.strftime("%Y")
                    if c.date
                    else None
                ),
            }
            for c in calculations
        ]
        return jsonify(result)

    @app.route("/suppliers", methods=["GET"])
    def list_suppliers():
        suppliers = Supplier.query.all()
        result = [
            {
                "id": s.id,
                "name": s.name,
                "email": s.email,
                "phone": s.phone,
                "address": s.address,
            }
            for s in suppliers
        ]
        return jsonify(result)

    @app.route("/import_history", methods=["GET"])
    def list_import_history():
        histories = ImportHistory.query.order_by(ImportHistory.import_date.desc()).all()
        result = [
            {
                "id": h.id,
                "filename": h.filename,
                "supplier_id": h.supplier_id,
                "product_count": h.product_count,
                "import_date": h.import_date.isoformat(),
            }
            for h in histories
        ]
        return jsonify(result)

    @app.route("/import", methods=["POST"])
    def create_import():
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        supplier_id = request.form.get("supplier_id")
        if supplier_id is not None:
            try:
                supplier_id = int(supplier_id)
            except ValueError:
                supplier_id = None

        # Clean previous temporary data
        TemporaryImport.query.delete()
        db.session.commit()

        df = pd.read_excel(file)
        df.columns = [c.lower().strip() for c in df.columns]
        if "description" in df.columns:
            df["description"] = df["description"].astype(str).str.strip()
        df.drop_duplicates(subset=["ean"], inplace=True)
        df = df[df["ean"].notna()]
        count_new = 0
        count_update = 0
        for _, row in df.iterrows():
            ean_value = str(int(row["ean"]))
            temp = TemporaryImport(
                description=row.get("description"),
                quantity=row.get("quantity", None),
                selling_price=row.get("sellingprice", None),
                ean=ean_value,
                supplier_id=supplier_id,
            )
            db.session.add(temp)

            ref = ProductReference.query.filter_by(
                ean=ean_value, supplier_id=supplier_id
            ).first()
            if ref:
                ref.description = row.get("description")
                ref.quantity = row.get("quantity", None)
                ref.selling_price = row.get("sellingprice", None)
                ref.supplier_id = supplier_id
                count_update += 1
            else:
                ref = ProductReference(
                    description=row.get("description"),
                    quantity=row.get("quantity", None),
                    selling_price=row.get("sellingprice", None),
                    ean=ean_value,
                    supplier_id=supplier_id,
                )
                count_new += 1
                db.session.add(ref)

        history = ImportHistory(
            filename=file.filename, supplier_id=supplier_id, product_count=len(df)
        )
        db.session.add(history)

        db.session.commit()
        return jsonify({"status": "success", "new": count_new, "updated": count_update})

    @app.route("/products", methods=["GET"])
    def list_products():
        products = Product.query.all()
        result = [
            {
                "id": p.id,
                "description": p.description,
                "name": p.name,
                "brand": p.brand.brand if p.brand else None,
                "price": (
                    p.reference.selling_price
                    if p.reference and p.reference.selling_price
                    else None
                ),
                "memory": p.memory.memory if p.memory else None,
                "color": p.color.color if p.color else None,
                "type": p.type.type if p.type else None,
                "reference": (
                    {
                        "id": p.reference.id if p.reference else None,
                        "description": p.reference.description if p.reference else None,
                    }
                    if p.reference
                    else None
                ),
            }
            for p in products
        ]
        return jsonify(result)

    @app.route("/last_import/<int:supplier_id>", methods=["GET"])
    def last_import(supplier_id):
        history = (
            ImportHistory.query.filter_by(supplier_id=supplier_id)
            .order_by(ImportHistory.import_date.desc())
            .first()
        )
        if not history:
            return jsonify({}), 200

        return jsonify(
            {
                "id": history.id,
                "filename": history.filename,
                "supplier_id": history.supplier_id,
                "product_count": history.product_count,
                "import_date": history.import_date.isoformat(),
            }
        )

    @app.route("/product_calculations/count", methods=["GET"])
    def count_product_calculations():
        count = ProductCalculation.query.count()
        return jsonify({"count": count})

    @app.route("/populate_products", methods=["POST"])
    def populate_products_from_reference():
        references = ProductReference.query.all()
        brands = Brand.query.all()
        colors = Color.query.all()
        memories = MemoryOption.query.all()
        types = DeviceType.query.all()
        color_transcos = ColorTranslation.query.all()
        exclusions = [e.term.lower() for e in Exclusion.query.all()]

        created = 0
        updated = 0
        for ref in references:
            description_lower = ref.description.lower() if ref.description else ""
            if any(exc in description_lower for exc in exclusions):
                continue

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
                    brand_id=brand_id,
                    color_id=color_id,
                    memory_id=memory_id,
                    type_id=type_id,
                    supplier_id=ref.supplier_id,
                )
                db.session.add(product)
                created += 1
        db.session.commit()
        return jsonify({"status": "success", "created": created, "updated": updated})

    @app.route("/calculate_products", methods=["POST"])
    def calculate_products():
        ProductCalculation.query.delete()
        db.session.commit()
        products = Product.query.all()
        created = 0
        for p in products:
            price = (
                p.reference.selling_price
                if p.reference and p.reference.selling_price
                else 0
            )
            memory = p.memory.memory.upper() if p.memory else ""
            tcp = 0
            if memory == "32GB":
                tcp = 10
            elif memory == "64GB":
                tcp = 12
            elif memory in ["128GB", "256GB", "512GB", "1TB"]:
                tcp = 14
            margin45 = price * 0.045
            price_with_tcp = price + tcp + margin45
            thresholds = [15, 29, 49, 79, 99, 129, 149, 179, 209, 299, 499, 799, 999]
            margins = [
                1.25,
                1.22,
                1.20,
                1.18,
                1.15,
                1.11,
                1.10,
                1.09,
                1.09,
                1.08,
                1.08,
                1.07,
                1.07,
                1.06,
            ]
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
                price=round(price, 2),
                tcp=round(tcp, 2),
                marge4_5=round(margin45, 2),
                prixht_tcp_marge4_5=round(price_with_tcp, 2),
                prixht_marge4_5=round(price_with_margin, 2),
                prixht_max=max_price,
                date=datetime.now(timezone.utc),
            )
            db.session.add(calc)
            created += 1
        db.session.commit()
        return jsonify({"status": "success", "created": created})

    @app.route("/export_calculates", methods=["GET"])
    def export_calculates():
        calcs = ProductCalculation.query.join(Product).all()
        rows = []
        for c in calcs:
            p = c.product
            rows.append(
                {
                    "id": p.id if p else None,
                    "reference_id": p.reference_id if p else None,
                    "name": p.name if p else None,
                    "description": p.description if p else None,
                    "brand": p.brand.brand if p.brand else None,
                    "price": c.price if c else None,
                    "memory": p.memory.memory if p.memory else None,
                    "color": p.color.color if p.color else None,
                    "type": p.type.type if p.type else None,
                    "supplier": p.supplier.name if p.supplier else None,
                    "TCP": c.tcp,
                    "Marge de 4,5%": c.marge4_5,
                    "Prix HT avec TCP et marge": c.prixht_tcp_marge4_5,
                    "Prix HT avec Marge": c.prixht_marge4_5,
                    "Prix HT Maximum": c.prixht_max,
                    "Date": c.date.isoformat() if c.date else None,
                    "Semaine": c.date.strftime("%Y-%W") if c.date else None,
                }
            )

        df = pd.DataFrame(rows)
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        filename = f"product_calculates_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @app.route("/refresh", methods=["POST"])
    def refresh():
        ProductCalculation.query.delete()
        return jsonify({"status": "success", "message": "Product calculations empty"})

    @app.route("/refresh_week", methods=["POST"])
    def refresh_week():
        data = request.get_json(silent=True)
        if not data or "dates" not in data:
            return jsonify({"error": "No date provided"}), 400

        try:
            date_objs = [datetime.fromisoformat(d) for d in data["dates"]]
        except Exception:
            return jsonify({"error": "Invalid date format"}), 400

        # Use monday as start of week and delete records for those weeks
        week_ranges = {}
        for d in date_objs:
            start = d - timedelta(days=d.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
            week_ranges[start] = end

        for start, end in week_ranges.items():
            ProductCalculation.query.filter(
                ProductCalculation.date >= start,
                ProductCalculation.date < end,
            ).delete(synchronize_session=False)

        db.session.commit()
        return jsonify(
            {
                "status": "success",
                "message": "Product calculations empty for selected weeks",
            }
        )

    @app.route("/brands", methods=["GET"])
    def list_brands():
        brands = Brand.query.all()
        result = [{"id": b.id, "brand": b.brand} for b in brands]
        return jsonify(result)

    @app.route("/colors", methods=["GET"])
    def list_colors():
        colors = Color.query.all()
        result = [{"id": c.id, "color": c.color} for c in colors]
        return jsonify(result)

    @app.route("/memory_options", methods=["GET"])
    def list_memory_options():
        memories = MemoryOption.query.all()
        result = [{"id": m.id, "memory": m.memory} for m in memories]
        return jsonify(result)

    @app.route("/device_types", methods=["GET"])
    def list_device_types():
        types = DeviceType.query.all()
        result = [{"id": t.id, "type": t.type} for t in types]
        return jsonify(result)

    @app.route("/exclusions", methods=["GET"])
    def list_exclusions():
        exclusions = Exclusion.query.all()
        result = [{"id": e.id, "term": e.term} for e in exclusions]
        return jsonify(result)

    @app.route("/references/<table>", methods=["GET"])
    def get_reference_table(table):
        mapping = {
            "suppliers": Supplier,
            "brands": Brand,
            "colors": Color,
            "memory_options": MemoryOption,
            "device_types": DeviceType,
            "exclusions": Exclusion,
        }
        model = mapping.get(table)
        if not model:
            return jsonify({"error": "Unknown table"}), 400
        items = model.query.all()

        def serialize(obj):
            if isinstance(obj, Supplier):
                return {
                    "id": obj.id,
                    "name": obj.name,
                    "email": obj.email,
                    "phone": obj.phone,
                    "address": obj.address,
                }
            if isinstance(obj, Brand):
                return {"id": obj.id, "brand": obj.brand}
            if isinstance(obj, Color):
                return {"id": obj.id, "color": obj.color}
            if isinstance(obj, MemoryOption):
                return {"id": obj.id, "memory": obj.memory}
            if isinstance(obj, DeviceType):
                return {"id": obj.id, "type": obj.type}
            if isinstance(obj, Exclusion):
                return {"id": obj.id, "term": obj.term}
            return {}

        return jsonify([serialize(i) for i in items])

    @app.route("/references/<table>/<int:item_id>", methods=["PUT"])
    def update_reference_item(table, item_id):
        mapping = {
            "suppliers": Supplier,
            "brands": Brand,
            "colors": Color,
            "memory_options": MemoryOption,
            "device_types": DeviceType,
            "exclusions": Exclusion,
        }
        model = mapping.get(table)
        if not model:
            return jsonify({"error": "Unknown table"}), 400
        item = model.query.get_or_404(item_id)
        data = request.json or {}
        for key, value in data.items():
            if hasattr(item, key):
                setattr(item, key, value)
        db.session.commit()
        return jsonify({"status": "success"})

    @app.route("/references/<table>", methods=["POST"])
    def create_reference_item(table):
        mapping = {
            "suppliers": Supplier,
            "brands": Brand,
            "colors": Color,
            "memory_options": MemoryOption,
            "device_types": DeviceType,
            "exclusions": Exclusion,
        }
        model = mapping.get(table)
        if not model:
            return jsonify({"error": "Unknown table"}), 400
        data = request.json or {}
        item = model(**data)
        db.session.add(item)
        db.session.commit()
        return jsonify({"id": item.id})

    @app.route("/references/<table>/<int:item_id>", methods=["DELETE"])
    def delete_reference_item(table, item_id):
        mapping = {
            "suppliers": Supplier,
            "brands": Brand,
            "colors": Color,
            "memory_options": MemoryOption,
            "device_types": DeviceType,
            "exclusions": Exclusion,
        }
        model = mapping.get(table)
        if not model:
            return jsonify({"error": "Unknown table"}), 400
        item = model.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        return jsonify({"status": "deleted"})

    return app


if __name__ == "__main__":
    app = create_app()
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5001"))
    app.run(host=host, port=port)

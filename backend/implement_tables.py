import os

import psycopg2
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL environment variable is not set")

conn = psycopg2.connect(db_url)
cur = conn.cursor()

cur.execute(
    """
    TRUNCATE TABLE suppliers, brands, colors, memory_options, device_types, exclusions, color_translations RESTART IDENTITY CASCADE;
"""
)
conn.commit()

cur.execute(
    """
    INSERT INTO suppliers (name) VALUES
    ('Yuka'),('supplier2')
    ;
"""
)

cur.execute(
    "INSERT INTO format_imports (supplier_id, column_name, column_type, column_order) VALUES (1, 'description', 'description', 1), (1, 'model', 'model', 2), (1, 'quantity', 'quantity', 3), (1, 'selling_price', 'selling_price', 4), (1, 'ean', 'ean', 5);"
)

cur.execute(
    """
    INSERT INTO brands(brand) VALUES ('Samsung'), ('Apple'), ('Huawei'), ('Xiaomi'), ('Oppo'),
    ('Dyson'), ('Sony'), ('LG'), ('Google'), ('Microsoft'), ('Lenovo'), ('Asus'),
    ('Dell'), ('HP'), ('Acer'), ('OnePlus'), ('Realme'),('Fairphone'),('JBL'), ('Bose'),
    ('Motorola'), ('Nokia'), ('Vivo'), ('ZTE'), ('Honor'),('GoPro'), ('Canon'), ('Nikon'),
    ('TCL'), ('Alcatel'), ('BlackBerry'), ('Panasonic'), ('Fujitsu'), ('Sharp'), ('Razer'), ('Logitech'),
    ('Corsair');
"""
)
cur.execute(
    "INSERT INTO memory_options (memory, tcp_value) VALUES ('32GB', 10),('64GB', 12), ('128GB', 14), ('256GB', 14), ('512GB', 14);"
)
cur.execute(
    "INSERT INTO colors (color) VALUES ('Blanc'), ('Noir'), ('Bleu'), ('Rouge'), ('Vert'),('Orange'),('Violet'),('Jaune'),('Rose');"
)
cur.execute(
    """

    INSERT INTO color_translations (color_source, color_target, color_target_id) VALUES
    ('black', 'Noir', 2),
    ('dark grey', 'Noir', 2),
    ('dark gray', 'Noir', 2),
    ('white', 'Blanc', 1),
    ('starlight', 'Blanc', 1),
    ('blue', 'Bleu', 3),
    ('blau', 'Bleu', 3),
    ('midnight', 'Bleu', 3),
    ('ultramarine', 'Bleu', 3),
    ('red', 'Rouge', 4),
    ('pink', 'Rose', 9),
    ('green', 'Vert', 5),
    ('orange', 'Orange', 6),
    ('purple', 'Violet', 7),
    ('gold', 'Blanc', 1),
    ('silver', 'Blanc', 1),
    ('grey', 'Noir', 2),
    ('gray', 'Noir', 2),
    ('champagne', 'Blanc', 1),
    ('rose', 'Rose', 9),
    ('yellow', 'Jaune', 8)
    
"""
)

cur.execute(
    "INSERT INTO device_types (type) VALUES ('Téléphone'), ('Tablette'), ('Montre'), ('Ordinateur'), ('Accessoire'),('Ecouteur'),('Chargeur'),('Câble'),('A définir');"
)
cur.execute(
    "INSERT INTO exclusions (term) VALUES ('Mac'), ('Backbone'), ('Bulk'), ('OH25B'), ('Soundbar');"
)

cur.execute(
    "INSERT INTO graph_settings (name, visible) VALUES ('global', True),('product', False),('relative', False),('distribution', False),('stdev', False),('range', False),('index', False),('correlation', False),('anomalies', False);"
)

conn.commit()
cur.close()
conn.close()



import os
from dotenv import load_dotenv
import psycopg2

env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL environment variable is not set")

conn = psycopg2.connect(db_url)
cur = conn.cursor()


cur.execute("""
    INSERT INTO suppliers (name) VALUES
    ('Yuka'),('supplier2')
    ;
""")

cur.execute("""
    INSERT INTO brands(brand) VALUES ('Samsung'), ('Apple'), ('Huawei'), ('Xiaomi'), ('Oppo'),
    ('Dyson'), ('Sony'), ('LG'), ('Google'), ('Microsoft'), ('Lenovo'), ('Asus'),
    ('Dell'), ('HP'), ('Acer'), ('OnePlus'), ('Realme'),('Fairphone'),('JBL'), ('Bose'),
    ('Motorola'), ('Nokia'), ('Vivo'), ('ZTE'), ('Honor'),('GoPro'), ('Canon'), ('Nikon'),
    ('TCL'), ('Alcatel'), ('BlackBerry'), ('Panasonic'), ('Fujitsu'), ('Sharp'), ('Razer'), ('Logitech'),
    ('Corsair');
""")
cur.execute("INSERT INTO memory_options (memory) VALUES ('32GB'),('64GB'), ('128GB'), ('256GB'), ('512GB');")
cur.execute("INSERT INTO colors (color) VALUES ('Blanc'), ('Noir'), ('Bleu'), ('Rouge'), ('Vert'),('Orange'),('Violet');")
cur.execute("""

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
    ('pink', 'Rouge', 4),
    ('green', 'Vert', 5),
    ('orange', 'Orange', 6),
    ('purple', 'Violet', 7),
    ('gold', 'Blanc', 1),
    ('silver', 'Blanc', 1),
    ('grey', 'Noir', 2),
    ('gray', 'Noir', 2),
    ('champagne', 'Blanc', 1);
""")

cur.execute("INSERT INTO device_types (type) VALUES ('Téléphone'), ('Tablette'), ('Montre'), ('Ordinateur');")

conn.commit()
cur.close()
conn.close()

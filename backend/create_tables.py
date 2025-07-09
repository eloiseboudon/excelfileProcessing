

# import os
# from dotenv import load_dotenv
# import psycopg2

# env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
# load_dotenv(env_path)
# db_url = os.getenv("DATABASE_URL")
# if not db_url:
#     raise RuntimeError("DATABASE_URL environment variable is not set")

# conn = psycopg2.connect(db_url)
# cur = conn.cursor()


# cur.execute("""DROP TABLE IF EXISTS temporary_imports CASCADE;""")
# cur.execute("""DROP TABLE IF EXISTS import_histories CASCADE;""")

# cur.execute("""DROP TABLE IF EXISTS device_types CASCADE;""")
# cur.execute("""DROP TABLE IF EXISTS color_translations CASCADE;""")
# cur.execute("""DROP TABLE IF EXISTS colors CASCADE;""")
# cur.execute("""DROP TABLE IF EXISTS memory_options CASCADE;""")
# cur.execute("""DROP TABLE IF EXISTS brands CASCADE;""")
# cur.execute("""DROP TABLE IF EXISTS suppliers CASCADE;""")

# cur.execute("""DROP TABLE IF EXISTS product_references CASCADE;""")  
# cur.execute("""DROP TABLE IF EXISTS products CASCADE;""")
# cur.execute("""DROP TABLE IF EXISTS product_calculations CASCADE;""")


# conn.commit()


# cur.execute("""
# CREATE TABLE IF NOT EXISTS suppliers (
#     id SERIAL PRIMARY KEY,
#     name VARCHAR(100) NOT NULL,
#     email VARCHAR(120) UNIQUE,
#     phone VARCHAR(20),
#     address VARCHAR(200)
# );
# """)


# cur.execute("""
# CREATE TABLE IF NOT EXISTS temporary_imports (
#     id SERIAL PRIMARY KEY,
#     description VARCHAR(200) NOT NULL,
#     quantity INTEGER,
#     selling_price FLOAT,
#     ean VARCHAR(20) NOT NULL,
#     supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
#     UNIQUE (ean, supplier_id)
# );
# """)

# cur.execute("""
# CREATE TABLE IF NOT EXISTS product_references (
#     id SERIAL PRIMARY KEY,
#     description VARCHAR(200) NOT NULL,
#     quantity INTEGER,
#     selling_price FLOAT,
#     ean VARCHAR(20) NOT NULL,
#     supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
#     UNIQUE (ean, supplier_id)
# );
# """)

# cur.execute("""
# CREATE TABLE IF NOT EXISTS brands (
#     id SERIAL PRIMARY KEY,
#     brand VARCHAR(50) NOT NULL
# );
# """)

# cur.execute("""
# CREATE TABLE IF NOT EXISTS memory_options (
#     id SERIAL PRIMARY KEY,
#     memory VARCHAR(50) NOT NULL
# );
# """)

# cur.execute("""
# CREATE TABLE IF NOT EXISTS colors (
#     id SERIAL PRIMARY KEY,
#     color VARCHAR(50) NOT NULL
# );
# """)

# cur.execute("""
# CREATE TABLE IF NOT EXISTS color_translations (
#     id SERIAL PRIMARY KEY,
#     color_source VARCHAR(50) NOT NULL,
#     color_target VARCHAR(50) NOT NULL,
#     color_target_id INTEGER REFERENCES colors(id) ON DELETE CASCADE
# );
# """)

# cur.execute("""
# CREATE TABLE IF NOT EXISTS device_types (
#     id SERIAL PRIMARY KEY,
#     type VARCHAR(50) NOT NULL
# );
# """)

# cur.execute("""
# CREATE TABLE IF NOT EXISTS products (
#     id SERIAL PRIMARY KEY,
#     reference_id INTEGER REFERENCES product_references(id) ON DELETE SET NULL,
#     description VARCHAR(120) NOT NULL,
#     name VARCHAR(120) NOT NULL,
#     brand_id INTEGER REFERENCES brands(id) ON DELETE SET NULL,
#     price FLOAT,
#     memory_id INTEGER REFERENCES memory_options(id) ON DELETE SET NULL,
#     color_id INTEGER REFERENCES colors(id) ON DELETE SET NULL,
#     type_id INTEGER REFERENCES device_types(id) ON DELETE SET NULL,
#     supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
#     UNIQUE (reference_id, supplier_id)
# );
# """)

# cur.execute("""
# CREATE TABLE IF NOT EXISTS product_calculations (
#     id SERIAL PRIMARY KEY,
#     product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
#     tcp FLOAT NOT NULL,
#     marge4_5 FLOAT NOT NULL,
#     prixHT_TCP_marge4_5 FLOAT NOT NULL,
#     prixHT_marge4_5 FLOAT NOT NULL,
#     prixHT_max FLOAT NOT NULL
# );
# """)

# cur.execute("""
# CREATE TABLE IF NOT EXISTS import_histories (
#     id SERIAL PRIMARY KEY,
#     filename VARCHAR(200) NOT NULL,
#     supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
#     product_count INTEGER NOT NULL,
#     import_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
# );
# """)

# conn.commit()

# cur.execute("""
#     INSERT INTO suppliers (name) VALUES
#     ('Yuka'),('supplier2')
#     ;
# """)

# cur.execute("""
#     INSERT INTO brands(brand) VALUES ('Samsung'), ('Apple'), ('Huawei'), ('Xiaomi'), ('Oppo'),
#     ('Dyson'), ('Sony'), ('LG'), ('Google'), ('Microsoft'), ('Lenovo'), ('Asus'),
#     ('Dell'), ('HP'), ('Acer'), ('OnePlus'), ('Realme'),('Fairphone'),('JBL'), ('Bose'),
#     ('Motorola'), ('Nokia'), ('Vivo'), ('ZTE'), ('Honor'),('GoPro'), ('Canon'), ('Nikon'),
#     ('TCL'), ('Alcatel'), ('BlackBerry'), ('Panasonic'), ('Fujitsu'), ('Sharp'), ('Razer'), ('Logitech'),
#     ('Corsair');
# """)
# cur.execute("INSERT INTO memory_options (memory) VALUES ('32GB'),('64GB'), ('128GB'), ('256GB'), ('512GB');")
# cur.execute("INSERT INTO colors (color) VALUES ('Blanc'), ('Noir'), ('Bleu'), ('Rouge'), ('Vert'),('Orange'),('Violet');")
# cur.execute("""

#     INSERT INTO color_translations (color_source, color_target, color_target_id) VALUES
#     ('black', 'Noir', 2),
#     ('dark grey', 'Noir', 2),
#     ('dark gray', 'Noir', 2),
#     ('white', 'Blanc', 1),
#     ('starlight', 'Blanc', 1),
#     ('blue', 'Bleu', 3),
#     ('blau', 'Bleu', 3),
#     ('midnight', 'Bleu', 3),
#     ('ultramarine', 'Bleu', 3),
#     ('red', 'Rouge', 4),
#     ('pink', 'Rouge', 4),
#     ('green', 'Vert', 5),
#     ('orange', 'Orange', 6),
#     ('purple', 'Violet', 7),
#     ('gold', 'Blanc', 1),
#     ('silver', 'Blanc', 1),
#     ('grey', 'Noir', 2),
#     ('gray', 'Noir', 2),
#     ('champagne', 'Blanc', 1);
# """)

# cur.execute("INSERT INTO device_types (type) VALUES ('Téléphone'), ('Tablette'), ('Montre'), ('Ordinateur');")

# conn.commit()
# cur.close()
# conn.close()

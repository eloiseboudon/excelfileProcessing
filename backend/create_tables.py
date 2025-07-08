

import psycopg2

conn = psycopg2.connect(
    dbname="ajtpro",
    user="eloise",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

cur.execute("""DROP TABLE IF EXISTS import_history;""")
cur.execute("""DROP TABLE IF EXISTS product_calculates;""")
cur.execute("""DROP TABLE IF EXISTS products;""") 
cur.execute("""DROP TABLE IF EXISTS size_references;""")
cur.execute("""DROP TABLE IF EXISTS type_references;""")
cur.execute("""DROP TABLE IF EXISTS color_transco;""")
cur.execute("""DROP TABLE IF EXISTS color_references;""")
cur.execute("""DROP TABLE IF EXISTS memory_references;""")
cur.execute("""DROP TABLE IF EXISTS brand_parameters;""")
cur.execute("""DROP TABLE IF EXISTS reference;""")    
cur.execute("""DROP TABLE IF EXISTS temp_imports;""")
cur.execute("""DROP TABLE IF EXISTS fournisseurs;""")
conn.commit()


cur.execute("""
CREATE TABLE IF NOT EXISTS fournisseurs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE,
    phone VARCHAR(20),
    address VARCHAR(200)
);
""")


cur.execute("""
CREATE TABLE IF NOT EXISTS temp_imports (
    id SERIAL PRIMARY KEY,
    description VARCHAR(200) NOT NULL,
    articelno VARCHAR(50),
    quantity INTEGER,
    selling_price FLOAT,
    ean VARCHAR(20) NOT NULL,
    id_fournisseur INTEGER REFERENCES fournisseurs(id) ON DELETE SET NULL,
    UNIQUE (ean, id_fournisseur)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS reference (
    id SERIAL PRIMARY KEY,
    description VARCHAR(200) NOT NULL,
    articelno VARCHAR(50),
    quantity INTEGER,
    selling_price FLOAT,
    ean VARCHAR(20) NOT NULL,
    id_fournisseur INTEGER REFERENCES fournisseurs(id) ON DELETE SET NULL,
    UNIQUE (ean, id_fournisseur)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS brand_parameters (
    id SERIAL PRIMARY KEY,
    brand VARCHAR(50) NOT NULL
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS memory_references (
    id SERIAL PRIMARY KEY,
    memory VARCHAR(50) NOT NULL
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS color_references (
    id SERIAL PRIMARY KEY,
    color VARCHAR(50) NOT NULL
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS color_transco (
    id SERIAL PRIMARY KEY,
    color_source VARCHAR(50) NOT NULL,
    color_target VARCHAR(50) NOT NULL,
    id_color_target INTEGER REFERENCES color_references(id) ON DELETE CASCADE
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS type_references (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    id_reference INTEGER REFERENCES reference(id) ON DELETE SET NULL,
    description VARCHAR(120) NOT NULL,
    name VARCHAR(120) NOT NULL,
    id_brand INTEGER REFERENCES brand_parameters(id) ON DELETE SET NULL,
    price FLOAT,
    id_memory INTEGER REFERENCES memory_references(id) ON DELETE SET NULL,
    id_color INTEGER REFERENCES color_references(id) ON DELETE SET NULL,
    id_type INTEGER REFERENCES type_references(id) ON DELETE SET NULL,
    id_fournisseur INTEGER REFERENCES fournisseurs(id) ON DELETE SET NULL,
    UNIQUE (id_reference, id_fournisseur)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS product_calculates (
    id SERIAL PRIMARY KEY,
    id_product INTEGER REFERENCES products(id) ON DELETE CASCADE,
    TCP FLOAT NOT NULL,
    marge4_5 FLOAT NOT NULL,
    prixHT_TCP_marge4_5 FLOAT NOT NULL,
    prixHT_marge4_5 FLOAT NOT NULL,
    prixHT_max FLOAT NOT NULL
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS import_history (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(200) NOT NULL,
    id_fournisseur INTEGER REFERENCES fournisseurs(id) ON DELETE SET NULL,
    product_count INTEGER NOT NULL,
    import_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
""")

conn.commit()

cur.execute("""
    INSERT INTO fournisseurs (name) VALUES
    ('Yuka'),('Fournisseur2')
    ;
""")

cur.execute("""
    INSERT INTO brand_parameters (brand) VALUES ('Samsung'), ('Apple'), ('Huawei'), ('Xiaomi'), ('Oppo'),
    ('Dyson'), ('Sony'), ('LG'), ('Google'), ('Microsoft'), ('Lenovo'), ('Asus'),
    ('Dell'), ('HP'), ('Acer'), ('OnePlus'), ('Realme'),('Fairphone'),('JBL'), ('Bose'),
    ('Motorola'), ('Nokia'), ('Vivo'), ('ZTE'), ('Honor'),('GoPro'), ('Canon'), ('Nikon'),
    ('TCL'), ('Alcatel'), ('BlackBerry'), ('Panasonic'), ('Fujitsu'), ('Sharp'), ('Razer'), ('Logitech'),
    ('Corsair');
""")
cur.execute("INSERT INTO memory_references (memory) VALUES ('32GB'),('64GB'), ('128GB'), ('256GB'), ('512GB');")
cur.execute("INSERT INTO color_references (color) VALUES ('Blanc'), ('Noir'), ('Bleu'), ('Rouge'), ('Vert'),('Orange'),('Violet');")
cur.execute("""
    INSERT INTO color_transco (color_source, color_target, id_color_target) VALUES 
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

cur.execute("INSERT INTO type_references (type) VALUES ('Téléphone'), ('Tablette'), ('Montre'), ('Ordinateur');")

conn.commit()
cur.close()
conn.close()

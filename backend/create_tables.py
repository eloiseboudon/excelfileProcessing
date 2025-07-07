

import psycopg2

conn = psycopg2.connect(
    dbname="ajtpro",
    user="eloise",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# cur.execute("""DROP TABLE IF EXISTS product_calculates;""")   
# cur.execute("""DROP TABLE IF EXISTS products;""") 
# cur.execute("""DROP TABLE IF EXISTS reference;""")    
# cur.execute("""DROP TABLE IF EXISTS temp_imports;""")

cur.execute("""
CREATE TABLE IF NOT EXISTS temp_imports (
    id SERIAL PRIMARY KEY,
    description VARCHAR(200) NOT NULL,
    articelno VARCHAR(50),
    quantity INTEGER,
    selling_price FLOAT,
    ean VARCHAR(20) UNIQUE NOT NULL
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS reference (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    articelno VARCHAR(50),
    quantity INTEGER,
    selling_price FLOAT,
    ean VARCHAR(20) UNIQUE NOT NULL
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    id_reference INTEGER REFERENCES reference(id) ON DELETE SET NULL,
    name VARCHAR(120) NOT NULL,
    brand VARCHAR(50),
    price FLOAT,
    memory VARCHAR(50),
    color VARCHAR(50)
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

conn.commit()
cur.close()
conn.close()
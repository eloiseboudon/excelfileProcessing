from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy without app context
# The app will initialize it later

db = SQLAlchemy()

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    brand = db.Column(db.String(50))
    price = db.Column(db.Float)

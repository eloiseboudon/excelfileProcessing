from . import imports, products, references, main


def register_routes(app):
    app.register_blueprint(main.bp)
    app.register_blueprint(imports.bp)
    app.register_blueprint(products.bp)
    app.register_blueprint(references.bp)

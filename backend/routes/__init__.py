from . import imports, products, references, main, stats, settings, auth, users, odoo


def register_routes(app):
    app.register_blueprint(main.bp)
    app.register_blueprint(imports.bp)
    app.register_blueprint(products.bp)
    app.register_blueprint(references.bp)
    app.register_blueprint(stats.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(odoo.bp)

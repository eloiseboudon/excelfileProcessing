# Lancez Python depuis votre répertoire racine
from backend import models

# Vérifiez que vos modèles sont dans les métadonnées
print("Tables dans metadata:", list(models.db.metadata.tables.keys()))
# Devrait afficher: ['tests', 'suppliers', 'temporary_imports', 'product_references', ...]

# Vérifiez que le modèle Test existe
print("Modèle Test:", models.Test)
print("Table Test:", models.Test.__table__)
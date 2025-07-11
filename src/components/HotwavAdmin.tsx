import React, { useState } from 'react';
import { Edit3, Save, X, Plus, Trash2 } from 'lucide-react';

interface HotwavProduct {
  nom: string;
  prix: number;
}

interface HotwavAdminProps {
  isVisible: boolean;
  onClose: () => void;
  onSave: (products: HotwavProduct[]) => void;
  initialProducts: HotwavProduct[];
}

function HotwavAdmin({ isVisible, onClose, onSave, initialProducts }: HotwavAdminProps) {
  const [products, setProducts] = useState<HotwavProduct[]>(initialProducts);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [newProduct, setNewProduct] = useState({ nom: '', prix: '' }); // Prix en string pour gérer l'état vide
  const [showAddForm, setShowAddForm] = useState(false);

  if (!isVisible) return null;

  const handleEdit = (index: number) => {
    setEditingIndex(index);
  };

  const handleSave = (index: number, updatedProduct: HotwavProduct) => {
    const updatedProducts = [...products];
    updatedProducts[index] = updatedProduct;
    setProducts(updatedProducts);
    setEditingIndex(null);
  };

  const handleDelete = (index: number) => {
    if (confirm('Êtes-vous sûr de vouloir supprimer ce produit ?')) {
      const updatedProducts = products.filter((_, i) => i !== index);
      setProducts(updatedProducts);
    }
  };

  const handleAddProduct = () => {
    const prix = parseFloat(newProduct.prix) || 0;
    if (newProduct.nom.trim() && prix > 0) {
      setProducts([...products, { nom: newProduct.nom, prix }]);
      setNewProduct({ nom: '', prix: '' });
      setShowAddForm(false);
    }
  };

  const handleSaveAll = () => {
    onSave(products);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-zinc-900 rounded-2xl border border-[#B8860B]/30 max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-[#B8860B] p-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-black">Administration Produits Hotwav</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-black/10 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-black" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {/* Add Product Button */}
          <div className="mb-6">
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg flex items-center space-x-2 hover:bg-green-700 transition-colors"
            >
              <Plus className="w-5 h-5" />
              <span>Ajouter un produit</span>
            </button>
          </div>

          {/* Add Product Form */}
          {showAddForm && (
            <div className="mb-6 p-4 bg-zinc-800 rounded-lg border border-zinc-700">
              <h3 className="text-lg font-semibold text-white mb-4">Nouveau produit</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">
                    Nom du produit
                  </label>
                  <input
                    type="text"
                    value={newProduct.nom}
                    onChange={(e) => setNewProduct({ ...newProduct, nom: e.target.value })}
                    className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white focus:border-[#B8860B] focus:outline-none"
                    placeholder="Ex: Hotwav Note 20 4G DS 8/128Gb Black"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">
                    Prix (€)
                  </label>
                  <input
                    type="number"
                    value={newProduct.prix}
                    onChange={(e) => setNewProduct({ ...newProduct, prix: e.target.value })}
                    className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white focus:border-[#B8860B] focus:outline-none"
                    placeholder="Ex: 125"
                    min="0"
                    step="0.01"
                  />
                </div>
              </div>
              <div className="flex space-x-2 mt-4">
                <button
                  onClick={handleAddProduct}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  Ajouter
                </button>
                <button
                  onClick={() => {
                    setShowAddForm(false);
                    setNewProduct({ nom: '', prix: '' });
                  }}
                  className="px-4 py-2 bg-zinc-600 text-white rounded-lg hover:bg-zinc-700 transition-colors"
                >
                  Annuler
                </button>
              </div>
            </div>
          )}

          {/* Products List */}
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-white mb-4">
              Produits Hotwav ({products.length})
            </h3>
            {products.map((product, index) => (
              <ProductRow
                key={index}
                product={product}
                index={index}
                isEditing={editingIndex === index}
                onEdit={() => handleEdit(index)}
                onSave={(updatedProduct) => handleSave(index, updatedProduct)}
                onCancel={() => setEditingIndex(null)}
                onDelete={() => handleDelete(index)}
              />
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 bg-zinc-800 border-t border-zinc-700 flex justify-between items-center">
          <div className="text-sm text-zinc-400">
            {products.length} produits • Modifications non sauvegardées
          </div>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="px-6 py-2 bg-zinc-600 text-white rounded-lg hover:bg-zinc-700 transition-colors"
            >
              Annuler
            </button>
            <button
              onClick={handleSaveAll}
              className="px-6 py-2 bg-[#B8860B] text-black rounded-lg hover:bg-[#B8860B]/90 transition-colors font-semibold"
            >
              Sauvegarder tout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

interface ProductRowProps {
  product: HotwavProduct;
  index: number;
  isEditing: boolean;
  onEdit: () => void;
  onSave: (product: HotwavProduct) => void;
  onCancel: () => void;
  onDelete: () => void;
}

function ProductRow({ product, index, isEditing, onEdit, onSave, onCancel, onDelete }: ProductRowProps) {
  const [editedProduct, setEditedProduct] = useState({ nom: product.nom, prix: product.prix.toString() });

  React.useEffect(() => {
    setEditedProduct({ nom: product.nom, prix: product.prix.toString() });
  }, [product]);

  const handleSaveClick = () => {
    const prix = parseFloat(editedProduct.prix) || 0;
    onSave({ nom: editedProduct.nom, prix });
  };

  if (isEditing) {
    return (
      <div className="p-4 bg-zinc-800 rounded-lg border border-[#B8860B]/30">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Nom du produit
            </label>
            <input
              type="text"
              value={editedProduct.nom}
              onChange={(e) => setEditedProduct({ ...editedProduct, nom: e.target.value })}
              className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white focus:border-[#B8860B] focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Prix (€)
            </label>
            <input
              type="number"
              value={editedProduct.prix}
              onChange={(e) => setEditedProduct({ ...editedProduct, prix: e.target.value })}
              className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white focus:border-[#B8860B] focus:outline-none"
              min="0"
              step="0.01"
            />
          </div>
        </div>
        <div className="flex space-x-2 mt-4">
          <button
            onClick={handleSaveClick}
            className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 transition-colors flex items-center space-x-1"
          >
            <Save className="w-4 h-4" />
            <span>Sauver</span>
          </button>
          <button
            onClick={onCancel}
            className="px-3 py-1 bg-zinc-600 text-white rounded hover:bg-zinc-700 transition-colors"
          >
            Annuler
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700 hover:border-zinc-600 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="font-medium text-white">{product.nom}</div>
          <div className="text-[#B8860B] font-semibold">{product.prix} €</div>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={onEdit}
            className="p-2 text-blue-400 hover:bg-blue-400/10 rounded transition-colors"
            title="Modifier"
          >
            <Edit3 className="w-4 h-4" />
          </button>
          <button
            onClick={onDelete}
            className="p-2 text-red-400 hover:bg-red-400/10 rounded transition-colors"
            title="Supprimer"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default HotwavAdmin;
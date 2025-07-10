import React, { useState } from 'react';
import { Edit3, Save, X, Plus, Trash2, Tag } from 'lucide-react';

interface Accessory {
  nom: string;
  prix: number;
  marque: string; // Nouvelle propriété pour la marque
}

interface AccessoriesAdminProps {
  isVisible: boolean;
  onClose: () => void;
  onSave: (accessories: Accessory[]) => void;
  initialAccessories: Accessory[];
}

const AVAILABLE_BRANDS = [
  'Apple',
  'Samsung',
  'Xiaomi',
  'Hotwav',
  'JBL',
  'Google',
  'Honor',
  'Nothing',
  'Universel' // Pour les accessoires compatibles avec plusieurs marques
];

function AccessoriesAdmin({ isVisible, onClose, onSave, initialAccessories }: AccessoriesAdminProps) {
  const [accessories, setAccessories] = useState<Accessory[]>(initialAccessories);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [newAccessory, setNewAccessory] = useState({ nom: '', prix: '', marque: 'Apple' });
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedBrandFilter, setSelectedBrandFilter] = useState<string>('all');

  if (!isVisible) return null;

  const handleEdit = (index: number) => {
    setEditingIndex(index);
  };

  const handleSave = (index: number, updatedAccessory: Accessory) => {
    const updatedAccessories = [...accessories];
    updatedAccessories[index] = updatedAccessory;
    setAccessories(updatedAccessories);
    setEditingIndex(null);
  };

  const handleDelete = (index: number) => {
    if (confirm('Êtes-vous sûr de vouloir supprimer cet accessoire ?')) {
      const updatedAccessories = accessories.filter((_, i) => i !== index);
      setAccessories(updatedAccessories);
    }
  };

  const handleAddAccessory = () => {
    const prix = parseFloat(newAccessory.prix) || 0;
    if (newAccessory.nom.trim() && prix > 0 && newAccessory.marque) {
      setAccessories([...accessories, {
        nom: newAccessory.nom,
        prix,
        marque: newAccessory.marque
      }]);
      setNewAccessory({ nom: '', prix: '', marque: 'Apple' });
      setShowAddForm(false);
    }
  };

  const handleSaveAll = () => {
    onSave(accessories);
    onClose();
  };

  // Filtrer les accessoires par marque
  const filteredAccessories = selectedBrandFilter === 'all'
    ? accessories
    : accessories.filter(acc => acc.marque === selectedBrandFilter);

  // Grouper les accessoires par marque pour l'affichage
  const accessoriesByBrand = accessories.reduce((acc, accessory) => {
    if (!acc[accessory.marque]) {
      acc[accessory.marque] = [];
    }
    acc[accessory.marque].push(accessory);
    return acc;
  }, {} as Record<string, Accessory[]>);

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-zinc-900 rounded-2xl border border-purple-500/30 max-w-5xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-purple-600 p-6 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">Administration Accessoires</h2>
            <p className="text-purple-100 text-sm mt-1">Organisés par marque pour un rangement optimal</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-black/10 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-white" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {/* Add Accessory Button */}
          <div className="mb-6 flex items-center justify-between">
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg flex items-center space-x-2 hover:bg-green-700 transition-colors"
            >
              <Plus className="w-5 h-5" />
              <span>Ajouter un accessoire</span>
            </button>

            {/* Filtre par marque */}
            <div className="flex items-center space-x-2">
              <span className="text-sm text-zinc-400">Filtrer par marque:</span>
              <select
                value={selectedBrandFilter}
                onChange={(e) => setSelectedBrandFilter(e.target.value)}
                className="px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white text-sm focus:border-purple-500 focus:outline-none"
              >
                <option value="all">Toutes les marques</option>
                {AVAILABLE_BRANDS.map(brand => (
                  <option key={brand} value={brand}>{brand}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Add Accessory Form */}
          {showAddForm && (
            <div className="mb-6 p-4 bg-zinc-800 rounded-lg border border-zinc-700">
              <h3 className="text-lg font-semibold text-white mb-4">Nouvel accessoire</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">
                    Nom de l'accessoire
                  </label>
                  <input
                    type="text"
                    value={newAccessory.nom}
                    onChange={(e) => setNewAccessory({ ...newAccessory, nom: e.target.value })}
                    className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                    placeholder="Ex: Coque iPhone 15 Pro Max Transparente"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">
                    Prix (€)
                  </label>
                  <input
                    type="number"
                    value={newAccessory.prix}
                    onChange={(e) => setNewAccessory({ ...newAccessory, prix: e.target.value })}
                    className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                    placeholder="Ex: 15"
                    min="0"
                    step="0.01"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">
                    Marque
                  </label>
                  <select
                    value={newAccessory.marque}
                    onChange={(e) => setNewAccessory({ ...newAccessory, marque: e.target.value })}
                    className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                  >
                    {AVAILABLE_BRANDS.map(brand => (
                      <option key={brand} value={brand}>{brand}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex space-x-2 mt-4">
                <button
                  onClick={handleAddAccessory}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  Ajouter
                </button>
                <button
                  onClick={() => {
                    setShowAddForm(false);
                    setNewAccessory({ nom: '', prix: '', marque: 'Apple' });
                  }}
                  className="px-4 py-2 bg-zinc-600 text-white rounded-lg hover:bg-zinc-700 transition-colors"
                >
                  Annuler
                </button>
              </div>
            </div>
          )}

          {/* Accessories List */}
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">
                Accessoires ({filteredAccessories.length})
              </h3>
              {selectedBrandFilter !== 'all' && (
                <div className="flex items-center space-x-2 text-sm text-zinc-400">
                  <Tag className="w-4 h-4" />
                  <span>Filtré par: {selectedBrandFilter}</span>
                </div>
              )}
            </div>

            {filteredAccessories.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-6xl mb-4">🔧</div>
                <p className="text-zinc-400 text-lg">
                  {selectedBrandFilter === 'all'
                    ? 'Aucun accessoire configuré'
                    : `Aucun accessoire pour ${selectedBrandFilter}`
                  }
                </p>
                <p className="text-zinc-500 text-sm mt-2">
                  Ajoutez vos premiers accessoires pour commencer
                </p>
              </div>
            ) : (
              <>
                {/* Vue filtrée */}
                {selectedBrandFilter !== 'all' ? (
                  <div className="space-y-2">
                    {filteredAccessories.map((accessory, index) => {
                      const originalIndex = accessories.findIndex(acc =>
                        acc.nom === accessory.nom && acc.prix === accessory.prix && acc.marque === accessory.marque
                      );
                      return (
                        <AccessoryRow
                          key={`${accessory.marque}-${index}`}
                          accessory={accessory}
                          index={originalIndex}
                          isEditing={editingIndex === originalIndex}
                          onEdit={() => handleEdit(originalIndex)}
                          onSave={(updatedAccessory) => handleSave(originalIndex, updatedAccessory)}
                          onCancel={() => setEditingIndex(null)}
                          onDelete={() => handleDelete(originalIndex)}
                        />
                      );
                    })}
                  </div>
                ) : (
                  /* Vue groupée par marque */
                  <div className="space-y-6">
                    {Object.entries(accessoriesByBrand)
                      .sort(([a], [b]) => a.localeCompare(b))
                      .map(([brand, brandAccessories]) => (
                        <div key={brand} className="bg-zinc-800/30 rounded-lg border border-zinc-700">
                          <div className="bg-zinc-700 px-4 py-3 rounded-t-lg">
                            <div className="flex items-center justify-between">
                              <h4 className="font-semibold text-white flex items-center space-x-2">
                                <Tag className="w-4 h-4 text-purple-400" />
                                <span>{brand}</span>
                              </h4>
                              <span className="text-sm text-zinc-400">
                                {brandAccessories.length} accessoire{brandAccessories.length > 1 ? 's' : ''}
                              </span>
                            </div>
                          </div>
                          <div className="p-4 space-y-2">
                            {brandAccessories.map((accessory, brandIndex) => {
                              const originalIndex = accessories.findIndex(acc =>
                                acc.nom === accessory.nom && acc.prix === accessory.prix && acc.marque === accessory.marque
                              );
                              return (
                                <AccessoryRow
                                  key={`${brand}-${brandIndex}`}
                                  accessory={accessory}
                                  index={originalIndex}
                                  isEditing={editingIndex === originalIndex}
                                  onEdit={() => handleEdit(originalIndex)}
                                  onSave={(updatedAccessory) => handleSave(originalIndex, updatedAccessory)}
                                  onCancel={() => setEditingIndex(null)}
                                  onDelete={() => handleDelete(originalIndex)}
                                />
                              );
                            })}
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 bg-zinc-800 border-t border-zinc-700 flex justify-between items-center">
          <div className="text-sm text-zinc-400">
            {accessories.length} accessoires • {Object.keys(accessoriesByBrand).length} marques • Modifications non sauvegardées
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
              className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-semibold"
            >
              Sauvegarder tout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

interface AccessoryRowProps {
  accessory: Accessory;
  index: number;
  isEditing: boolean;
  onEdit: () => void;
  onSave: (accessory: Accessory) => void;
  onCancel: () => void;
  onDelete: () => void;
}

function AccessoryRow({ accessory, index, isEditing, onEdit, onSave, onCancel, onDelete }: AccessoryRowProps) {
  const [editedAccessory, setEditedAccessory] = useState({
    nom: accessory.nom,
    prix: accessory.prix.toString(),
    marque: accessory.marque
  });

  React.useEffect(() => {
    setEditedAccessory({
      nom: accessory.nom,
      prix: accessory.prix.toString(),
      marque: accessory.marque
    });
  }, [accessory]);

  const handleSaveClick = () => {
    const prix = parseFloat(editedAccessory.prix) || 0;
    onSave({
      nom: editedAccessory.nom,
      prix,
      marque: editedAccessory.marque
    });
  };

  if (isEditing) {
    return (
      <div className="p-4 bg-zinc-800 rounded-lg border border-purple-500/30">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Nom de l'accessoire
            </label>
            <input
              type="text"
              value={editedAccessory.nom}
              onChange={(e) => setEditedAccessory({ ...editedAccessory, nom: e.target.value })}
              className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white focus:border-purple-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Prix (€)
            </label>
            <input
              type="number"
              value={editedAccessory.prix}
              onChange={(e) => setEditedAccessory({ ...editedAccessory, prix: e.target.value })}
              className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white focus:border-purple-500 focus:outline-none"
              min="0"
              step="0.01"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Marque
            </label>
            <select
              value={editedAccessory.marque}
              onChange={(e) => setEditedAccessory({ ...editedAccessory, marque: e.target.value })}
              className="w-full px-3 py-2 bg-zinc-700 border border-zinc-600 rounded-lg text-white focus:border-purple-500 focus:outline-none"
            >
              {AVAILABLE_BRANDS.map(brand => (
                <option key={brand} value={brand}>{brand}</option>
              ))}
            </select>
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
          <div className="font-medium text-white">{accessory.nom}</div>
          <div className="flex items-center space-x-3 mt-1">
            <div className="text-purple-400 font-semibold">{accessory.prix} €</div>
            <div className="flex items-center space-x-1 text-xs">
              <Tag className="w-3 h-3 text-zinc-400" />
              <span className="text-zinc-400">{accessory.marque}</span>
            </div>
          </div>
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

export default AccessoriesAdmin;

import React, { useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import HotwavAdmin from './HotwavAdmin';
import AccessoriesAdmin from './AccessoriesAdmin';
import ReferenceAdmin from './ReferenceAdmin';

interface AdminPageProps {
  onBack: () => void;
}

function AdminPage({ onBack }: AdminPageProps) {
  const [showHotwav, setShowHotwav] = useState(false);
  const [showAccessories, setShowAccessories] = useState(false);
  const [showReferences, setShowReferences] = useState(false);

  return (
    <div className="max-w-6xl mx-auto px-2 sm:px-4 py-6 sm:py-8">
      <button
        onClick={onBack}
        className="flex items-center space-x-2 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700 transition-colors mb-6"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Retour</span>
      </button>
      <h1 className="text-4xl font-bold text-center mb-6">Administration</h1>
      <div className="flex justify-center space-x-4">
        <button
          onClick={() => setShowHotwav(true)}
          className="px-6 py-3 bg-[#B8860B] text-black rounded-lg font-semibold hover:bg-[#B8860B]/90"
        >
          Produits Hotwav
        </button>
        <button
          onClick={() => setShowAccessories(true)}
          className="px-6 py-3 bg-[#B8860B] text-black rounded-lg font-semibold hover:bg-[#B8860B]/90"
        >
          Accessoires
        </button>
        <button
          onClick={() => setShowReferences(true)}
          className="px-6 py-3 bg-[#B8860B] text-black rounded-lg font-semibold hover:bg-[#B8860B]/90"
        >
          Tables référence
        </button>
      </div>
      <HotwavAdmin
        isVisible={showHotwav}
        onClose={() => setShowHotwav(false)}
        onSave={() => { }}
        initialProducts={[]}
      />
      <AccessoriesAdmin
        isVisible={showAccessories}
        onClose={() => setShowAccessories(false)}
        onSave={() => { }}
        initialAccessories={[]}
      />
      <ReferenceAdmin
        isVisible={showReferences}
        onClose={() => setShowReferences(false)}
      />
    </div>
  );
}

export default AdminPage;

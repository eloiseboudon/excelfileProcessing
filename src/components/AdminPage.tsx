import React, { useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import ReferenceAdmin from './ReferenceAdmin';
import TranslationAdmin from './TranslationAdmin';

interface AdminPageProps {
  onBack: () => void;
}

function AdminPage({ onBack }: AdminPageProps) {
  const [showReferences, setShowReferences] = useState(false);
  const [showTranslations, setShowTranslations] = useState(false);

  return (
    <div className="max-w-7xl mx-auto px-1 sm:px-2 py-6 sm:py-8">
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
          onClick={() => setShowReferences(true)}
          className="px-6 py-3 bg-[#B8860B] text-black rounded-lg font-semibold hover:bg-[#B8860B]/90"
        >
          Tables référence
        </button>
      </div>
         <div className="flex justify-center space-x-4">
        <button
          onClick={() => setShowTranslations(true)}
          className="px-6 py-3 bg-[#B8860B] text-black rounded-lg font-semibold hover:bg-[#B8860B]/90"
        >
          Cohérence des tables de référence
        </button>
      </div>
      <ReferenceAdmin
        isVisible={showReferences}
        onClose={() => setShowReferences(false)}
      />
      <TranslationAdmin
        isVisible={showTranslations}
        onClose={() => setShowTranslations(false)}
      />
    </div>
  );
}

export default AdminPage;

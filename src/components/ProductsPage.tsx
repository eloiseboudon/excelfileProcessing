import React, { useState } from 'react';
import { ArrowLeft } from 'lucide-react';

interface ProductsPageProps {
  onBack: () => void;
}

function ProductsPage({ onBack }: ProductsPageProps) {
  return (
    <div className="max-w-6xl mx-auto px-2 sm:px-4 py-6 sm:py-8">
      <button
        onClick={onBack}
        className="flex items-center space-x-2 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700 transition-colors mb-6"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Retour</span>
      </button>
    </div>
  );
}

export default ProductsPage;

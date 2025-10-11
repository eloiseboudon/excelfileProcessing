import { ArrowLeft } from 'lucide-react';
import { useState } from 'react';
import ReferenceAdmin from './ReferenceAdmin';
import SupplierApiAdmin from './SupplierApiAdmin';
import TranslationAdmin from './TranslationAdmin';
import UserAdmin from './UserAdmin';

interface AdminPageProps {
  onBack: () => void;
}

function AdminPage({ onBack }: AdminPageProps) {
  const [showReferences, setShowReferences] = useState(false);
  const [showTranslations, setShowTranslations] = useState(false);
  const [showUsers, setShowUsers] = useState(false);
  const [showApiManagement, setShowApiManagement] = useState(false);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
      <button
        onClick={onBack}
        className="btn btn-secondary mb-6"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Retour</span>
      </button>
      <h1 className="text-4xl font-bold text-center mb-6">Administration</h1>
      <div className="flex justify-center space-x-4">
        <button
          onClick={() => setShowReferences(true)}
          className="btn btn-primary px-6 py-3"
        >
          Tables référence
        </button>
        <button
          onClick={() => setShowTranslations(true)}
          className="btn btn-primary px-6 py-3"
        >
          Cohérence des tables de référence
        </button>
        <button
          onClick={() => setShowApiManagement(true)}
          className="btn btn-primary px-6 py-3"
        >
          Gestion API fournisseurs
        </button>
        <button
          onClick={() => setShowUsers(true)}
          className="btn btn-primary px-6 py-3"
        >
          Gestion utilisateurs
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
      <SupplierApiAdmin
        isVisible={showApiManagement}
        onClose={() => setShowApiManagement(false)}
      />
      <UserAdmin
        isVisible={showUsers}
        onClose={() => setShowUsers(false)}
      />
    </div>
  );
}

export default AdminPage;

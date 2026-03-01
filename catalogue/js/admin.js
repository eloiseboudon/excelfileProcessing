/* ========== ADMIN BACKOFFICE — ALPINE.JS APP ========== */

const STORAGE_KEY = 'hotwav_admin_products';
const CATEGORIES = {
  'rugged-phones': 'Smartphones Renforcés',
  'phones': 'Smartphones',
  'rugged-tabs': 'Tablettes Renforcées',
  'tabs': 'Tablettes',
};

function adminApp() {
  return {
    // ========== STATE ==========
    products: [],
    editingIndex: null,
    searchQuery: '',
    catFilter: '',
    showProductModal: false,
    showPreview: false,
    showConfirm: false,
    confirmText: '',
    confirmCallback: null,
    previewProduct: null,
    toasts: [],
    dragSrcIndex: null,
    uploadingColorIndex: null,
    highlightInput: '',
    form: {
      id: '', name: '', cat: 'rugged-phones', badge: '4G', specs: '',
      screen: '', ram: '', storage: '', battery: '', camera: '', protection: '',
      highlights: [],
      colors: [{ name: 'Black', hex: '#1a1a1a', img: '', url: '' }],
    },

    // ========== INIT ==========
    init() {
      this.loadProducts();
      this.$watch('products', () => this.saveProducts());
    },

    loadProducts() {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        try {
          this.products = JSON.parse(stored);
        } catch {
          this.products = [];
        }
      }
      if (!this.products.length && typeof PRODUCTS !== 'undefined') {
        this.products = JSON.parse(JSON.stringify(PRODUCTS));
        this.saveProducts();
      }
    },

    saveProducts() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.products));
    },

    // ========== GETTERS ==========
    get filteredProducts() {
      const search = this.searchQuery.toLowerCase();
      return this.products
        .map((p, i) => ({ ...p, _idx: i }))
        .filter(p => {
          if (this.catFilter && p.cat !== this.catFilter) return false;
          if (search && !p.name.toLowerCase().includes(search) && !p.id.toLowerCase().includes(search)) return false;
          return true;
        });
    },

    get stats() {
      const byCat = { 'rugged-phones': 0, 'phones': 0, 'rugged-tabs': 0, 'tabs': 0 };
      this.products.forEach(p => { if (byCat[p.cat] !== undefined) byCat[p.cat]++; });
      return {
        total: this.products.length,
        ruggedPhones: byCat['rugged-phones'],
        phones: byCat['phones'],
        ruggedTabs: byCat['rugged-tabs'],
        tabs: byCat['tabs'],
        colors: this.products.reduce((sum, p) => sum + (p.colors ? p.colors.length : 0), 0),
      };
    },

    get existingColorsPalette() {
      const seen = new Map();
      this.products.forEach(p => {
        (p.colors || []).forEach(c => {
          if (c.name && c.hex && !seen.has(c.name)) {
            seen.set(c.name, c.hex);
          }
        });
      });
      return Array.from(seen.entries()).sort((a, b) => a[0].localeCompare(b[0]));
    },

    // ========== HELPERS ==========
    badgeClass(badge) {
      if (badge === '5G') return 'badge-5g';
      if (badge === 'LTE') return 'badge-lte';
      if (badge === 'soon') return 'badge-soon';
      return 'badge-4g';
    },

    badgeLabel(badge) {
      return badge === 'soon' ? 'Bientôt' : badge;
    },

    categoryLabel(cat) {
      return CATEGORIES[cat] || cat;
    },

    // ========== CRUD ==========
    openAddModal() {
      this.editingIndex = null;
      this.resetForm();
      this.showProductModal = true;
    },

    editProduct(idx) {
      this.editingIndex = idx;
      const p = this.products[idx];
      this.form = {
        id: p.id,
        name: p.name,
        cat: p.cat,
        badge: p.badge,
        specs: p.specs,
        screen: p.details.screen || '',
        ram: p.details.ram || '',
        storage: p.details.storage || '',
        battery: p.details.battery || '',
        camera: p.details.camera || '',
        protection: p.details.protection || '',
        highlights: [...(p.highlights || [])],
        colors: (p.colors || []).map(c => ({ ...c })),
      };
      this.showProductModal = true;
    },

    duplicateProduct(idx) {
      const orig = this.products[idx];
      const copy = JSON.parse(JSON.stringify(orig));
      copy.id = orig.id + '-copy';
      copy.name = orig.name + ' (copie)';
      this.products.splice(idx + 1, 0, copy);
      this.showToast('success', `"${copy.name}" dupliqué`);
    },

    confirmDelete(idx) {
      const p = this.products[idx];
      this.confirmText = `Supprimer "${p.name}" ?`;
      this.confirmCallback = () => {
        this.deleteProduct(idx);
        this.showConfirm = false;
      };
      this.showConfirm = true;
    },

    deleteProduct(idx) {
      const name = this.products[idx].name;
      this.products.splice(idx, 1);
      this.showToast('success', `"${name}" supprimé`);
    },

    saveProduct() {
      const { id, name, cat, badge } = this.form;
      if (!id.trim() || !name.trim() || !cat || !badge) {
        this.showToast('error', 'Les champs ID, Nom, Catégorie et Badge sont obligatoires');
        return;
      }

      const dupeIdx = this.products.findIndex(p => p.id === id.trim());
      if (dupeIdx !== -1 && dupeIdx !== this.editingIndex) {
        this.showToast('error', `L'ID "${id}" est déjà utilisé par un autre produit`);
        return;
      }

      const product = {
        id: id.trim(),
        name: name.trim(),
        cat,
        badge,
        specs: this.form.specs.trim(),
        highlights: [...this.form.highlights],
        details: {
          screen: this.form.screen.trim() || '—',
          ram: this.form.ram.trim() || '—',
          storage: this.form.storage.trim() || '—',
          battery: this.form.battery.trim() || '—',
          camera: this.form.camera.trim() || '—',
          protection: this.form.protection.trim() || '—',
        },
        colors: this.form.colors.map(c => ({
          name: c.name, hex: c.hex, img: c.img, url: c.url,
        })),
      };

      if (this.editingIndex !== null) {
        this.products[this.editingIndex] = product;
        this.showToast('success', `"${name}" modifié`);
      } else {
        this.products.push(product);
        this.showToast('success', `"${name}" ajouté`);
      }

      this.showProductModal = false;
    },

    resetForm() {
      this.form = {
        id: '', name: '', cat: 'rugged-phones', badge: '4G', specs: '',
        screen: '', ram: '', storage: '', battery: '', camera: '', protection: '',
        highlights: [],
        colors: [{ name: 'Black', hex: '#1a1a1a', img: '', url: '' }],
      };
      this.highlightInput = '';
    },

    // ========== HIGHLIGHTS ==========
    addHighlight() {
      const val = this.highlightInput.trim();
      if (val && !this.form.highlights.includes(val)) {
        this.form.highlights.push(val);
        this.highlightInput = '';
      }
    },

    removeHighlight(idx) {
      this.form.highlights.splice(idx, 1);
    },

    handleHighlightKey(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        this.addHighlight();
      }
    },

    // ========== COLOR VARIANTS ==========
    addColor() {
      this.form.colors.push({ name: '', hex: '#808080', img: '', url: '' });
    },

    removeColor(idx) {
      if (this.form.colors.length <= 1) return;
      this.form.colors.splice(idx, 1);
    },

    selectExistingColor(name, hex) {
      this.form.colors.push({ name, hex, img: '', url: '' });
    },

    // ========== IMAGE UPLOAD ==========
    uploadImage(colorIndex) {
      if (this.uploadingColorIndex !== null) return;

      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/png,image/jpeg,image/webp';
      input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        this.uploadingColorIndex = colorIndex;

        const uploadUrl = document.body.dataset.uploadUrl || 'http://localhost:8090';
        const token = document.body.dataset.uploadToken || '';

        const formData = new FormData();
        formData.append('file', file);
        formData.append('product_id', this.form.id || 'new-product');
        formData.append('color_name', this.form.colors[colorIndex].name || `color-${colorIndex}`);

        try {
          const resp = await fetch(`${uploadUrl}/upload`, {
            method: 'POST',
            headers: { 'X-Upload-Token': token },
            body: formData,
          });
          const data = await resp.json();
          if (resp.ok) {
            this.form.colors[colorIndex].img = data.path;
            this.showToast('success', 'Image uploadee');
          } else {
            this.showToast('error', data.error || 'Erreur upload');
          }
        } catch (err) {
          this.showToast('error', 'Erreur reseau : ' + err.message);
        } finally {
          this.uploadingColorIndex = null;
        }
      };
      input.click();
    },

    isUploadingColor(i) {
      return this.uploadingColorIndex === i;
    },

    // ========== DRAG & DROP ==========
    onDragStart(e, idx) {
      this.dragSrcIndex = idx;
      e.currentTarget.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
    },

    onDragOver(e) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      e.currentTarget.classList.add('drag-over');
    },

    onDragLeave(e) {
      e.currentTarget.classList.remove('drag-over');
    },

    onDrop(e, destIdx) {
      e.preventDefault();
      e.currentTarget.classList.remove('drag-over');
      if (this.dragSrcIndex !== null && this.dragSrcIndex !== destIdx) {
        const moved = this.products.splice(this.dragSrcIndex, 1)[0];
        this.products.splice(destIdx, 0, moved);
        this.showToast('info', 'Ordre mis à jour');
      }
    },

    onDragEnd(e) {
      e.currentTarget.classList.remove('dragging');
      document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
      this.dragSrcIndex = null;
    },

    // ========== PREVIEW ==========
    openPreview(idx) {
      this.previewProduct = this.products[idx];
      this.showPreview = true;
    },

    // ========== CONFIRM ==========
    executeConfirm() {
      if (this.confirmCallback) this.confirmCallback();
    },

    // ========== KEYBOARD ==========
    handleEscape() {
      if (this.showPreview) { this.showPreview = false; }
      else if (this.showConfirm) { this.showConfirm = false; }
      else if (this.showProductModal) { this.showProductModal = false; }
    },

    // ========== EXPORT ==========
    exportProductsJS() {
      const lines = [];
      lines.push("const BASE = 'https://shop.ajtpro.com';");
      lines.push('');
      lines.push('const PRODUCTS = [');
      lines.push('');

      const catComments = {
        'rugged-phones': '// ===== SMARTPHONES RENFORCÉS =====',
        'phones': '// ===== SMARTPHONES =====',
        'rugged-tabs': '// ===== TABLETTES RENFORCÉES =====',
        'tabs': '// ===== TABLETTES =====',
      };

      let lastCat = null;
      this.products.forEach(p => {
        if (p.cat !== lastCat) {
          if (lastCat !== null) lines.push('');
          lines.push(catComments[p.cat] || `// ===== ${p.cat.toUpperCase()} =====`);
          lastCat = p.cat;
        }
        lines.push('{');
        lines.push(`  id: ${jsStr(p.id)}, name: ${jsStr(p.name)}, cat: ${jsStr(p.cat)},`);
        lines.push(`  badge: ${jsStr(p.badge)}, specs: ${jsStr(p.specs)},`);
        lines.push(`  highlights: [${(p.highlights || []).map(h => jsStr(h)).join(', ')}],`);
        const d = p.details || {};
        lines.push(`  details: { screen: ${jsStr(d.screen || '—')}, ram: ${jsStr(d.ram || '—')}, storage: ${jsStr(d.storage || '—')}, battery: ${jsStr(d.battery || '—')}, camera: ${jsStr(d.camera || '—')}, protection: ${jsStr(d.protection || '—')} },`);
        lines.push('  colors: [');
        (p.colors || []).forEach(c => {
          lines.push(`    { name: ${jsStr(c.name)}, hex: ${jsStr(c.hex)}, img: ${jsStr(c.img)}, url: ${jsStr(c.url)} },`);
        });
        lines.push('  ],');
        lines.push('},');
      });

      lines.push('');
      lines.push('];');

      const content = lines.join('\n') + '\n';
      this.downloadFile('products.js', content, 'application/javascript');
      this.showToast('success', 'products.js exporté !');
    },

    // ========== IMPORT ==========
    importProductsJS() {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.js';
      input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
          try {
            const text = ev.target.result;
            const parsed = this.parseProductsJS(text);
            if (parsed && parsed.length) {
              this.products = parsed;
              this.showToast('success', `${parsed.length} produits importés depuis ${file.name}`);
            } else {
              this.showToast('error', 'Aucun produit trouvé dans le fichier');
            }
          } catch (err) {
            this.showToast('error', 'Erreur lors du parsing : ' + err.message);
          }
        };
        reader.readAsText(file);
      };
      input.click();
    },

    parseProductsJS(text) {
      const wrapped = text
        .replace(/^const\s+BASE\s*=/, 'var BASE =')
        .replace(/^const\s+PRODUCTS\s*=/, 'var PRODUCTS =');
      const fn = new Function(wrapped + '\nreturn PRODUCTS;');
      return fn();
    },

    // ========== RESET ==========
    resetFromOriginal() {
      if (typeof PRODUCTS === 'undefined') {
        this.showToast('error', 'products.js original non chargé');
        return;
      }
      this.confirmText = 'Recharger depuis le fichier products.js original ? Les modifications non exportées seront perdues.';
      this.confirmCallback = () => {
        this.products = JSON.parse(JSON.stringify(PRODUCTS));
        this.showConfirm = false;
        this.showToast('success', `${this.products.length} produits rechargés depuis l'original`);
      };
      this.showConfirm = true;
    },

    // ========== TOASTS ==========
    showToast(type, message) {
      const id = Date.now() + Math.random();
      this.toasts.push({ id, type, message, fading: false });
      setTimeout(() => {
        const t = this.toasts.find(t => t.id === id);
        if (t) t.fading = true;
        setTimeout(() => {
          this.toasts = this.toasts.filter(t => t.id !== id);
        }, 300);
      }, 3000);
    },

    toastIcon(type) {
      if (type === 'success') return 'ti-check';
      if (type === 'error') return 'ti-x';
      return 'ti-info-circle';
    },

    // ========== UTILITIES ==========
    downloadFile(filename, content, mimeType) {
      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    },
  };
}

function jsStr(val) {
  if (val === undefined || val === null) return "''";
  return "'" + String(val).replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'";
}

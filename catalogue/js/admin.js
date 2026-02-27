/* ========== ADMIN BACKOFFICE — LOGIC ========== */

const STORAGE_KEY = 'hotwav_admin_products';
const CATEGORIES = {
  'rugged-phones': 'Smartphones Renforcés',
  'phones': 'Smartphones',
  'rugged-tabs': 'Tablettes Renforcées',
  'tabs': 'Tablettes',
};
const BADGES = ['5G', '4G', 'LTE', 'soon'];

let products = [];
let editingIndex = null; // null = add, number = edit index
let dragSrcIndex = null;

// ========== INIT ==========

function initAdmin() {
  loadProducts();
  renderStats();
  renderTable();
  bindToolbarEvents();
}

function loadProducts() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try {
      products = JSON.parse(stored);
    } catch {
      products = [];
    }
  }
  // If no localStorage data, load from PRODUCTS global (products.js)
  if (!products.length && typeof PRODUCTS !== 'undefined') {
    products = JSON.parse(JSON.stringify(PRODUCTS));
    saveProducts();
  }
}

function saveProducts() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(products));
}

// ========== STATS ==========

function renderStats() {
  const total = products.length;
  const byCat = {};
  Object.keys(CATEGORIES).forEach(k => byCat[k] = 0);
  products.forEach(p => { if (byCat[p.cat] !== undefined) byCat[p.cat]++; });

  const totalColors = products.reduce((sum, p) => sum + (p.colors ? p.colors.length : 0), 0);

  document.getElementById('stat-total').textContent = total;
  document.getElementById('stat-rugged-phones').textContent = byCat['rugged-phones'];
  document.getElementById('stat-phones').textContent = byCat['phones'];
  document.getElementById('stat-rugged-tabs').textContent = byCat['rugged-tabs'];
  document.getElementById('stat-tabs').textContent = byCat['tabs'];
  document.getElementById('stat-colors').textContent = totalColors;
}

// ========== TABLE ==========

function renderTable() {
  const tbody = document.getElementById('products-tbody');
  const search = document.getElementById('search-input').value.toLowerCase();
  const catFilter = document.getElementById('cat-filter').value;

  const filtered = products
    .map((p, i) => ({ ...p, _idx: i }))
    .filter(p => {
      if (catFilter && p.cat !== catFilter) return false;
      if (search && !p.name.toLowerCase().includes(search) && !p.id.toLowerCase().includes(search)) return false;
      return true;
    });

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><i class="ti ti-package-off"></i><p>Aucun produit trouvé</p></div></td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(p => {
    const badgeClass = p.badge === '5G' ? 'badge-5g' : p.badge === 'LTE' ? 'badge-lte' : p.badge === 'soon' ? 'badge-soon' : 'badge-4g';
    const thumb = p.colors && p.colors.length ? p.colors[0].img : '';
    const colorDots = (p.colors || []).slice(0, 6).map(c =>
      `<span class="color-dot-mini" style="background:${c.hex}" title="${c.name}"></span>`
    ).join('');
    const extraColors = (p.colors || []).length > 6 ? `<span style="font-size:11px;color:var(--text-dim)">+${p.colors.length - 6}</span>` : '';

    return `<tr data-idx="${p._idx}" draggable="true">
      <td><span class="drag-handle" title="Réordonner"><i class="ti ti-grip-vertical"></i></span></td>
      <td>
        <div class="product-name-cell">
          ${thumb ? `<img class="product-thumb" src="${thumb}" alt="${p.name}" onerror="this.style.display='none'">` : ''}
          <div>
            <div class="product-name-text">${escapeHtml(p.name)}</div>
            <div class="product-id">${escapeHtml(p.id)}</div>
          </div>
        </div>
      </td>
      <td>${CATEGORIES[p.cat] || p.cat}</td>
      <td><span class="badge ${badgeClass}">${p.badge === 'soon' ? 'Bientôt' : p.badge}</span></td>
      <td><div class="color-dots-cell">${colorDots}${extraColors}</div></td>
      <td>
        <div class="actions-cell">
          <button class="btn-icon" title="Prévisualiser" onclick="previewProduct(${p._idx})"><i class="ti ti-eye"></i></button>
          <button class="btn-icon" title="Modifier" onclick="editProduct(${p._idx})"><i class="ti ti-pencil"></i></button>
          <button class="btn-icon" title="Dupliquer" onclick="duplicateProduct(${p._idx})"><i class="ti ti-copy"></i></button>
          <button class="btn-icon danger" title="Supprimer" onclick="confirmDelete(${p._idx})"><i class="ti ti-trash"></i></button>
        </div>
      </td>
    </tr>`;
  }).join('');

  // Bind drag events
  bindDragEvents();
}

function bindToolbarEvents() {
  document.getElementById('search-input').addEventListener('input', renderTable);
  document.getElementById('cat-filter').addEventListener('change', renderTable);
}

// ========== CRUD ==========

function openAddModal() {
  editingIndex = null;
  resetForm();
  document.getElementById('modal-title-text').textContent = 'Ajouter un produit';
  document.getElementById('product-modal').classList.add('open');
}

function editProduct(idx) {
  editingIndex = idx;
  const p = products[idx];
  document.getElementById('modal-title-text').textContent = 'Modifier le produit';

  document.getElementById('f-id').value = p.id;
  document.getElementById('f-name').value = p.name;
  document.getElementById('f-cat').value = p.cat;
  document.getElementById('f-badge').value = p.badge;
  document.getElementById('f-specs').value = p.specs;
  document.getElementById('f-screen').value = p.details.screen || '';
  document.getElementById('f-ram').value = p.details.ram || '';
  document.getElementById('f-storage').value = p.details.storage || '';
  document.getElementById('f-battery').value = p.details.battery || '';
  document.getElementById('f-camera').value = p.details.camera || '';
  document.getElementById('f-protection').value = p.details.protection || '';

  // Highlights
  currentHighlights = [...(p.highlights || [])];
  renderHighlights();

  // Colors
  currentColors = (p.colors || []).map(c => ({ ...c }));
  renderColorVariants();

  document.getElementById('product-modal').classList.add('open');
}

function duplicateProduct(idx) {
  const orig = products[idx];
  const copy = JSON.parse(JSON.stringify(orig));
  copy.id = orig.id + '-copy';
  copy.name = orig.name + ' (copie)';
  products.splice(idx + 1, 0, copy);
  saveProducts();
  renderStats();
  renderTable();
  showToast('success', `"${copy.name}" dupliqué`);
}

function confirmDelete(idx) {
  const p = products[idx];
  document.getElementById('confirm-text').textContent = `Supprimer "${p.name}" ?`;
  document.getElementById('confirm-action').onclick = () => {
    deleteProduct(idx);
    closeConfirm();
  };
  document.getElementById('confirm-dialog').classList.add('open');
}

function deleteProduct(idx) {
  const name = products[idx].name;
  products.splice(idx, 1);
  saveProducts();
  renderStats();
  renderTable();
  showToast('success', `"${name}" supprimé`);
}

function closeConfirm() {
  document.getElementById('confirm-dialog').classList.remove('open');
}

function closeProductModal() {
  document.getElementById('product-modal').classList.remove('open');
  editingIndex = null;
}

function saveProduct() {
  const id = document.getElementById('f-id').value.trim();
  const name = document.getElementById('f-name').value.trim();
  const cat = document.getElementById('f-cat').value;
  const badge = document.getElementById('f-badge').value;
  const specs = document.getElementById('f-specs').value.trim();

  if (!id || !name || !cat || !badge) {
    showToast('error', 'Les champs ID, Nom, Catégorie et Badge sont obligatoires');
    return;
  }

  // Check duplicate ID (except when editing same product)
  const dupeIdx = products.findIndex(p => p.id === id);
  if (dupeIdx !== -1 && dupeIdx !== editingIndex) {
    showToast('error', `L'ID "${id}" est déjà utilisé par un autre produit`);
    return;
  }

  const product = {
    id,
    name,
    cat,
    badge,
    specs,
    highlights: [...currentHighlights],
    details: {
      screen: document.getElementById('f-screen').value.trim() || '—',
      ram: document.getElementById('f-ram').value.trim() || '—',
      storage: document.getElementById('f-storage').value.trim() || '—',
      battery: document.getElementById('f-battery').value.trim() || '—',
      camera: document.getElementById('f-camera').value.trim() || '—',
      protection: document.getElementById('f-protection').value.trim() || '—',
    },
    colors: currentColors.map(c => ({
      name: c.name,
      hex: c.hex,
      img: c.img,
      url: c.url,
    })),
  };

  if (editingIndex !== null) {
    products[editingIndex] = product;
    showToast('success', `"${name}" modifié`);
  } else {
    products.push(product);
    showToast('success', `"${name}" ajouté`);
  }

  saveProducts();
  renderStats();
  renderTable();
  closeProductModal();
}

function resetForm() {
  document.getElementById('f-id').value = '';
  document.getElementById('f-name').value = '';
  document.getElementById('f-cat').value = 'rugged-phones';
  document.getElementById('f-badge').value = '4G';
  document.getElementById('f-specs').value = '';
  document.getElementById('f-screen').value = '';
  document.getElementById('f-ram').value = '';
  document.getElementById('f-storage').value = '';
  document.getElementById('f-battery').value = '';
  document.getElementById('f-camera').value = '';
  document.getElementById('f-protection').value = '';
  currentHighlights = [];
  renderHighlights();
  currentColors = [{ name: 'Black', hex: '#1a1a1a', img: '', url: '' }];
  renderColorVariants();
}

// ========== HIGHLIGHTS ==========

let currentHighlights = [];

function renderHighlights() {
  const container = document.getElementById('highlights-tags');
  container.innerHTML = currentHighlights.map((h, i) =>
    `<span class="tag">${escapeHtml(h)}<button onclick="removeHighlight(${i})">&times;</button></span>`
  ).join('');
}

function addHighlight() {
  const input = document.getElementById('highlight-input');
  const val = input.value.trim();
  if (val && !currentHighlights.includes(val)) {
    currentHighlights.push(val);
    renderHighlights();
    input.value = '';
  }
  input.focus();
}

function removeHighlight(idx) {
  currentHighlights.splice(idx, 1);
  renderHighlights();
}

function handleHighlightKey(e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    addHighlight();
  }
}

// ========== COLOR VARIANTS ==========

let currentColors = [{ name: 'Black', hex: '#1a1a1a', img: '', url: '' }];

function getExistingColors() {
  const seen = new Map();
  products.forEach(p => {
    (p.colors || []).forEach(c => {
      if (c.name && c.hex && !seen.has(c.name)) {
        seen.set(c.name, c.hex);
      }
    });
  });
  return Array.from(seen.entries()).sort((a, b) => a[0].localeCompare(b[0]));
}

function selectExistingColor(name, hex) {
  currentColors.push({ name, hex, img: '', url: '' });
  renderColorVariants();
}

function renderColorVariants() {
  const container = document.getElementById('color-variants');
  const palette = getExistingColors();

  const paletteHtml = palette.length ? `
    <div class="existing-colors-palette">
      <div class="palette-label">Couleurs existantes <span>(cliquer pour ajouter)</span></div>
      <div class="palette-dots">
        ${palette.map(([name, hex]) =>
          `<button type="button" class="palette-dot" style="background:${hex}" title="${escapeHtml(name)}" onclick="selectExistingColor('${escapeHtml(name).replace(/'/g, "\\'")}', '${hex}')">
            <span class="palette-dot-name">${escapeHtml(name)}</span>
          </button>`
        ).join('')}
      </div>
    </div>
  ` : '';

  container.innerHTML = paletteHtml + currentColors.map((c, i) => `
    <div class="color-variant-item">
      <div class="form-group">
        <label>Couleur</label>
        <input type="color" value="${c.hex}" onchange="updateColor(${i}, 'hex', this.value)">
      </div>
      <div class="form-group">
        <label>Nom</label>
        <input type="text" value="${escapeHtml(c.name)}" placeholder="Black" onchange="updateColor(${i}, 'name', this.value)">
      </div>
      <div class="form-group">
        <label>Image</label>
        <input type="text" value="${escapeHtml(c.img)}" placeholder="imgs/xxx.png" onchange="updateColor(${i}, 'img', this.value)">
      </div>
      <div class="form-group">
        <label>URL boutique</label>
        <input type="text" value="${escapeHtml(c.url)}" placeholder="/shop/xxx" onchange="updateColor(${i}, 'url', this.value)">
      </div>
      <button class="btn-icon danger" title="Supprimer" onclick="removeColor(${i})" ${currentColors.length <= 1 ? 'disabled style="opacity:0.3"' : ''}>
        <i class="ti ti-trash"></i>
      </button>
    </div>
  `).join('');
}

function addColor() {
  currentColors.push({ name: '', hex: '#808080', img: '', url: '' });
  renderColorVariants();
}

function removeColor(idx) {
  if (currentColors.length <= 1) return;
  currentColors.splice(idx, 1);
  renderColorVariants();
}

function updateColor(idx, field, value) {
  currentColors[idx][field] = value;
}

// ========== DRAG & DROP ==========

function bindDragEvents() {
  const rows = document.querySelectorAll('#products-tbody tr[draggable]');
  rows.forEach(row => {
    row.addEventListener('dragstart', onDragStart);
    row.addEventListener('dragover', onDragOver);
    row.addEventListener('dragleave', onDragLeave);
    row.addEventListener('drop', onDrop);
    row.addEventListener('dragend', onDragEnd);
  });
}

function onDragStart(e) {
  dragSrcIndex = parseInt(e.currentTarget.dataset.idx);
  e.currentTarget.classList.add('dragging');
  e.dataTransfer.effectAllowed = 'move';
}

function onDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  e.currentTarget.classList.add('drag-over');
}

function onDragLeave(e) {
  e.currentTarget.classList.remove('drag-over');
}

function onDrop(e) {
  e.preventDefault();
  const destIdx = parseInt(e.currentTarget.dataset.idx);
  e.currentTarget.classList.remove('drag-over');

  if (dragSrcIndex !== null && dragSrcIndex !== destIdx) {
    const moved = products.splice(dragSrcIndex, 1)[0];
    products.splice(destIdx, 0, moved);
    saveProducts();
    renderTable();
    showToast('info', 'Ordre mis à jour');
  }
}

function onDragEnd(e) {
  e.currentTarget.classList.remove('dragging');
  document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
  dragSrcIndex = null;
}

// ========== PREVIEW ==========

function previewProduct(idx) {
  const p = products[idx];
  const c0 = p.colors && p.colors[0];
  const badgeClass = p.badge === '5G' ? 'badge-5g' : p.badge === 'LTE' ? 'badge-lte' : p.badge === 'soon' ? 'badge-soon' : 'badge-4g';
  const badgeLabel = p.badge === 'soon' ? 'Bientôt' : p.badge;

  const colorDots = (p.colors || []).map((c, ci) =>
    `<div class="color-dot ${ci === 0 ? 'active' : ''}" style="background:${c.hex}" title="${c.name}"></div>`
  ).join('');

  const highlights = (p.highlights || []).map(h =>
    `<span class="card-hl">${escapeHtml(h)}</span>`
  ).join('');

  document.getElementById('preview-content').innerHTML = `
    <div class="preview-card">
      <div class="card-img-wrap">
        <span class="card-badge ${badgeClass}">${badgeLabel}</span>
        ${c0 && c0.img ? `<img class="card-img" src="${c0.img}" alt="${escapeHtml(p.name)}" onerror="this.style.display='none'">` : ''}
      </div>
      <div class="card-body">
        <div class="card-name">${escapeHtml(p.name)}</div>
        <div class="card-specs">${escapeHtml(p.specs)}</div>
        <div class="card-highlights">${highlights}</div>
        <div class="card-bottom">
          <div class="color-dots">${colorDots}</div>
          <span class="card-cart"><i class="ti ti-shopping-cart"></i></span>
        </div>
      </div>
    </div>
  `;
  document.getElementById('preview-overlay').classList.add('open');
}

function closePreview() {
  document.getElementById('preview-overlay').classList.remove('open');
}

// ========== EXPORT products.js ==========

function exportProductsJS() {
  const lines = [];
  lines.push("const BASE = 'https://shop.ajtpro.com';");
  lines.push('');
  lines.push('const PRODUCTS = [');
  lines.push('');

  // Group by category
  const catOrder = ['rugged-phones', 'phones', 'rugged-tabs', 'tabs'];
  const catComments = {
    'rugged-phones': '// ===== SMARTPHONES RENFORCÉS =====',
    'phones': '// ===== SMARTPHONES =====',
    'rugged-tabs': '// ===== TABLETTES RENFORCÉES =====',
    'tabs': '// ===== TABLETTES =====',
  };

  let lastCat = null;

  products.forEach(p => {
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
    (p.colors || []).forEach((c, ci) => {
      const comma = ci < p.colors.length - 1 ? ',' : ',';
      const parts = [];
      parts.push(`name: ${jsStr(c.name)}`);
      parts.push(`hex: ${jsStr(c.hex)}`);
      parts.push(`img: ${jsStr(c.img)}`);
      parts.push(`url: ${jsStr(c.url)}`);
      lines.push(`    { ${parts.join(', ')} }${comma}`);
    });
    lines.push('  ],');
    lines.push('},');
  });

  lines.push('');
  lines.push('];');

  const content = lines.join('\n') + '\n';
  downloadFile('products.js', content, 'application/javascript');
  showToast('success', 'products.js exporté !');
}

function jsStr(val) {
  if (val === undefined || val === null) return "''";
  return "'" + String(val).replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'";
}

// ========== IMPORT products.js ==========

function importProductsJS() {
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
        // Parse the JS file: extract the PRODUCTS array
        const parsed = parseProductsJS(text);
        if (parsed && parsed.length) {
          products = parsed;
          saveProducts();
          renderStats();
          renderTable();
          showToast('success', `${parsed.length} produits importés depuis ${file.name}`);
        } else {
          showToast('error', 'Aucun produit trouvé dans le fichier');
        }
      } catch (err) {
        showToast('error', 'Erreur lors du parsing : ' + err.message);
      }
    };
    reader.readAsText(file);
  };
  input.click();
}

function parseProductsJS(text) {
  // Strategy: use Function constructor to evaluate the JS safely
  // The file defines const BASE and const PRODUCTS
  // We wrap it so we can extract PRODUCTS
  const wrapped = text
    .replace(/^const\s+BASE\s*=/, 'var BASE =')
    .replace(/^const\s+PRODUCTS\s*=/, 'var PRODUCTS =');

  const fn = new Function(wrapped + '\nreturn PRODUCTS;');
  return fn();
}

// ========== RESET ==========

function resetFromOriginal() {
  if (typeof PRODUCTS === 'undefined') {
    showToast('error', 'products.js original non chargé');
    return;
  }
  document.getElementById('confirm-text').textContent = 'Recharger depuis le fichier products.js original ? Les modifications non exportées seront perdues.';
  document.getElementById('confirm-action').onclick = () => {
    products = JSON.parse(JSON.stringify(PRODUCTS));
    saveProducts();
    renderStats();
    renderTable();
    closeConfirm();
    showToast('success', `${products.length} produits rechargés depuis l'original`);
  };
  document.getElementById('confirm-dialog').classList.add('open');
}

// ========== UTILITIES ==========

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function downloadFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function showToast(type, message) {
  const container = document.getElementById('toast-container');
  const iconMap = { success: 'ti-check', error: 'ti-x', info: 'ti-info-circle' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<i class="ti ${iconMap[type] || 'ti-info-circle'}"></i> ${escapeHtml(message)}`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    toast.style.transition = 'all .3s';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ========== KEYBOARD ==========

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    if (document.getElementById('preview-overlay').classList.contains('open')) {
      closePreview();
    } else if (document.getElementById('confirm-dialog').classList.contains('open')) {
      closeConfirm();
    } else if (document.getElementById('product-modal').classList.contains('open')) {
      closeProductModal();
    }
  }
});

// ========== INIT ==========
document.addEventListener('DOMContentLoaded', initAdmin);

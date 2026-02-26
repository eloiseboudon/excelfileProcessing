// ===== RENDER =====
function renderProducts() {
  const grids = {
    'rugged-phones': document.getElementById('grid-rugged-phones'),
    'phones':        document.getElementById('grid-phones'),
    'rugged-tabs':   document.getElementById('grid-rugged-tabs'),
    'tabs':          document.getElementById('grid-tabs'),
  };

  PRODUCTS.forEach((p, idx) => {
    const grid = grids[p.cat];
    if (!grid) return;

    const c0 = p.colors[0];
    const badgeClass = p.badge === '5G'   ? 'badge-5g'
                     : p.badge === 'LTE'  ? 'badge-lte'
                     : p.badge === 'soon' ? 'badge-soon'
                     : 'badge-4g';

    const card = document.createElement('div');
    card.className = 'card reveal';
    card.dataset.product = idx;
    card.style.animationDelay = (idx % 6) * 0.05 + 's';
    card.onclick = () => openModal(idx);

    card.innerHTML = `
      <div class="card-img-wrap">
        <span class="card-badge ${badgeClass}">${p.badge === 'soon' ? 'Bientôt' : p.badge}</span>
        <img class="card-img" id="img-${p.id}" src="${c0.img}" alt="${p.name}" loading="lazy"
          onerror="this.parentElement.innerHTML='<div class=img-fallback>${p.name}</div>'">
      </div>
      <div class="card-body">
        <div class="card-name">${p.name}</div>
        <div class="card-specs">${p.specs}</div>
        <div class="card-highlights">
          ${p.highlights.map(h => `<span class="card-hl">${h}</span>`).join('')}
        </div>
        <div class="card-bottom">
          <div class="color-dots">
            ${p.colors.map((c, ci) => `
              <div class="color-dot ${ci === 0 ? 'active' : ''}"
                   style="background:${c.hex}" title="${c.name}"
                   onclick="event.stopPropagation(); switchColor('${p.id}', ${idx}, ${ci})">
              </div>
            `).join('')}
          </div>
          <a class="card-cart" id="cart-${p.id}"
             href="${p.badge === 'soon' ? '#' : BASE + c0.url}"
             target="_blank"
             onclick="event.stopPropagation()">
            ${p.badge === 'soon' ? '⏳' : '🛒'}
          </a>
        </div>
      </div>
    `;

    grid.appendChild(card);
  });
}

// ===== COLOR SWITCH (card) =====
function switchColor(pid, prodIdx, colorIdx) {
  const p = PRODUCTS[prodIdx];
  const c = p.colors[colorIdx];

  const img = document.getElementById('img-' + pid);
  if (img) img.src = c.img;

  const cart = document.getElementById('cart-' + pid);
  if (cart && p.badge !== 'soon') cart.href = BASE + c.url;

  const card = document.querySelector(`[data-product="${prodIdx}"]`);
  if (card) {
    card.querySelectorAll('.color-dot').forEach((d, i) => {
      d.classList.toggle('active', i === colorIdx);
    });
  }
}

// ===== MODAL =====
let currentModal = null;

function openModal(idx) {
  const p = PRODUCTS[idx];
  currentModal = idx;

  // Zoom-from-card animation
  const cardEl = document.querySelector(`[data-product="${idx}"]`);
  const modalEl = document.querySelector('#modal .modal');
  if (cardEl && modalEl) {
    const rect = cardEl.getBoundingClientRect();
    const cardCX = rect.left + rect.width / 2;
    const cardCY = rect.top + rect.height / 2;
    const fromX = cardCX - window.innerWidth / 2;
    const fromY = cardCY - window.innerHeight / 2;
    modalEl.style.setProperty('--from-x', `${fromX}px`);
    modalEl.style.setProperty('--from-y', `${fromY}px`);
    // Restart animation
    modalEl.style.animation = 'none';
    modalEl.offsetHeight; // force reflow
    modalEl.style.animation = '';
    // Brief card scale-up
    cardEl.classList.add('is-zooming');
    setTimeout(() => cardEl.classList.remove('is-zooming'), 250);
  }

  document.getElementById('modal-name').textContent = p.name;
  document.getElementById('modal-sub').textContent  = p.specs;
  const modalImg = document.getElementById('modal-img');
  modalImg.style.display = '';
  modalImg.src = p.colors[0].img;

  const d = p.details;
  const specItems = [
    d.screen     !== '—' ? `<div class="modal-spec"><div class="val">${d.screen}</div><div class="lbl">Écran</div></div>`       : '',
    d.ram        !== '—' ? `<div class="modal-spec"><div class="val">${d.ram}</div><div class="lbl">RAM</div></div>`            : '',
    d.storage    !== '—' ? `<div class="modal-spec"><div class="val">${d.storage}</div><div class="lbl">Stockage</div></div>`   : '',
    d.battery    !== '—' ? `<div class="modal-spec"><div class="val">${d.battery}</div><div class="lbl">Batterie</div></div>`   : '',
    d.camera     !== '—' ? `<div class="modal-spec"><div class="val">${d.camera}</div><div class="lbl">Caméra</div></div>`      : '',
    d.protection !== '—' ? `<div class="modal-spec"><div class="val">${d.protection}</div><div class="lbl">Protection</div></div>` : '',
  ];
  document.getElementById('modal-specs').innerHTML = specItems.join('');

  document.getElementById('modal-colors').innerHTML = p.colors.map((c, ci) => `
    <div class="modal-color-dot ${ci === 0 ? 'active' : ''}"
         style="background:${c.hex}" title="${c.name}"
         onclick="switchModalColor(${ci})">
    </div>
  `).join('');

  document.getElementById('modal-color-name').textContent = p.colors[0].name;

  const cart = document.getElementById('modal-cart');
  if (p.badge === 'soon') {
    cart.textContent   = '⏳ Bientôt disponible';
    cart.href          = '#';
    cart.style.opacity = '.5';
  } else {
    cart.textContent   = '🛒 Voir sur la boutique';
    cart.href          = BASE + p.colors[0].url;
    cart.style.opacity = '1';
  }

  document.getElementById('modal').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function switchModalColor(ci) {
  const p = PRODUCTS[currentModal];
  const c = p.colors[ci];

  const modalImg = document.getElementById('modal-img');
  modalImg.style.display = '';
  modalImg.src = c.img;
  document.getElementById('modal-color-name').textContent = c.name;
  if (p.badge !== 'soon') document.getElementById('modal-cart').href = BASE + c.url;

  document.querySelectorAll('.modal-color-dot').forEach((d, i) => {
    d.classList.toggle('active', i === ci);
  });
}

function closeModal() {
  document.getElementById('modal').classList.remove('open');
  document.body.style.overflow = '';
}

// ===== FILTER =====
function filterCategory(cat, btn) {
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');

  let firstVisible = null;
  document.querySelectorAll('.section').forEach(s => {
    const visible = cat === 'all' || s.dataset.cat === cat;
    s.style.display = visible ? '' : 'none';
    if (visible && !firstVisible) firstVisible = s;
  });

  document.querySelector('.nav-tabs').classList.remove('open');

  if (firstVisible) {
    const navHeight = document.querySelector('.nav').offsetHeight;
    const top = firstVisible.getBoundingClientRect().top + window.scrollY - navHeight - 16;
    window.scrollTo({ top, behavior: 'smooth' });
  }
}

// ===== SCROLL REVEAL =====
function initReveal() {
  const observer = new IntersectionObserver(
    entries => entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); }),
    { threshold: 0.05 }
  );
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
}

// ===== EVENTS =====
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

// ===== INIT =====
renderProducts();
initReveal();

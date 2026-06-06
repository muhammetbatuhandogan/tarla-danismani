/**
 * Tarla Danışmanı — WhatsApp UI + Backend Entegrasyonu
 */

const State = {
  il: null,
  urun: null,
  ekimAyi: null,
  kayitli: false,
  oneri: null,  // Son API'dan gelen öneri
};

// API base URL — backend ile aynı origin'den gelir
const API = '';

// ── Saat yardımcısı ─────────────────────────────────────────────────────────
function simdi() {
  const d = new Date();
  return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
}

// ── Ekran geçişi ────────────────────────────────────────────────────────────
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  const target = document.getElementById(id);
  if (target) {
    target.classList.add('active');
    const body = target.querySelector('.wa-body');
    if (body) body.scrollTop = body.scrollHeight;
  }
  updateHeader(id);
  updateProgress(id);
}

function updateHeader(screenId) {
  const statusEl = document.getElementById('wa-status');
  if (!statusEl) return;
  const msgScreens = ['screen-msg-sula','screen-msg-sulama','screen-msg-don','screen-msg-hastalik','screen-teknik-hata'];
  statusEl.textContent = msgScreens.includes(screenId) ? 'Pazartesi, 07:30' : 'Çevrimiçi';
}

const progressSteps = ['screen-welcome','screen-il','screen-urun','screen-ekim','screen-onay'];

function updateProgress(screenId) {
  const bar = document.getElementById('progress-bar');
  if (!bar) return;
  const idx = progressSteps.indexOf(screenId);
  if (idx === -1) { bar.style.display = 'none'; return; }
  bar.style.display = 'flex';
  bar.querySelectorAll('.progress-step').forEach((el, i) => {
    el.classList.remove('done', 'active');
    if (i < idx) el.classList.add('done');
    else if (i === idx) el.classList.add('active');
  });
  const label = bar.querySelector('.progress-label');
  if (label) label.textContent = `${idx + 1} / ${progressSteps.length}`;
}

// ── İl seçimi ───────────────────────────────────────────────────────────────
function selectIl(il) {
  State.il = il;
  if (il === 'diger') { showScreen('screen-diger-il'); return; }
  document.getElementById('urun-il-label').textContent = il + ' seçildi ✓';
  showScreen('screen-urun');
}

function submitDigerIl() {
  const val = document.getElementById('input-il').value.trim();
  if (!val) return;
  State.il = val;
  document.getElementById('urun-il-label').textContent = val + ' seçildi ✓';
  showScreen('screen-urun');
}

// ── Ürün seçimi ─────────────────────────────────────────────────────────────
const URUN_LABEL = {
  bugday: '🌾 Buğday', aycicek: '🌻 Ayçiçeği',
  pancar: '🍬 Şeker pancarı', misir: '🌽 Mısır',
};

function selectUrun(urun) {
  State.urun = urun;
  if (urun === 'diger') { showScreen('screen-diger-urun'); return; }
  document.getElementById('ekim-urun-label').textContent = URUN_LABEL[urun] || urun;
  showScreen('screen-ekim');
}

function submitDigerUrun() {
  const val = document.getElementById('input-urun').value.trim();
  if (!val) return;
  State.urun = val;
  document.getElementById('ekim-urun-label').textContent = val;
  showScreen('screen-diger-urun-uyari');
}

function digerUrunDevam() { showScreen('screen-ekim'); }

// ── Ekim ayı seçimi ─────────────────────────────────────────────────────────
function selectAy(ay) {
  State.ekimAyi = ay;
  if (ay === 'diger') { showScreen('screen-diger-ay'); return; }
  buildOnay();
  showScreen('screen-onay');
}

function submitDigerAy(ay) {
  State.ekimAyi = ay;
  buildOnay();
  showScreen('screen-onay');
}

// ── Onay ekranı ─────────────────────────────────────────────────────────────
function buildOnay() {
  const el = document.getElementById('onay-bilgiler');
  if (el) {
    el.innerHTML =
      `📍 ${State.il}<br>` +
      `${URUN_LABEL[State.urun] || State.urun}<br>` +
      `📅 ${State.ekimAyi} ayı ekimi`;
  }
  const bilgiEl = document.getElementById('guncelle-bilgi');
  if (bilgiEl) bilgiEl.innerHTML = el ? el.innerHTML : '';
  const geriEl = document.getElementById('geri-don-bilgi');
  if (geriEl) geriEl.textContent = `📍 ${State.il} — ${URUN_LABEL[State.urun] || State.urun}`;
  State.kayitli = true;
}

// ── Gerçek API önerisi ───────────────────────────────────────────────────────
async function goGercekOneri() {
  const il = State.il || 'Konya';
  const urun = State.urun || 'bugday';
  const ekimAyi = State.ekimAyi || 'Ekim';

  // Loading ekranı göster
  const body = document.getElementById('gercek-oneri-body');
  body.innerHTML = `
    <div class="chat-divider">Bugün — Gerçek Veri</div>
    <div class="loading-bubble">
      <div class="spinner"></div>
      <span>${il} için hava verisi alınıyor…</span>
    </div>
  `;
  showScreen('screen-gercek-oneri');

  try {
    const url = `${API}/api/simulate?il=${encodeURIComponent(il)}&urun=${encodeURIComponent(urun)}&ekim_ayi=${encodeURIComponent(ekimAyi)}`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    State.oneri = data;
    renderGercekOneri(data);
  } catch (err) {
    body.innerHTML = `
      <div class="chat-divider">Bugün</div>
      <div class="bubble incoming red">
        <span class="bubble-title red">⚙️ Veri alınamadı.</span>
        Bağlantı hatası: ${err.message}<br>
        Lütfen tekrar deneyin.
        <div class="bubble-time">${simdi()}</div>
      </div>
      <div class="bubble incoming" style="margin-top:8px">
        <button class="wa-btn primary" onclick="goGercekOneri()">Tekrar dene</button>
        <button class="wa-btn secondary" style="margin-top:6px" onclick="showScreen('screen-msg-sula')">Demo mesajları gör</button>
        <div class="bubble-time">${simdi()}</div>
      </div>
    `;
  }
}

function renderGercekOneri(data) {
  const body = document.getElementById('gercek-oneri-body');
  const renkSinif = {
    green: 'green', red: 'red', yellow: 'yellow', white: ''
  }[data.renk] || '';

  const tarih = new Date().toLocaleDateString('tr-TR', {
    weekday: 'long', day: 'numeric', month: 'long'
  });

  let ilaclaHtml = '';
  if (data.ilacla_not) {
    ilaclaHtml = `
      <div class="bubble incoming yellow" style="margin-top:4px">
        <span class="bubble-title yellow">💊 İlaçlama notu</span>
        ${data.ilacla_not.replace(/\n/g, '<br>')}
        <div class="bubble-time">${simdi()}</div>
      </div>
    `;
  }

  body.innerHTML = `
    <div class="chat-divider">${tarih} — Gerçek Veri</div>

    <div class="bubble incoming ${renkSinif}">
      <span class="bubble-title ${renkSinif}">${data.baslik}</span>
      ${data.detay.replace(/\n/g, '<br>')}
      <div class="bubble-time">${simdi()}</div>
    </div>

    <div class="bubble incoming" style="margin-top:4px">
      <span style="font-size:12px;color:#555;white-space:pre-line">${data.hava_ozeti}</span>
      <div class="bubble-time">${simdi()}</div>
    </div>

    <div class="bubble incoming" style="margin-top:4px">
      <span style="font-size:11px;color:#888">
        🌱 Büyüme evresi: ${data.buyume_evresi}<br>
        📊 GDD birikimi: ${data.gdd_birikmis}<br>
        📍 ${data.il} — ${data.urun_isim}
      </span>
      <div class="bubble-time">${simdi()}</div>
    </div>

    ${ilaclaHtml}

    <div class="bubble incoming" style="margin-top:8px">
      <button class="wa-btn outline" onclick="goGercekOneri()">🔄 Yenile</button>
      <button class="wa-btn secondary" style="margin-top:6px" onclick="tesekkurEt()">Teşekkürler →</button>
      <button class="wa-btn secondary" style="margin-top:6px" onclick="showScreen('screen-msg-sula')">Demo mesajları gör</button>
      <div class="bubble-time">${simdi()}</div>
    </div>
  `;
}

// ── Mesaj akışları (statik demo) ─────────────────────────────────────────────
function goMesajlar() { showScreen('screen-msg-sula'); }
function tesekkurEt() { showScreen('screen-tesekkur'); }
function anlamsizMesaj() { showScreen('screen-anlamsiz'); }

function menuSecim(secim) {
  const map = { guncelle: 'screen-guncelle', nasil: 'screen-nasil', durdur: 'screen-durdur-onay' };
  if (map[secim]) showScreen(map[secim]);
}

function guncelleSecim(alan) {
  const map = { il: 'screen-il', urun: 'screen-urun', ekim: 'screen-ekim' };
  if (map[alan]) { State[alan] = null; showScreen(map[alan]); }
}

function durdurOnay(karar) {
  if (karar === 'evet') { State.kayitli = false; showScreen('screen-durdur-tamam'); }
  else showScreen('screen-msg-sula');
}

function geriDonDevam(devam) {
  showScreen(devam ? 'screen-msg-sula' : 'screen-guncelle');
}

// ── Demo navigasyon ─────────────────────────────────────────────────────────
function demoGo(screen) { showScreen(screen); }

// ── Enter tuşu ──────────────────────────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter') return;
  const active = document.querySelector('.screen.active');
  if (!active) return;
  if (active.id === 'screen-diger-il')   submitDigerIl();
  if (active.id === 'screen-diger-urun') submitDigerUrun();
});

// ── Başlangıç ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  showScreen('screen-welcome');
});

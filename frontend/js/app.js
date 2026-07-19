/* ── App — Main Application Logic ────────────────────────────────── */
/* getbased-style Single Page Application                             */

const App = {
  /* ── Initialization ──────────────────────────────────────────── */
  async init() {
    this._bindNavigation();
    this._bindGlobalEvents();
    await this._checkStatus();
    this._renderPage('dashboard');
  },

  /* ── Navigation ──────────────────────────────────────────────── */
  _bindNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', () => {
        const page = item.dataset.page;
        this._renderPage(page);
      });
    });
  },

  _renderPage(page) {
    State.set('currentPage', page);
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const navItem = document.querySelector(`.nav-item[data-page="${page}"]`);
    if (navItem) navItem.classList.add('active');

    const titles = {
      dashboard: 'Übersicht',
      dna: '🧬 DNA-Analyse',
      blood: '🩸 Blutwerte',
      medications: '💊 Medikamente',
      genome: '🧬 Genomen',
      supplements: '💊 Supplement-Empfehlungen',
      tolerance: '💉 Verträglichkeit',
      export: '📄 Report-Export',
    };

    document.getElementById('page-title').textContent = titles[page] || page;

    switch (page) {
      case 'dashboard': this._renderDashboard(); break;
      case 'dna': this._renderDnaPage(); break;
      case 'blood': this._renderBloodPage(); break;
      case 'medications': this._renderMedicationsInputPage(); break;
      case 'genome': this._renderProfilePage(); break;
      case 'supplements': this._renderSupplementsPage(); break;
      case 'tolerance': this._renderTolerancePage(); break;
      case 'export': this._renderExportPage(); break;
    }
  },

  /* ── Server Status ───────────────────────────────────────────── */
  async _checkStatus() {
    try {
      const status = await API.status();
      State.set('serverStatus', status);
      const dot = document.getElementById('status-dot');
      const text = document.getElementById('status-text');
      dot.className = 'status-dot';
      text.textContent = `${status.panel_size} SNPs · verbunden`;
    } catch {
      document.getElementById('status-dot').className = 'status-dot offline';
      document.getElementById('status-text').textContent = 'Server offline';
    }
  },

  /* ── Global Event Bindings ───────────────────────────────────── */
  _bindGlobalEvents() {
    // Start analyze button on welcome screen
    document.getElementById('btn-start-analyze')?.addEventListener('click', () => {
      this._renderPage('dna');
    });
  },

  /* ================================================================
     PAGE: DASHBOARD
     ================================================================ */
  _renderDashboard() {
    const body = document.getElementById('main-body');
    const results = State.get('results');

    if (!results) {
      body.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🧬</div>
          <div class="empty-state-title">Willkommen bei Herrmann Nutrigenomik</div>
          <div class="empty-state-text">
            Laden Sie Ihre DNA-Rohdaten hoch und starten Sie die Analyse,
            um personalisierte Supplement-Empfehlungen zu erhalten.
          </div>
          <button class="btn btn-primary" onclick="App._renderPage('dna')">
            🧬 Zur DNA-Analyse
          </button>
        </div>
      `;
      return;
    }

    const rp = results.risk_profile?.category_scores || {};
    const ms = results.methylation_score || {};
    const sp = results.supplement_plan || [];
    const br = results.blood_results || [];

    const highCats = Object.values(rp).filter(v => v.category === 'Erhöht').length;
    const highSupps = sp.filter(s => s.risk_level === 'hoch').length;
    const suboptimalBlood = br.filter(b => b.status !== 'optimal').length;

    body.innerHTML = `
      <div class="grid-5">
        <div class="metric-card">
          <div class="metric-value">${ms.score != null ? ms.score + '/10' : '—'}</div>
          <div class="metric-label">🧬 Methylierung</div>
          <div class="metric-delta ${this._scoreClass(ms.score || 0)}">${ms.level || ''}</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">${results.snp_found || 0}/${results.snp_total || 0}</div>
          <div class="metric-label">🎯 SNPs analysiert</div>
        </div>
        <div class="metric-card">
          <div class="metric-value ${this._scoreClass(highCats * 3.3)}">${highCats}</div>
          <div class="metric-label">🔴 Erhöhte Risiken</div>
        </div>
        <div class="metric-card">
          <div class="metric-value ${this._scoreClass(highSupps * 3.3)}">${highSupps}</div>
          <div class="metric-label">💊 Supplemente (hoch)</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">${br.length > 0 ? suboptimalBlood : '—'}</div>
          <div class="metric-label">🩸 Blutwerte suboptimal</div>
        </div>
      </div>

      <hr class="section-divider">

      <div class="card">
        <div class="flex justify-between items-center mb-3">
          <span class="card-title" style="margin-bottom:0">🧬 Executive Summary</span>
        </div>
        ${results.risk_profile?.executive_summary?.length > 0
          ? `<ul style="list-style:none;padding:0">
              ${results.risk_profile.executive_summary.map(s =>
                `<li style="padding:4px 0;font-size:13px;color:var(--text-secondary)">${s}</li>`
              ).join('')}
            </ul>`
          : '<div class="text-xs" style="color:var(--text-muted)">Keine Executive Summary verfügbar</div>'
        }
      </div>

      <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn" onclick="App._renderPage('genome')">🧬 Genomen anzeigen</button>
        <button class="btn btn-primary" onclick="App._renderPage('supplements')">💊 Supplement-Plan</button>
        <button class="btn" onclick="App._renderPage('tolerance')">💉 Verträglichkeit</button>
      </div>
    `;
  },

  /* ================================================================
     PAGE: DNA ANALYSIS
     ================================================================ */
  _renderDnaPage() {
    const body = document.getElementById('main-body');
    const dnaLoaded = State.get('dnaLoaded');
    const results = State.get('results');

    body.innerHTML = `
      <div class="card">
        <div class="card-title">DNA-Rohdaten hochladen</div>
        <div class="card-subtitle">Unterstützt 23andMe (.txt), AncestryDNA (.csv) und VCF (.vcf/.vcf.gz)</div>

        <div class="file-upload" id="dna-dropzone">
          <div class="file-upload-icon">🧬</div>
          <div class="file-upload-text">DNA-Datei hier ablegen oder klicken zum Auswählen</div>
          <div class="file-upload-subtext">23andMe, AncestryDNA, VCF — bis zu 50 MB</div>
          <input type="file" id="dna-file-input" accept=".txt,.csv,.vcf,.gz" style="display:none">
        </div>
      </div>

      <div id="dna-status"></div>

      <div id="dna-profile-form"></div>

      <div id="dna-results"></div>
    `;

    this._bindDnaUpload();

    if (dnaLoaded && results) {
      this._renderDnaStatus(results);
      this._renderProfileForm();
      this._renderDnaResults(results);
    } else if (dnaLoaded) {
      this._renderProfileForm();
    }
  },

  _bindDnaUpload() {
    const dropzone = document.getElementById('dna-dropzone');
    const input = document.getElementById('dna-file-input');

    dropzone.addEventListener('click', () => input.click());
    dropzone.addEventListener('dragover', e => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', e => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files.length > 0) {
        this._handleDnaFile(e.dataTransfer.files[0]);
      }
    });
    input.addEventListener('change', () => {
      if (input.files.length > 0) {
        this._handleDnaFile(input.files[0]);
      }
    });
  },

  async _handleDnaFile(file) {
    const statusDiv = document.getElementById('dna-status');
    statusDiv.innerHTML = '<div class="alert alert-info">📄 Lade DNA-Datei...</div>';

    try {
      const formData = new FormData();
      formData.append('dna', file);

      // Quick parse status check via a lightweight approach
      const profile = State.get('profile');
      formData.append('profile', JSON.stringify(profile));

      statusDiv.innerHTML = '<div class="loading-overlay"><div class="spinner"></div><div class="loading-text">Analysiere DNA...</div></div><div class="progress-bar"><div class="progress-fill" id="progress-fill" style="width:0%"></div></div>';

      const results = await API.analyze(formData, (msg, pct) => {
        const fill = document.getElementById('progress-fill');
        if (fill) fill.style.width = pct + '%';
      });

      State.set('results', results);
      State.set('dnaLoaded', true);
      State.set('analysisDone', true);

      statusDiv.innerHTML = `<div class="alert alert-success">✅ ${file.name} — ${results.format}, ${results.genotype_count?.toLocaleString()} SNPs, ${results.snp_found}/${results.snp_total} Panel-SNPs gefunden</div>`;

      this._renderProfileForm();
      this._renderDnaResults(results);

    } catch (err) {
      statusDiv.innerHTML = `<div class="alert alert-error">❌ ${err.message}</div>`;
    }
  },

  _renderDnaStatus(results) {
    const statusDiv = document.getElementById('dna-status');
    if (!statusDiv) return;
    statusDiv.innerHTML = `
      <div class="alert alert-success">
        ✅ ${results.dna_file || 'DNA-Datei'} — ${results.format}, ${results.genotype_count?.toLocaleString()} SNPs,
        ${results.snp_found}/${results.snp_total} Panel-SNPs gefunden
      </div>
    `;
  },

  _renderProfileForm() {
    const div = document.getElementById('dna-profile-form');
    if (!div) return;
    const p = State.get('profile');

    div.innerHTML = `
      <div class="card">
        <div class="card-title">📋 Nächste Schritte</div>
        <div class="card-subtitle">Ergänzen Sie optionale Daten für präzisere Empfehlungen</div>
        <div style="display:flex;gap:10px;flex-wrap:wrap">
          <button class="btn" onclick="App._renderPage('blood')" style="flex:1;justify-content:center">
            🩸 Blutwerte eingeben
          </button>
          <button class="btn" onclick="App._renderPage('medications')" style="flex:1;justify-content:center">
            💊 Medikamente verwalten
          </button>
        </div>
        <div class="text-xs mt-2" style="color:var(--text-muted);text-align:center">
          Daten jederzeit nachträglich ergänzbar · Supplemente werden automatisch neu berechnet
        </div>
        <hr class="section-divider">
        <button class="btn btn-primary" id="btn-reanalyze" style="width:100%">🔄 Analyse aktualisieren</button>
      </div>
    `;

    // Re-analyze
    document.getElementById('btn-reanalyze').addEventListener('click', () => this._reanalyze());
  },

  async _drugSearch() {
    const input = document.getElementById('drug-search-input');
    const q = input.value.trim();
    if (!q) return;

    try {
      const data = await API.drugSearch(q);
      const resultsDiv = document.getElementById('drug-search-results');
      if (data.results?.length > 0) {
        resultsDiv.innerHTML = `
          <div class="drug-tags">
            ${data.results.map(d =>
              `<span class="drug-tag" onclick="App._addDrug('${d.replace(/'/g, "\\'")}')">+ ${d}</span>`
            ).join('')}
          </div>
        `;
      } else {
        resultsDiv.innerHTML = '<div class="text-xs" style="color:var(--text-muted)">Keine Treffer</div>';
      }
    } catch {
      // ignore
    }
  },

  _addDrug(name) {
    const p = State.get('profile');
    if (!p.drugs.includes(name)) {
      p.drugs.push(name);
      State.set('profile', p);
    }
    this._renderDrugTags();
    document.getElementById('drug-search-results').innerHTML = '';
    document.getElementById('drug-search-input').value = '';
  },

  _removeDrug(name) {
    const p = State.get('profile');
    p.drugs = p.drugs.filter(d => d !== name);
    State.set('profile', p);
    this._renderDrugTags();
  },

  _renderDrugTags() {
    const div = document.getElementById('drug-tags');
    if (!div) return;
    const drugs = State.get('profile').drugs || [];
    if (drugs.length === 0) {
      div.innerHTML = '<div class="text-xs" style="color:var(--text-muted)">Keine Medikamente ausgewählt</div>';
      return;
    }
    div.innerHTML = `
      <div class="drug-tags">
        ${drugs.map(d =>
          `<span class="drug-tag selected">
            ${d}
            <span class="drug-tag-remove" onclick="App._removeDrug('${d.replace(/'/g, "\\'")}')">×</span>
          </span>`
        ).join('')}
      </div>
    `;
  },

  async _reanalyze() {
    const statusDiv = document.getElementById('dna-status');
    const results = State.get('results');
    if (!results) return;

    const p = State.get('profile');
    const formData = new FormData();
    formData.append('profile', JSON.stringify(p));

    statusDiv.innerHTML = '<div class="loading-overlay"><div class="spinner"></div><div class="loading-text">Analysiere mit aktualisierten Daten...</div></div><div class="progress-bar"><div class="progress-fill" style="width:0%" id="progress-fill2"></div></div>';

    try {
      const newResults = await API.analyze(formData, (msg, pct) => {
        const fill = document.getElementById('progress-fill2');
        if (fill) fill.style.width = pct + '%';
      });
      State.set('results', newResults);
      this._renderDnaStatus(newResults);
      this._renderDnaResults(newResults);
      statusDiv.innerHTML += '<div class="alert alert-success">✅ Analyse aktualisiert</div>';
    } catch (err) {
      statusDiv.innerHTML = `<div class="alert alert-error">❌ ${err.message}</div>`;
    }
  },

  _renderDnaResults(results) {
    const div = document.getElementById('dna-results');
    if (!div) return;

    const rp = results.risk_profile?.category_scores || {};
    const sp = results.supplement_plan || [];
    const drugWarnings = results.drug_warnings || [];

    const topCategories = Object.entries(rp)
      .sort((a, b) => (b[1]?.score || 0) - (a[1]?.score || 0))
      .slice(0, 5);

    div.innerHTML = `
      <hr class="section-divider">
      <div class="card">
        <div class="card-title">📋 Analyse-Ergebnisse</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
          <div>
            <div class="text-sm mb-2" style="color:var(--text-secondary);font-weight:600">Top-Kategorien</div>
            ${topCategories.map(([cat, data]) => `
              <div class="flex justify-between items-center" style="padding:4px 0">
                <span style="font-size:13px">${cat}</span>
                <span class="badge ${data.category === 'Erhöht' ? 'badge-high' : data.category === 'Moderat' ? 'badge-moderate' : 'badge-low'}">
                  ${data.score != null ? data.score.toFixed(1) : '—'}/10 · ${data.category || '?'}
                </span>
              </div>
            `).join('')}
          </div>
          <div>
            <div class="text-sm mb-2" style="color:var(--text-secondary);font-weight:600">Top-Supplemente</div>
            ${sp.slice(0, 5).map(s => `
              <div class="flex justify-between items-center" style="padding:4px 0">
                <span style="font-size:13px">${s.name || s.id}</span>
                <span style="font-size:13px;color:var(--accent);font-weight:600">
                  ${s.final_dose_mg || s.dose_mg || 0} mg
                </span>
              </div>
            `).join('')}
            ${drugWarnings.length > 0 ? `
              <div class="text-sm mt-2" style="color:var(--yellow);font-weight:600">
                ⚠️ ${drugWarnings.length} Medikamenten-Warnung(en)
              </div>
            ` : ''}
          </div>
        </div>
      </div>

      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-primary" onclick="App._renderPage('genome')">🧬 Genomen anzeigen</button>
        <button class="btn" onclick="App._renderPage('supplements')">💊 Supplement-Plan</button>
      </div>
    `;
  },

  /* ================================================================
     PAGE: BLOOD VALUES
     ================================================================ */
  _renderBloodPage() {
    const body = document.getElementById('main-body');
    const results = State.get('results');

    // Known biomarkers for autocomplete
    const knownBiomarkers = [
      'Homocystein', 'Vitamin D (25-OH)', 'Vitamin B12', 'Ferritin',
      'CRP', 'hs-CRP', 'Magnesium', 'Omega-3-Index', 'Zink', 'Selen',
      'Glucose', 'HbA1c', 'TSH', 'Cortisol', 'LDL-Cholesterin',
      'HDL-Cholesterin', 'Gesamt-Cholesterin', 'Triglyceride',
      'Kreatinin', 'GFR', 'GPT (ALT)', 'GOT (AST)', 'Gamma-GT',
      'Eisen', 'Transferrin-Sättigung', 'Harnstoff', 'Harnsäure',
      'Calcium', 'Natrium', 'Kalium', 'Leukozyten', 'Hämoglobin',
      'Thrombozyten', 'Vitamin B6', 'CoQ10',
    ];

    body.innerHTML = `
      <div class="card">
        <div class="card-title">🩸 Blutwerte hochladen</div>
        <div class="card-subtitle">CSV oder Excel mit Biomarker, Wert, Einheit</div>
        <div class="file-upload" id="blood-dropzone">
          <div class="file-upload-icon">🩸</div>
          <div class="file-upload-text">Blutwert-Datei hier ablegen oder klicken</div>
          <div class="file-upload-subtext">CSV (.csv) oder Excel (.xlsx)</div>
          <input type="file" id="blood-file-input" accept=".csv,.xlsx" style="display:none">
        </div>
        <div id="blood-upload-status" style="margin-top:12px"></div>
      </div>

      <div class="card">
        <div class="card-title">✏️ Manuelle Eingabe</div>
        <div class="card-subtitle">Einzelne Blutwerte direkt eintragen</div>
        <div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:8px;align-items:end">
          <div class="form-group">
            <label class="form-label">Biomarker</label>
            <input type="text" class="form-input" id="manual-biomarker" list="biomarker-list" placeholder="z.B. Vitamin D">
            <datalist id="biomarker-list">
              ${knownBiomarkers.map(b => `<option value="${b}">`).join('')}
            </datalist>
          </div>
          <div class="form-group">
            <label class="form-label">Wert</label>
            <input type="number" class="form-input" id="manual-value" step="any" placeholder="z.B. 42.5">
          </div>
          <div class="form-group">
            <label class="form-label">Einheit</label>
            <input type="text" class="form-input" id="manual-unit" placeholder="z.B. ng/ml">
          </div>
          <div class="form-group">
            <label class="form-label">&nbsp;</label>
            <button class="btn btn-primary" id="btn-add-blood" style="width:100%">+ Hinzufügen</button>
          </div>
        </div>
        <div id="manual-blood-list" style="margin-top:8px"></div>
        <div id="manual-blood-actions" style="margin-top:8px;display:none">
          <button class="btn btn-primary" id="btn-save-blood">💾 Speichern & Analysieren</button>
          <button class="btn btn-sm" id="btn-clear-blood">Alle löschen</button>
        </div>
        <div class="text-xs mt-3" style="color:var(--text-muted);line-height:1.5">
          ℹ️ Die eingegeben Blutwerte werden gespeichert und fließen in die Supplement-Dosierung ein.
          Sie dienen der persönlichen Aufklärung und ersetzen keine ärztliche Diagnose.
        </div>
      </div>

      <div id="blood-manual-status"></div>
      <div id="blood-results"></div>
      <div id="blood-history-section"></div>
    `;

    // File upload bindings
    const dropzone = document.getElementById('blood-dropzone');
    const input = document.getElementById('blood-file-input');

    dropzone.addEventListener('click', () => input.click());
    dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('dragover'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
    dropzone.addEventListener('drop', e => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files.length > 0) this._handleBloodFile(e.dataTransfer.files[0]);
    });
    input.addEventListener('change', () => {
      if (input.files.length > 0) this._handleBloodFile(input.files[0]);
    });

    // Manual input bindings
    document.getElementById('btn-add-blood').addEventListener('click', () => this._addManualBlood());
    document.getElementById('manual-value').addEventListener('keydown', e => {
      if (e.key === 'Enter') this._addManualBlood();
    });
    document.getElementById('manual-biomarker').addEventListener('change', () => this._autoFillUnit());
    document.getElementById('manual-biomarker').addEventListener('input', () => this._autoFillUnit());

    const btnSave = document.getElementById('btn-save-blood');
    if (btnSave) btnSave.addEventListener('click', () => this._saveManualBlood());
    const btnClear = document.getElementById('btn-clear-blood');
    if (btnClear) btnClear.addEventListener('click', () => this._clearManualBlood());

    // Init manual blood list
    State.set('manualBloodList', []);
    this._renderManualBloodList();

    // Show existing blood results
    if (results?.blood_results?.length > 0) {
      this._renderBloodResults(results.blood_results);
    }

    // Show blood history
    this._renderBloodHistory();
  },

  _autoFillUnit() {
    const nameEl = document.getElementById('manual-biomarker');
    const unitEl = document.getElementById('manual-unit');
    const name = nameEl?.value?.trim().toLowerCase();
    if (!name || !unitEl) return;

    const unitMap = {
      'homocystein': 'µmol/l',
      'vitamin d': 'ng/ml',
      'vitamin b12': 'pg/ml',
      'ferritin': 'ng/ml',
      'crp': 'mg/l',
      'hs-crp': 'mg/l',
      'magnesium': 'mmol/l',
      'omega-3-index': '%',
      'zink': 'µg/l',
      'selen': 'µg/l',
      'glucose': 'mg/dl',
      'hba1c': '%',
      'tsh': 'mU/l',
      'cortisol': 'µg/dl',
      'ldl-cholesterin': 'mg/dl',
      'hdl-cholesterin': 'mg/dl',
      'gesamt-cholesterin': 'mg/dl',
      'triglyceride': 'mg/dl',
      'kreatinin': 'mg/dl',
      'gfr': 'ml/min',
      'gpt': 'U/l',
      'got': 'U/l',
      'gamma-gt': 'U/l',
      'eisen': 'µg/dl',
      'transferrin-sättigung': '%',
      'harnstoff': 'mg/dl',
      'harnsäure': 'mg/dl',
      'calcium': 'mmol/l',
      'natrium': 'mmol/l',
      'kalium': 'mmol/l',
      'leukozyten': 'G/l',
      'hämoglobin': 'g/dl',
      'thrombozyten': 'G/l',
      'coq10': 'mg/l',
    };

    for (const [key, unit] of Object.entries(unitMap)) {
      if (name.includes(key)) {
        unitEl.value = unit;
        break;
      }
    }
  },

  _addManualBlood() {
    const nameEl = document.getElementById('manual-biomarker');
    const valueEl = document.getElementById('manual-value');
    const unitEl = document.getElementById('manual-unit');

    const name = nameEl?.value?.trim();
    const value = parseFloat(valueEl?.value);
    const unit = unitEl?.value?.trim() || '';

    if (!name) {
      this._showManualStatus('Bitte Biomarker eingeben', 'error');
      return;
    }
    if (isNaN(value)) {
      this._showManualStatus('Bitte gültigen Wert eingeben', 'error');
      return;
    }

    const list = State.get('manualBloodList') || [];
    // Check duplicate
    const existing = list.find(i => i.name.toLowerCase() === name.toLowerCase());
    if (existing) {
      existing.value = value;
      existing.unit = unit;
    } else {
      list.push({ name, value, unit });
    }
    State.set('manualBloodList', list);

    // Clear inputs
    nameEl.value = '';
    valueEl.value = '';
    unitEl.value = '';
    nameEl.focus();

    this._renderManualBloodList();
    this._showManualStatus(`✅ ${name}: ${value} ${unit} hinzugefügt`, 'success');
  },

  _renderManualBloodList() {
    const div = document.getElementById('manual-blood-list');
    const actionsDiv = document.getElementById('manual-blood-actions');
    const list = State.get('manualBloodList') || [];

    if (!div) return;

    if (list.length === 0) {
      div.innerHTML = '<div class="text-xs" style="color:var(--text-muted)">Noch keine Werte eingegeben</div>';
      if (actionsDiv) actionsDiv.style.display = 'none';
      return;
    }

    if (actionsDiv) actionsDiv.style.display = 'block';

    div.innerHTML = `
      <div class="text-sm mb-2" style="color:var(--text-secondary);font-weight:600">Ausstehende Werte (${list.length})</div>
      <table class="score-table">
        <thead><tr><th>Biomarker</th><th>Wert</th><th>Einheit</th><th></th></tr></thead>
        <tbody>
          ${list.map((item, i) => `
            <tr>
              <td style="font-weight:500">${item.name}</td>
              <td>${item.value}</td>
              <td>${item.unit}</td>
              <td><span class="drug-tag-remove" onclick="App._removeManualBlood(${i})" style="cursor:pointer">×</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  },

  _removeManualBlood(index) {
    const list = State.get('manualBloodList') || [];
    list.splice(index, 1);
    State.set('manualBloodList', list);
    this._renderManualBloodList();
  },

  _clearManualBlood() {
    State.set('manualBloodList', []);
    this._renderManualBloodList();
    this._showManualStatus('Eingaben gelöscht', 'info');
  },

  async _saveManualBlood() {
    const list = State.get('manualBloodList') || [];
    if (list.length === 0) {
      this._showManualStatus('Keine Werte zum Speichern', 'error');
      return;
    }

    // Convert to values dict for API
    const values = {};
    list.forEach(item => {
      values[item.name.toLowerCase()] = {
        value: item.value,
        unit: item.unit,
      };
    });

    try {
      await API.bloodSnapshot(values);
      this._showManualStatus(`✅ ${list.length} Blutwert(e) gespeichert. Analysiere neu...`, 'success');
      State.set('manualBloodList', []);

      // Re-analyze if DNA results exist
      const results = State.get('results');
      if (results) {
        const p = State.get('profile');
        const formData = new FormData();
        const bloodBlob = new Blob(
          ['Biomarker,Wert,Einheit\n' + list.map(i => `${i.name},${i.value},${i.unit}`).join('\n')],
          { type: 'text/csv' }
        );
        formData.append('blood', bloodBlob, 'manual.csv');
        formData.append('profile', JSON.stringify(p));

        const newResults = await API.analyze(formData);
        State.set('results', newResults);
        this._renderBloodResults(newResults.blood_results || []);
        this._renderBloodHistory();
      }

      this._renderManualBloodList();
    } catch (err) {
      this._showManualStatus(`❌ Fehler: ${err.message}`, 'error');
    }
  },

  _showManualStatus(msg, type) {
    const div = document.getElementById('blood-manual-status');
    if (!div) return;
    div.innerHTML = `<div class="alert alert-${type}">${msg}</div>`;
    setTimeout(() => { if (div) div.innerHTML = ''; }, 3000);
  },

  async _handleBloodFile(file) {
    const statusDiv = document.getElementById('blood-upload-status');
    statusDiv.innerHTML = '<div class="alert alert-info">📄 Lade Blutwerte...</div>';

    try {
      const formData = new FormData();
      formData.append('blood', file);
      const result = await API.bloodUpload(formData);

      statusDiv.innerHTML = `<div class="alert alert-success">✅ ${result.count} Biomarker geladen</div>`;

      // Re-analyze with blood values
      const results = State.get('results');
      if (results) {
        const p = State.get('profile');
        const dnaFormData = new FormData();
        dnaFormData.append('blood', file);
        dnaFormData.append('profile', JSON.stringify(p));

        statusDiv.innerHTML += '<div class="alert alert-info">🔄 Analysiere mit Blutwerten neu...</div>';
        const newResults = await API.analyze(dnaFormData);
        State.set('results', newResults);
        this._renderBloodResults(newResults.blood_results || []);
        this._renderBloodHistory();
      }
    } catch (err) {
      statusDiv.innerHTML = `<div class="alert alert-error">❌ ${err.message}</div>`;
    }
  },

  _renderBloodResults(bloodResults) {
    const div = document.getElementById('blood-results');
    if (!div || bloodResults.length === 0) {
      if (div) div.innerHTML = '';
      return;
    }

    div.innerHTML = `
      <div class="card">
        <div class="card-title">Aktuelle Blutwerte</div>
        <table class="score-table">
          <thead><tr>
            <th>Biomarker</th>
            <th>Wert</th>
            <th>Status</th>
            <th>Bewertung</th>
          </tr></thead>
          <tbody>
            ${bloodResults.map(b => `
              <tr>
                <td style="font-weight:500">${b.name}</td>
                <td>${b.value} ${b.unit}</td>
                <td><span class="badge ${b.status === 'optimal' ? 'badge-low' : b.status === 'grenzwertig' ? 'badge-moderate' : 'badge-high'}">${b.status || 'unbekannt'}</span></td>
                <td style="font-size:12px;color:var(--text-secondary)">${b.description || b.bewertung || ''}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        <div class="text-xs mt-2" style="color:var(--text-muted)">
          Blutwerte fließen in die Supplement-Dosierung ein
        </div>
      </div>
    `;
  },

  async _renderBloodHistory() {
    const div = document.getElementById('blood-history-section');
    if (!div) return;

    try {
      const data = await API.bloodHistory();
      const history = data.history || [];

      if (history.length === 0) {
        div.innerHTML = `
          <div class="card">
            <div class="card-title">📈 Blutwert-Verlauf</div>
            <div class="text-xs" style="color:var(--text-muted)">Noch keine Historie vorhanden</div>
          </div>
        `;
        return;
      }

      // Collect unique biomarkers
      const biomarkers = new Set();
      history.forEach(h => {
        if (h.values) Object.keys(h.values).forEach(k => biomarkers.add(k));
      });

      div.innerHTML = `
        <div class="card">
          <div class="flex justify-between items-center mb-3">
            <span class="card-title" style="margin-bottom:0">📈 Blutwert-Verlauf (${history.length} Messungen)</span>
            <button class="btn btn-sm btn-danger" onclick="App._clearBloodHistory()">Historie löschen</button>
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px" id="biomarker-pills">
            ${Array.from(biomarkers).map(b =>
              `<span class="drug-tag" onclick="App._showBiomarkerTrend('${b.replace(/'/g, "\\'")}')">📈 ${b}</span>`
            ).join('')}
          </div>
          <div id="biomarker-chart"></div>
          <div id="biomarker-table"></div>
        </div>
      `;

      // Show latest measurements
      const latest = history[0]?.values || {};
      const tableDiv = document.getElementById('biomarker-table');
      if (Object.keys(latest).length > 0) {
        tableDiv.innerHTML = `
          <div class="text-sm mb-2" style="color:var(--text-secondary);font-weight:600">Letzte Messung (${history[0].date || '?'})</div>
          <table class="score-table">
            <thead><tr><th>Biomarker</th><th>Wert</th><th>Einheit</th></tr></thead>
            <tbody>
              ${Object.entries(latest).map(([name, data]) =>
                `<tr><td style="font-weight:500">${name}</td><td>${data.value}</td><td>${data.unit || ''}</td></tr>`
              ).join('')}
            </tbody>
          </table>
        `;
      }

    } catch {
      // ignore
    }
  },

  async _showBiomarkerTrend(biomarker) {
    try {
      const data = await API.bloodHistory(biomarker);
      const history = data.history || [];
      const chartDiv = document.getElementById('biomarker-chart');
      if (chartDiv) {
        Charts.renderBloodTrend('biomarker-chart', history, biomarker);
      }
    } catch {
      // ignore
    }
  },

  async _clearBloodHistory() {
    if (!confirm('Blutwert-Historie wirklich löschen?')) return;
    try {
      await API.bloodClear();
      this._renderBloodHistory();
    } catch {
      // ignore
    }
  },

  /* ================================================================
     PAGE: RISK PROFILE
     ================================================================ */
  _renderProfilePage() {
    const body = document.getElementById('main-body');
    const results = State.get('results');

    if (!results) {
      body.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📈</div>
          <div class="empty-state-title">Keine Analyse vorhanden</div>
          <div class="empty-state-text">Führen Sie zuerst eine DNA-Analyse durch.</div>
          <button class="btn btn-primary" onclick="App._renderPage('dna')">🧬 Zur DNA-Analyse</button>
        </div>
      `;
      return;
    }

    const rp = results.risk_profile?.category_scores || {};
    const ms = results.methylation_score || {};
    const standardScores = results.standard_category_scores || {};
    const expertScores = results.expert_category_scores || {};
    const hasExpert = Object.keys(expertScores).length > 0;

    const categoryExplanations = {
      methylierung: 'MTHFR, COMT, MTR, BHMT — Folat-, B12- und Methylgruppen-Stoffwechsel',
      fettstoffwechsel: 'FADS1/2, APOE, APOA5 — Omega-3, LDL, HDL, Triglyceride',
      vitamin_stoffwechsel: 'VDR, GC, BCMO1 — Vitamin D, A, C, B6, B12',
      entgiftung: 'CYP1A2, SOD2, GPX1, GSTP1 — Phase-1/2-Entgiftung, Antioxidantien',
      entzuendung: 'TNF-a, IL6, CRP, CTLA4 — Zytokine, Immunregulation',
      stoffwechsel: 'FTO, TCF7L2, ADRB2/3 — Kohlenhydrate, Energie, Gewicht',
      sensitivitaet: 'LCT, HLA-DQ — Laktose, Gluten, Nahrungsmittel-Unvertrglichkeiten',
      hormone: 'CYP19A1, SHBG, ESR1/2 — Hormonhaushalt, OEstrogen-Stoffwechsel',
      knochen_gelenke: 'VDR, GC, COL1A1 — Knochendichte, Kollagen, Vitamin-D-Wirkung',
      herz_kreislauf: 'ACE, NOS3, PON1, F2 — Blutdruck, Gerinnung, Gefaessfunktion',
      sport_genetik: 'ACTN3, PPARGC1A, AMPD1 — Muskelfasertyp, Ausdauer, ATP-Regeneration',
    };

    const plainLang = {
      methylierung: 'Ihr Methylierungs-Stoffwechsel ist wie eine Fabrik, die Schalter in Ihren Genen umlegt und wichtige Botenstoffe herstellt.',
      fettstoffwechsel: 'Ihr Fettstoffwechsel bestimmt, wie gut Ihr Körper Omega-3-Fettsäuren umwandeln und Cholesterin transportieren kann.',
      vitamin_stoffwechsel: 'Ihre Vitamin-Verwertung zeigt, wie effizient Ihr Körper Vitamine aus der Nahrung aufnimmt.',
      entgiftung: 'Ihre Entgiftungsenzyme sind die Müllabfuhr Ihres Körpers.',
      entzuendung: 'Entzündungs-Gene steuern, wie stark Ihr Körper auf Reize reagiert.',
      stoffwechsel: 'Ihr Stoffwechsel-Typ zeigt, wie Ihr Körper mit Kohlenhydraten und Energie umgeht.',
      sensitivitaet: 'Hier sehen Sie genetische Unverträglichkeiten für Laktose oder Gluten.',
      hormone: 'Ihre Hormon-Gene beeinflussen, wie Ihr Körper Sexual- und Stresshormone verarbeitet.',
      knochen_gelenke: 'Ihre Knochen- und Gelenk-Gene bestimmen Knochendichte und Bindegewebs-Reparatur.',
      herz_kreislauf: 'Ihre Herz-Kreislauf-Gene beeinflussen Blutdruck, Gefäßelastizität und Gerinnung.',
      sport_genetik: 'Ihre Sport-Gene verraten, ob Sie eher Kraft- oder Ausdauertyp sind.',
    };

    body.innerHTML = `
      <div class="card">
        <div class="card-title">🧬 Genetischen Profil</div>
        <div class="card-subtitle">
          Score ${ms.score != null ? ms.score + '/10' : '—'} · ${ms.level || 'Unbekannt'} · ${hasExpert ? 'Standard (47 SNPs) + Experten (610 SNPs)' : 'Standard (47 SNPs)'}
        </div>
        <div class="text-xs mb-2" style="color:var(--text-muted);padding:8px 0;border-bottom:1px solid var(--border-light)">
          📊 <strong>So lesen Sie die Werte:</strong> Ein Wert von 0–10 zeigt an, wie stark ein Bereich genetisch gefordert ist.
          <strong>Niedrig (≤3.5)</strong> = Ihr genetischer Standard ist gut, keine Extra-Unterstützung nötig.
          <strong>Moderat (3.5–6.5)</strong> = leichte genetische Abweichung, Ihr Körper kann Extra-Hilfe brauchen.
          <strong>Hoch (≥6.5)</strong> = stärkere genetische Besonderheit, hier lohnt sich gezielte Unterstützung besonders.<br>
          <em>Klicken Sie auf eine Kategorie, um die einzelnen Gene und ihre Wirkung zu sehen.</em>
        </div>

        <div id="radar-chart" style="width:100%"></div>
      </div>

      <div class="card">
        <div class="card-title">📊 Kategorien-Scores (Standard · 47 SNPs)</div>
        <div class="text-xs mb-3" style="color:var(--text-muted)">
          🟢 ≤3.5 Niedrig · 🟡 3.5–6.5 Moderat · 🔴 ≥6.5 Erhöht
        </div>
        ${this._scoreTableHtml(standardScores, categoryExplanations, plainLang, 'std')}
      </div>

      ${hasExpert ? `
      <div class="card">
        <div class="card-title">🔬 Experten-Scores (610 SNPs)</div>
        <div class="card-subtitle">Erweiterte Abdeckung — zusätzliche Gene und Kategorien aus dem Expert-Panel</div>
        ${this._scoreTableHtml(expertScores, {}, {}, 'exp')}
      </div>` : ''}

      <div class="text-xs mt-2" style="color:var(--yellow);padding:10px;border:1px solid rgba(234,179,8,0.3);border-radius:6px;background:var(--yellow-bg);line-height:1.6">
        ⚠️ <strong>Hinweis:</strong> Ihr genetisches Profil zeigt genetische Veranlagungen, keine Diagnosen.
        Die Interpretation dient der Aufklärung und ersetzt <strong>keine ärztliche Beratung</strong>.
        Konsultieren Sie bei gesundheitlichen Fragen immer einen Arzt.
      </div>

      ${results.risk_profile?.interactions?.length > 0 ? `
      <div class="card">
        <div class="card-title">🔄 SNP-Interaktionen (Epistasis)</div>
        ${results.risk_profile.interactions.map(i => `
          <div class="supplement-card">
            <div class="supplement-name">${i.gene_a} + ${i.gene_b}</div>
            <div class="supplement-detail">${i.description} — Faktor: ×${i.factor}</div>
          </div>
        `).join('')}
      </div>` : ''}
    `;

    setTimeout(() => {
      Charts.renderRadar('radar-chart', rp, categoryExplanations, plainLang);
    }, 50);
  },

  _scoreTableHtml(scores, explanations, plainLang, prefix) {
    if (!scores || Object.keys(scores).length === 0) {
      return '<div class="text-xs" style="color:var(--text-muted);padding:12px 0">Keine Daten verfügbar</div>';
    }
    const idPrefix = prefix || 'std';
    return `
      <table class="score-table">
        <thead><tr>
          <th>Kategorie</th>
          <th>Score</th>
          <th>Risiko</th>
          <th>SNPs</th>
          <th>Gene</th>
        </tr></thead>
        <tbody>
          ${Object.entries(scores)
            .sort((a, b) => (b[1]?.score || 0) - (a[1]?.score || 0))
            .map(([cat, data]) => {
              const catId = 'snp-' + idPrefix + '-' + cat.replace(/[^a-zA-Z0-9]/g, '-');
              const snps = data.contributing_snps || [];
              return `
              <tr style="cursor:pointer" onclick="App._toggleSnpDetail('${catId}')">
                <td style="font-weight:500">${this._catLabel(cat)}</td>
                <td><span class="${this._scoreClass(data.score || 0)}">${data.score != null ? data.score.toFixed(1) : '—'}</span></td>
                <td><span class="badge ${data.category === 'Erhöht' ? 'badge-high' : data.category === 'Moderat' ? 'badge-moderate' : 'badge-low'}">${data.category || '?'}</span></td>
                <td style="font-size:12px">${data.tested_snps || 0}/${(data.tested_snps || 0) + (data.missing_snps || 0)}</td>
                <td style="font-size:12px;color:var(--text-muted)">${data.genes?.slice(0, 4).join(', ') || ''}</td>
              </tr>
              <tr id="${catId}" style="display:none">
                <td colspan="5" style="padding:0">
                  <div style="background:var(--bg-tertiary);padding:12px 16px;border-radius:4px;margin:4px 0">
                    ${this._plainLangForCat(cat, plainLang)}
                    ${snps.length > 0 ? `
                      <div style="margin-top:10px">
                        ${snps.map(s => `
                          <div style="padding:8px 0;border-bottom:1px solid var(--border-light)">
                            <div style="font-weight:600;font-size:13px;color:var(--text-primary)">
                              ${s.gene || s.rsid} (${s.rsid})
                              <span class="${this._scoreClass((s.raw_score || 0) * 10)}" style="font-size:11px;margin-left:8px">
                                ${s.risk_count != null ? s.risk_count + ' Risiko-Allele' : '—'}
                              </span>
                            </div>
                            <div style="font-size:12px;color:var(--text-secondary);margin-top:2px">${s.description || ''}</div>
                            ${s.effect ? `<div style="font-size:11px;color:var(--text-muted);margin-top:2px">🧬 Wirkung: ${this._effectLabel(s.effect)}</div>` : ''}
                            ${s.recommendation ? `<div style="font-size:11px;color:var(--accent);margin-top:2px">💡 ${s.recommendation}</div>` : ''}
                          </div>
                        `).join('')}
                      </div>
                    ` : '<div class="text-xs" style="color:var(--text-muted)">Keine SNP-Details verfügbar</div>'}
                  </div>
                </td>
              </tr>`;
            }).join('')}
        </tbody>
      </table>
    `;
  },

  /* ================================================================
     PAGE: SUPPLEMENTS
     ================================================================ */
  _renderSupplementsPage() {
    const body = document.getElementById('main-body');
    const results = State.get('results');

    if (!results || !results.supplement_plan) {
      body.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">💊</div>
          <div class="empty-state-title">Keine Supplement-Empfehlungen</div>
          <div class="empty-state-text">Führen Sie zuerst eine DNA-Analyse durch.</div>
          <button class="btn btn-primary" onclick="App._renderPage('dna')">🧬 Zur DNA-Analyse</button>
        </div>
      `;
      return;
    }

    const sp = results.supplement_plan || [];
    const high = sp.filter(s => s.risk_level === 'hoch');
    const medium = sp.filter(s => s.risk_level === 'mittel');
    const low = sp.filter(s => s.risk_level === 'niedrig');
    const p = State.get('profile');

    body.innerHTML = `
      <div class="card">
        <div class="flex justify-between items-center mb-3">
          <span class="card-title" style="margin-bottom:0">👤 Profil</span>
          <span class="text-xs" style="color:var(--text-muted)">Beeinflusst Supplement-Dosierung</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:10px;align-items:end">
          <div class="form-group" style="margin-bottom:0">
            <label class="form-label">Alter (Jahre)</label>
            <input type="number" class="form-input" id="supp-profile-age" value="${p.age}" min="1" max="120">
          </div>
          <div class="form-group" style="margin-bottom:0">
            <label class="form-label">Gewicht (kg)</label>
            <input type="number" class="form-input" id="supp-profile-weight" value="${p.weight}" min="20" max="300">
          </div>
          <div class="form-group" style="margin-bottom:0">
            <label class="form-label">Geschlecht</label>
            <select class="form-select" id="supp-profile-gender">
              <option value="m" ${p.gender === 'm' ? 'selected' : ''}>Männlich</option>
              <option value="w" ${p.gender === 'w' ? 'selected' : ''}>Weiblich</option>
              <option value="d" ${p.gender === 'd' ? 'selected' : ''}>Divers</option>
            </select>
          </div>
          <div class="form-group" style="margin-bottom:0">
            <button class="btn btn-primary" id="btn-update-supplements" style="white-space:nowrap">📊 Aktualisieren</button>
          </div>
        </div>
        <div id="supp-update-status" style="margin-top:8px"></div>
      </div>

      <div class="text-xs mt-2" style="color:var(--yellow);padding:10px;border:1px solid rgba(234,179,8,0.3);border-radius:6px;background:var(--yellow-bg);line-height:1.6">
        ⚠️ <strong>Hinweis:</strong> Diese Dosierungsempfehlungen basieren auf Ihren genetischen Daten und wissenschaftlichen Leitlinien.
        Sie ersetzen <strong>keine ärztliche Beratung</strong>. Besprechen Sie Supplement-Einnahmen immer mit Ihrem Arzt,
        besonders wenn Sie bereits Medikamente einnehmen.
      </div>

      ${high.length > 0 ? `
      <div class="card">
        <div class="card-title">🔴 Hohe Priorität</div>
        ${high.map(s => this._supplementCard(s)).join('')}
      </div>` : ''}

      ${medium.length > 0 ? `
      <div class="card">
        <div class="card-title">🟡 Mittlere Priorität</div>
        ${medium.map(s => this._supplementCard(s)).join('')}
      </div>` : ''}

      ${low.length > 0 ? `
      <div class="card">
        <div class="card-title">🟢 Niedrige Priorität</div>
        ${low.map(s => this._supplementCard(s)).join('')}
      </div>` : ''}

      <div class="card">
        <div class="card-title">📊 Details zur Dosierung</div>
        <div class="text-xs" style="color:var(--text-muted)">
          <p>1. Genetische Anpassung: Risiko-Gene × Faktor (prozentual, skaliert mit Gewicht) — <em>außer bei Omega-3, da FADS1/2 nur die ALA-Umwandlung betreffen, nicht fertiges EPA/DHA</em></p>
          <p>2. Gewichtsfaktor: +200 mg pro 20 kg</p>
          <p>3. Blutwert-Anpassung: z.B. Omega-3-Index &lt;8% → ×1.5</p>
          <p>4. Methylierungs-Score: +30% bei Score &gt;5</p>
          <p>5. Medikamenten-Interaktionen: Dosis-Begrenzung bei Kontraindikation</p>
          <p>6. Geschlechtsfaktor: Frauen mehr DHA, Männer mehr EPA</p>
          <p>7. Altersfaktor: supplement-spezifische Anpassungen</p>
        </div>
      </div>
    `;

    // ── Profile bindings on supplements page ──
    const ageEl = document.getElementById('supp-profile-age');
    const weightEl = document.getElementById('supp-profile-weight');
    const genderEl = document.getElementById('supp-profile-gender');
    const updateBtn = document.getElementById('btn-update-supplements');

    if (ageEl) ageEl.addEventListener('change', e => {
      const p = State.get('profile');
      p.age = parseInt(e.target.value) || 35;
      State.set('profile', p);
    });
    if (weightEl) weightEl.addEventListener('change', e => {
      const p = State.get('profile');
      p.weight = parseInt(e.target.value) || 75;
      State.set('profile', p);
    });
    if (genderEl) genderEl.addEventListener('change', e => {
      const p = State.get('profile');
      p.gender = e.target.value;
      State.set('profile', p);
    });
    if (updateBtn) updateBtn.addEventListener('click', () => this._updateSupplements());
  },

  async _updateSupplements() {
    const statusDiv = document.getElementById('supp-update-status');
    const results = State.get('results');
    if (!results) return;

    statusDiv.innerHTML = '<div class="alert alert-info">🔄 Berechne Supplemente neu...</div>';

    try {
      const p = State.get('profile');
      const formData = new FormData();
      formData.append('profile', JSON.stringify(p));

      const newResults = await API.analyze(formData);
      State.set('results', newResults);

      statusDiv.innerHTML = '<div class="alert alert-success">✅ Supplemente aktualisiert</div>';
      // Re-render the whole page
      this._renderSupplementsPage();
    } catch (err) {
      statusDiv.innerHTML = `<div class="alert alert-error">❌ ${err.message}</div>`;
    }
  },

  _supplementCard(s) {
    const dose = s.final_dose_mg || s.dose_mg || 0;
    const riskLevel = s.risk_level || 'niedrig';
    const badgeClass = riskLevel === 'hoch' ? 'badge-high' : riskLevel === 'mittel' ? 'badge-moderate' : 'badge-low';
    const badgeLabel = riskLevel === 'hoch' ? '🔴 Hoch' : riskLevel === 'mittel' ? '🟡 Mittel' : '🟢 Niedrig';
    const reasons = s.reasons || [];
    const epaDha = s.epa_dha;
    const interactions = (s.interactions || []).map(i => this._translateInteraction(i));

    return `
      <div class="supplement-card">
        <div class="flex justify-between items-center">
          <div class="supplement-name">${s.name || s.id}
            <span class="badge ${badgeClass}" style="margin-left:8px">${badgeLabel}</span>
          </div>
        </div>
        <div class="supplement-dose">${dose}<span class="supplement-dose-unit"> ${s.unit || 'mg'}/Tag</span></div>
        ${epaDha ? `
          <div class="supplement-detail" style="color:var(--accent);font-weight:500;margin-top:4px">
            EPA: ${epaDha.epa} mg · DHA: ${epaDha.dha} mg
          </div>
        ` : ''}
        ${reasons.length > 0 ? `
          <div style="margin-top:8px">
            <div class="text-xs" style="color:var(--text-muted);font-weight:600;margin-bottom:4px">📐 Berechnung:</div>
            ${reasons.map(r => `
              <div class="text-xs" style="color:var(--text-secondary);padding:2px 0;border-bottom:1px solid var(--border-light)">${r}</div>
            `).join('')}
          </div>
        ` : ''}
        ${s.base_note ? `<div class="supplement-detail">${s.base_note}</div>` : ''}
        ${s.preferred_form ? `<div class="supplement-form">Empfohlen: ${s.preferred_form}</div>` : ''}
        ${s.safety ? `<div class="supplement-detail" style="color:var(--yellow);margin-top:4px">⚠️ ${s.safety}</div>` : ''}
        ${interactions.length > 0 ? `
          <div style="margin-top:10px">
            <div class="text-xs" style="color:var(--text-muted);font-weight:600;margin-bottom:4px">⚡ Wechselwirkungen mit anderen Nährstoffen:</div>
            ${interactions.map(i => `
              <div class="text-xs" style="color:var(--text-secondary);padding:4px 0;border-bottom:1px solid var(--border-light)">${i}</div>
            `).join('')}
          </div>
        ` : ''}
      </div>
    `;
  },

  _translateInteraction(interaction) {
    const plain = {
      'Vitamin E (als Schutz vor Oxidation)':
        'Vitamin E: Omega-3-Fettsäuren sind empfindlich gegenüber Oxidation. Vitamin E schützt sie im Körper vor dem Verderben — ähnlich wie ein Schutzumschlag.',
      'Vitamin D3 (erhoeht Mg-Bedarf)':
        'Vitamin D3: Ihr Körper braucht Magnesium, um Vitamin D überhaupt aktivieren zu können. Wenn Sie Vitamin D nehmen, verbrauchen Sie mehr Magnesium — der Bedarf steigt.',
      'Zink (kompetitive Aufnahme)':
        'Zink: Magnesium und Zink konkurrieren im Darm um die gleichen Aufnahme-Wege. Am besten zeitlich getrennt einnehmen (z.B. Magnesium morgens, Zink abends), damit beide gut ankommen.',
      'Magnesium (fuer D3-Aktivierung noetig)':
        'Magnesium: Vitamin D kann ohne Magnesium nicht in seine aktive Form umgewandelt werden. Magnesium ist sozusagen der Zündfunke für Vitamin D.',
      'K2 (lenkt Calcium in Knochen)':
        'Vitamin K2: Es sorgt dafür, dass das Calcium aus dem Vitamin D nicht in den Arterien landet, sondern in die Knochen eingebaut wird — quasi der Lotse für Calcium.',
      'Vitamin B12 (Methylcobalamin)':
        'Vitamin B12: 5-MTHF und B12 arbeiten im Methylzyklus als Team. B12 ist der Partner, der die Methylgruppen weiterreicht. Beide zusammen sind wirksamer.',
      'Betain/Cholin':
        'Betain/Cholin: Wenn der 5-MTHF-Weg nicht optimal läuft, springt Betain/Cholin als alternativer Methyl-Lieferant ein — ein zweiter Weg zum gleichen Ziel.',
      'Vitamin C (erhoeht Eisenaufnahme)':
        'Vitamin C: Es macht Eisen besser verfügbar, indem es dreiwertiges Eisen in zweiwertiges umwandelt — das kann der Darm viel besser aufnehmen. Bis zu 3x mehr Eisen gelangt so ins Blut.',
      'Calcium (kompetitive Aufnahme)':
        'Calcium: Eisen und Calcium stören sich gegenseitig bei der Aufnahme im Darm. Am besten mit zeitlichem Abstand einnehmen (2–3 Stunden).',
      'Kupfer (Zink ueberschreitet aufnahme)':
        'Kupfer: Viel Zink über längere Zeit kann die Kupfer-Aufnahme blockieren. Bei Zink über 25 mg/Tag sollte gelegentlich auch Kupfer mit aufgenommen werden.',
      'Curcumin (verbessert Bioverfuegbarkeit)':
        'Curcumin: Ein natürlicher Verstärker für Omega-3 — Curcumin und Omega-3 wirken zusammen besser gegen Entzündungen als jedes allein.',
      'Vitamin K2 (lenkt Calcium in Knochen)':
        'Vitamin K2: Es leitet das Calcium aus dem Blutkreislauf in die Knochen um. Ohne K2 könnte Calcium in den Arterien landen statt dort, wo es gebraucht wird.',
      'Vitamin D (verbessert Calciumaufnahme)':
        'Vitamin D: Es öffnet sozusagen die Tür für Calcium im Darm — ohne Vitamin D wird Calcium kaum aufgenommen, egal wie viel Sie essen.',
      'CoQ10 (mit fettloeslicher Mahraei)':
        'CoQ10: Da CoQ10 fettlöslich ist, nehmen Sie es am besten mit einer Mahlzeit ein, die etwas Fett enthält. Das steigert die Aufnahme um ein Vielfaches.',
      'Vitamin B-Komplex (synergistische Wirkung)':
        'B-Vitamine: Alle B-Vitamine arbeiten im Energiestoffwechsel zusammen. Fehlt eines, können die anderen nicht richtig arbeiten — ein gut eingestelltes Team.',
      'Vitamin D (unterstuetzt Calciumeinbau)':
        'Vitamin D: Es befördert Calcium aus dem Darm ins Blut. Erst mit genug Vitamin D kann Calcium überhaupt dorthin gelangen, wo es gebraucht wird.',
      'Omega-3 (unterstuetzt Aufnahme)':
        'Omega-3: Vitamin D und K2 sind fettlöslich — sie brauchen Fett, um vom Darm aufgenommen zu werden. Omega-3-Fettsäuren liefern dieses Fett gleich mit.',
    };
    return plain[interaction] || interaction;
  },

  /* ================================================================
     PAGE: MEDICATIONS INPUT (unter DATEN)
     ================================================================ */
  _renderMedicationsInputPage() {
    const body = document.getElementById('main-body');
    const p = State.get('profile');

    body.innerHTML = `
      <div class="card">
        <div class="card-title">💊 Medikamente verwalten</div>
        <div class="card-subtitle">Wählen Sie Ihre Medikamente für die CYP450-Interaktionsprüfung (Verträglichkeit)</div>

        <div class="form-group">
          <label class="form-label">Eingenommene Medikamente</label>
          <div id="med-drug-tags"></div>
          <div style="display:flex;gap:8px;margin-top:8px">
            <input type="text" class="form-input" id="med-drug-search-input" placeholder="Medikament suchen... (z.B. Omeprazol, Metformin, Warfarin)" style="flex:1">
            <button class="btn btn-sm" id="med-drug-search-btn">Suchen</button>
          </div>
          <div id="med-drug-search-results" style="margin-top:8px"></div>
        </div>

        <hr class="section-divider">

        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-primary" id="btn-med-save">💾 Speichern & Analyse aktualisieren</button>
          <button class="btn" onclick="App._renderPage('tolerance')">💉 Zur Verträglichkeit</button>
        </div>
        <div id="med-save-status" style="margin-top:8px"></div>
      </div>

      <div class="card">
        <div class="card-title">ℹ️ Verfügbare Medikamente in der Datenbank</div>
        <div class="text-sm" style="color:var(--text-secondary)">
          CYP2D6, CYP2C19, CYP1A2, CYP3A4, CYP2C9 — 19 Medikamente mit CPIC-Level-A-Evidenz
        </div>
        <div class="text-xs mt-2" style="color:var(--text-muted)">
          Nach dem Speichern werden Supplement-Dosierungen und Verträglichkeits-Warnungen automatisch aktualisiert.
        </div>
        <div class="text-xs mt-2" style="color:var(--yellow);padding:8px;border:1px solid rgba(234,179,8,0.2);border-radius:4px;background:var(--yellow-bg);line-height:1.6">
          ⚠️ <strong>Wichtig:</strong> Diese Daten dienen der Aufklärung. Nehmen Sie keine Medikamentenänderungen ohne Rücksprache mit Ihrem Arzt vor.
        </div>
      </div>
    `;

    // Bind drug search
    document.getElementById('med-drug-search-btn').addEventListener('click', () => this._medDrugSearch());
    document.getElementById('med-drug-search-input').addEventListener('keydown', e => {
      if (e.key === 'Enter') this._medDrugSearch();
    });

    // Bind save
    document.getElementById('btn-med-save').addEventListener('click', () => this._medSaveDrugs());

    // Show selected drugs
    this._renderMedDrugTags();
  },

  _medDrugSearch() {
    const input = document.getElementById('med-drug-search-input');
    const q = input.value.trim();
    if (!q) return;

    API.drugSearch(q).then(data => {
      const resultsDiv = document.getElementById('med-drug-search-results');
      if (data.results?.length > 0) {
        resultsDiv.innerHTML = `
          <div class="drug-tags">
            ${data.results.map(d =>
              `<span class="drug-tag" onclick="App._medAddDrug('${d.replace(/'/g, "\\'")}')">+ ${d}</span>`
            ).join('')}
          </div>
        `;
      } else {
        resultsDiv.innerHTML = '<div class="text-xs" style="color:var(--text-muted)">Keine Treffer</div>';
      }
    }).catch(() => {});
  },

  _medAddDrug(name) {
    const p = State.get('profile');
    if (!p.drugs.includes(name)) {
      p.drugs.push(name);
      State.set('profile', p);
    }
    this._renderMedDrugTags();
    document.getElementById('med-drug-search-results').innerHTML = '';
    document.getElementById('med-drug-search-input').value = '';
  },

  _medRemoveDrug(name) {
    const p = State.get('profile');
    p.drugs = p.drugs.filter(d => d !== name);
    State.set('profile', p);
    this._renderMedDrugTags();
  },

  _renderMedDrugTags() {
    const div = document.getElementById('med-drug-tags');
    if (!div) return;
    const drugs = State.get('profile').drugs || [];
    if (drugs.length === 0) {
      div.innerHTML = '<div class="text-xs" style="color:var(--text-muted)">Keine Medikamente ausgewählt — suchen und hinzufügen</div>';
      return;
    }
    div.innerHTML = `
      <div class="drug-tags">
        ${drugs.map(d =>
          `<span class="drug-tag selected">
            ${d}
            <span class="drug-tag-remove" onclick="App._medRemoveDrug('${d.replace(/'/g, "\\'")}')">×</span>
          </span>`
        ).join('')}
      </div>
    `;
  },

  async _medSaveDrugs() {
    const statusDiv = document.getElementById('med-save-status');
    const results = State.get('results');

    statusDiv.innerHTML = '<div class="alert alert-info">💾 Speichere & analysiere neu...</div>';

    try {
      const p = State.get('profile');
      const formData = new FormData();
      formData.append('profile', JSON.stringify(p));

      const newResults = await API.analyze(formData);
      State.set('results', newResults);

      const drugCount = p.drugs?.length || 0;
      const warnCount = newResults.drug_warnings?.length || 0;
      statusDiv.innerHTML = `<div class="alert alert-success">✅ ${drugCount} Medikamente gespeichert · ${warnCount} Warnungen gefunden · Analyse aktualisiert</div>`;

      // Offer link to tolerance page
      statusDiv.innerHTML += `<div style="margin-top:8px"><button class="btn btn-sm" onclick="App._renderPage('tolerance')">💉 Verträglichkeit anzeigen</button></div>`;
    } catch (err) {
      statusDiv.innerHTML = `<div class="alert alert-error">❌ ${err.message}</div>`;
    }
  },

  /* ================================================================
     PAGE: TOLERANCE (Verträglichkeit — renamed old medications)
     ================================================================ */
  _renderTolerancePage() {
    const body = document.getElementById('main-body');
    const results = State.get('results');

    if (!results) {
      body.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">💉</div>
          <div class="empty-state-title">Keine Medikamenten-Daten</div>
          <div class="empty-state-text">Führen Sie zuerst eine DNA-Analyse durch.</div>
          <button class="btn btn-primary" onclick="App._renderPage('dna')">🧬 Zur DNA-Analyse</button>
        </div>
      `;
      return;
    }

    const drugWarnings = results.drug_warnings || [];
    const phenotypes = results.phenotypes || {};

    body.innerHTML = `
      <div class="card">
        <div class="card-title">💉 Verträglichkeit (CYP450)</div>
        <div class="card-subtitle">Ob ein Medikament bei Ihnen normal wirkt, stärker oder schwächer — das liegt an Ihren Genen für den Medikamenten-Abbau in der Leber.</div>

        ${Object.keys(phenotypes).length > 0 ? `
          <div class="mb-4">
            <div class="text-sm mb-2" style="color:var(--text-secondary);font-weight:600">Ihr Leber-Enzym-Profil (CYP450)</div>
            <div style="display:flex;flex-wrap:wrap;gap:8px">
              ${Object.entries(phenotypes).map(([gene, pheno]) => `
                <span class="drug-tag" style="background:var(--bg-tertiary);padding:6px 12px;cursor:default">
                  <strong>${gene}</strong>: ${this._translatePhenotype(pheno.phenotype || pheno)}
                </span>
              `).join('')}
            </div>
            <div class="text-xs mt-2" style="color:var(--text-muted);line-height:1.6">
              ${this._cypExplanation(Object.keys(phenotypes))}
            </div>
          </div>
        ` : '<div class="text-xs" style="color:var(--text-muted);padding:8px 0">Keine CYP-Gen-Daten in Ihrer DNA-Datei gefunden.</div>'}
      </div>

      <div class="card">
        <div class="card-title">⚠️ Warnungen & Interaktionen</div>
        ${drugWarnings.length > 0 ? `
          <div class="text-xs mb-3" style="color:var(--text-secondary);line-height:1.6">
            Diese Warnungen zeigen, wie Ihre Leber-Enzyme Ihre Medikamente verarbeiten.
            Je nach Genvariante kann ein Medikament <strong>stärker oder schwächer wirken</strong> als üblich.
            Die Empfehlungen basieren auf den CPIC-Richtlinien (Clinical Pharmacogenetics Implementation Consortium).
          </div>
          ${drugWarnings.map(w => this._drugWarningCard(w)).join('')}
          <div class="text-xs mt-4" style="color:var(--yellow);padding:10px;border:1px solid rgba(234,179,8,0.3);border-radius:6px;background:var(--yellow-bg);line-height:1.6">
            ⚠️ <strong>Wichtig:</strong> Diese Informationen dienen der Aufklärung und ersetzen keine ärztliche Beratung.
            Nehmen Sie keine Dosisanpassungen oder Medikamentenänderungen <strong>ohne Rücksprache mit Ihrem Arzt</strong> vor.
            Die genetischen Daten geben Hinweise auf mögliche Wechselwirkungen — die klinische Entscheidung trifft immer Ihr behandelnder Arzt.
          </div>
        ` : `
          <div class="text-xs" style="color:var(--text-muted);padding:12px 0">
            Keine Medikamenten-Warnungen. Fügen Sie Medikamente unter "Medikamente" in Daten hinzu.
          </div>
        `}
      </div>

      <div style="display:flex;gap:8px">
        <button class="btn" onclick="App._renderPage('medications')">💊 Medikamente verwalten</button>
        <button class="btn" onclick="App._renderPage('supplements')">💊 Supplemente prüfen</button>
      </div>
    `;
  },

  _translatePhenotype(pheno) {
    if (!pheno) return 'normal';
    const labels = {
      'langsam (PM)': 'Langsamer Abbau (PM)',
      'intermediaer (IM)': 'Verlangsamter Abbau (IM)',
      'normal (EM)': 'Normaler Abbau (EM)',
      'schnell (UM)': 'Schneller Abbau (UM)',
      'langsam': 'Langsamer Abbau',
      'schnell': 'Schneller Abbau',
      'normal': 'Normaler Abbau',
    };
    return labels[pheno] || pheno;
  },

  _cypExplanation(genes) {
    const explanations = {
      'CYP2D6': 'CYP2D6 baut etwa 25% aller verschriebenen Medikamente ab — darunter viele Antidepressiva, Betablocker, Opioid-Schmerzmittel und Antipsychotika. Je nach Variante arbeiten Sie entweder "normal", "langsam" oder "schnell".',
      'CYP2C19': 'CYP2C19 ist wichtig für Magensäure-Hemmer (Omeprazol), das Blutgerinnungsmittel Clopidogrel und einige Antidepressiva. Bei "langsamen" Varianten wirken diese Medikamente stärker und länger.',
      'CYP2C9': 'CYP2C9 baut Blutverdünner (Warfarin, Phenprocoumon), entzündungshemmende Schmerzmittel und bestimmte Blutdruckmittel ab. Die Dosis muss bei Varianten oft angepasst werden.',
      'CYP1A2': 'CYP1A2 baut Koffein, bestimmte Antidepressiva und Schmerzmittel ab. Raucher bauen diese Stoffe schneller ab (CYP1A2 wird durch Rauchen aktiviert).',
      'CYP3A4': 'CYP3A4 ist das wichtigste Leber-Enzym überhaupt — es baut etwa 50% aller Medikamente ab. Dazu gehören viele Statine, Blutdruckmittel, Immunsuppressiva und Hormonpräparate.',
    };
    const found = genes.map(g => explanations[g] || '').filter(Boolean);
    if (found.length === 0) return '';
    return '🧬 ' + found.join('<br><br>🧬 ');
  },

  _drugWarningCard(w) {
    const drug = w.drug || w.medikament || 'Unbekannt';
    const severity = w.severity || 'verringert';
    const pheno = w.phenotype || '';
    const gene = w.gene || '';
    const rec = w.recommendation || w.empfehlung || '';

    // Severity label and icon
    const sevConfig = {
      'kontraindiziert': { icon: '⛔', label: 'Nicht empfohlen', color: 'var(--red)' },
      'erhoeht': { icon: '🔴', label: 'Erhöhtes Risiko', color: 'var(--red)' },
      'verringert': { icon: '🟡', label: 'Vorsicht geboten', color: 'var(--yellow)' },
      'positiv': { icon: '🟢', label: 'Positiver Effekt', color: 'var(--green)' },
    };
    const cfg = sevConfig[severity] || sevConfig.verringert;

    // Clean up recommendation text - remove technical prefixes
    let cleanRec = rec
      .replace(/^🟡 |^🔴 |^⛔ |^ℹ️ /, '')
      .replace(/^ALTERNATIVE:\s*/, '')
      .replace(/^DOSISANPASSUNG:\s*/i, '')
      .replace(/^KONTRAINDIZIERT:\s*/i, '')
      .replace(/^VORSICHT:\s*/i, '')
      .replace(/^INFO:\s*/i, '')
      .trim();

    // Detailed explanation based on severity + gene
    let explanation = '';
    if (severity === 'kontraindiziert') {
      explanation = 'Ihr Körper kann dieses Medikament nicht richtig verarbeiten. Es sollte nicht eingenommen werden — es gibt sicherere Alternativen.';
    } else if (severity === 'erhoeht') {
      if (pheno.includes('langsam')) {
        explanation = `Weil Ihr ${gene}-Enzym verlangsamt arbeitet, baut Ihr Körper dieses Medikament langsamer ab. Es bleibt länger und stärker wirksam im Blut — die Dosis sollte reduziert werden.`;
      } else if (pheno.includes('schnell')) {
        explanation = `Weil Ihr ${gene}-Enzym beschleunigt arbeitet, baut Ihr Körper dieses Medikament sehr schnell ab. Es wirkt kürzer und schwächer — oft ist eine höhere Dosis nötig.`;
      }
    } else if (severity === 'verringert') {
      if (pheno.includes('langsam')) {
        explanation = `Ihr ${gene}-Enzym arbeitet verlangsamt. Dieses Medikament wird daher langsamer abgebaut — die Wirkung kann verstärkt sein.`;
      } else if (pheno.includes('schnell')) {
        explanation = `Ihr ${gene}-Enzym arbeitet beschleunigt. Dieses Medikament wird schneller abgebaut — die Wirkdauer kann verkürzt sein.`;
      } else {
        explanation = 'Die Verarbeitung dieses Medikaments weicht vom Durchschnitt ab. Eine Überwachung der Wirkung wird empfohlen.';
      }
    }

    return `
      <div class="drug-warning ${severity}">
        <div class="flex justify-between items-center">
          <div class="drug-warning-name">${cfg.icon} ${drug}</div>
          <span class="badge ${severity === 'erhoeht' || severity === 'kontraindiziert' ? 'badge-high' : severity === 'positiv' ? 'badge-low' : 'badge-moderate'}">${cfg.label}</span>
        </div>
        <div class="text-xs" style="color:var(--text-muted);margin-top:2px">Betroffenes Enzym: ${gene} · Ihr Profil: ${this._translatePhenotype(pheno)}</div>
        <div class="drug-warning-desc" style="margin-top:8px;line-height:1.6">${explanation || 'Dieses Medikament wird anders verarbeitet als beim Durchschnitt.'}</div>
        ${cleanRec ? `<div class="drug-warning-desc" style="margin-top:6px;padding:8px;background:var(--bg-tertiary);border-radius:4px">💡 <strong>Empfehlung:</strong> ${cleanRec}</div>` : ''}
      </div>
    `;
  },

  /* ================================================================
     PAGE: EXPORT
     ================================================================ */
  _renderExportPage() {
    const body = document.getElementById('main-body');
    const results = State.get('results');

    if (!results) {
      body.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📄</div>
          <div class="empty-state-title">Kein Report verfügbar</div>
          <div class="empty-state-text">Führen Sie zuerst eine Analyse durch.</div>
          <button class="btn btn-primary" onclick="App._renderPage('dna')">🧬 Zur DNA-Analyse</button>
        </div>
      `;
      return;
    }

    body.innerHTML = `
      <div class="card">
        <div class="card-title">📄 Report-Export</div>
        <div class="card-subtitle">Exportieren Sie Ihre Analyse als PDF oder Markdown</div>

        <div style="display:flex;gap:12px;flex-wrap:wrap">
          <button class="btn btn-primary" id="btn-export-pdf">
            📄 PDF-Report herunterladen
          </button>
          <button class="btn" id="btn-export-markdown">
            📝 Markdown anzeigen
          </button>
        </div>
      </div>

      <div class="card" id="markdown-preview" style="display:none">
        <div class="card-title">📝 Markdown-Report</div>
        <pre style="background:var(--bg-tertiary);padding:16px;border-radius:var(--radius);font-size:12px;overflow-x:auto;white-space:pre-wrap;color:var(--text-secondary);max-height:500px;overflow-y:auto">${results.markdown_report || ''}</pre>
      </div>
    `;

    document.getElementById('btn-export-pdf').addEventListener('click', () => {
      this._exportPdf(results);
    });

    document.getElementById('btn-export-markdown').addEventListener('click', () => {
      const preview = document.getElementById('markdown-preview');
      preview.style.display = preview.style.display === 'none' ? 'block' : 'none';
    });
  },

  async _exportPdf(results) {
    try {
      const p = State.get('profile');
      await API.exportPdf({
        risk_profile: results.risk_profile,
        methylation_score: results.methylation_score,
        supplement_plan: results.supplement_plan,
        blood_results: results.blood_results,
        profile: p,
      });
    } catch (err) {
      alert('PDF-Export fehlgeschlagen: ' + err.message);
    }
  },

  /* ================================================================
     HELPERS
     ================================================================ */
  _scoreClass(score) {
    if (score == null) return '';
    if (score >= 6.5) return 'score-high';
    if (score >= 3.5) return 'score-moderate';
    return 'score-low';
  },

  _catLabel(cat) {
    const labels = {
      methylierung: 'Methylierung',
      fettstoffwechsel: 'Fettstoffwechsel',
      vitamin_stoffwechsel: 'Vitamin-Stoffwechsel',
      entgiftung: 'Entgiftung',
      entzuendung: 'Entzündung',
      stoffwechsel: 'Stoffwechsel',
      sensitivitaet: 'Sensitivität',
      hormone: 'Hormone',
      knochen_gelenke: 'Knochen & Gelenke',
      herz_kreislauf: 'Herz & Kreislauf',
      sport_genetik: 'Sport-Genetik',
    };
    return labels[cat] || cat;
  },

  _toggleSnpDetail(id) {
    const row = document.getElementById(id);
    if (row) {
      row.style.display = row.style.display === 'none' ? 'table-row' : 'none';
    }
  },

  _plainLangForCat(cat, plainLang) {
    const text = plainLang[cat];
    if (text) {
      return `<div class="text-xs" style="color:var(--text-secondary);line-height:1.6;margin-bottom:8px">${text}</div>`;
    }
    return '';
  },

  _effectLabel(effect) {
    // 1. Individuelle Übersetzungen für bekannte Effekte (52 Standard-SNPs)
    const labels = {
      'verringerte_Folat_Umwandlung': 'Reduzierte Folat-Umwandlung — der Körper kann Folsäure aus der Nahrung schlechter in die aktive Form (5-MTHF) umwandeln. Das bremst den gesamten Methyl-Stoffwechsel aus.',
      'verringerte_LC_PUFA_Synthese': 'Reduzierte Omega-3-Eigenproduktion — der Körper kann aus pflanzlichen Omega-3-Quellen (Leinsamen, Walnüsse) weniger langkettige Fettsäuren (EPA/DHA) herstellen. Direktes Fischöl oder Algenöl ist hier sinnvoller.',
      'veraenderte_Omega6_Omega3_Ratio': 'Verschobenes Omega-6/3-Verhältnis — der Körper baut bevorzugt entzündungsfördernde Omega-6-Fettsäuren in die Zellmembranen ein.',
      'verringerte_VitaminD_Aufnahme': 'Reduzierte Vitamin-D-Wirkung — der Vitamin-D-Rezeptor arbeitet weniger effizient. Selbst bei guten Spiegeln im Blut kommt weniger im Körper an.',
      'verringerte_VitaminD_Bindung': 'Reduzierte Vitamin-D-Bindung — das Transportprotein, das Vitamin D im Blut zu den Zellen bringt, arbeitet weniger effizient.',
      'verringerte_B12_Regeneration': 'Verlangsamtes B12-Recycling — Vitamin B12 wird normalerweise vom Körper immer wieder neu verwertet. Hier klappt das schlechter, mehr B12 muss von außen kommen.',
      'erhoehtes_Homocystein_Risiko': 'Erhöhtes Homocystein-Risiko — ein Stoffwechsel-Zwischenprodukt wird langsamer abgebaut. Ein hoher Homocystein-Wert gilt als Risikofaktor für Herz und Gefäße.',
      'veraenderter_Betain_Stoffwechsel': 'Veränderter Betain-Stoffwechsel — Betain springt als alternativer Methyl-Lieferant ein, wenn der normale Folat-Weg nicht optimal läuft. Hier ist dieser Ausweich-Weg beeinträchtigt.',
      'verringerte_Phosphatidylcholin_Synthese': 'Reduzierte Cholin-Eigenproduktion — der Körper kann Cholin für Zellmembranen und Fettstoffwechsel der Leber schlechter selbst herstellen.',
      'verringerte_Entgiftung': 'Reduzierte Entgiftungskapazität — die Giftstoff-Abbau-Enzyme in der Leber arbeiten langsamer. Umweltgifte und Medikamente werden verzögert ausgeschieden.',
      'erhoehte_Entzuendungsbereitschaft': 'Erhöhte Entzündungsbereitschaft — das Immunsystem reagiert schneller und stärker auf Reize. Der Körper ist öfter im Alarm-Zustand, was auf Dauer belastet.',
      'erhoehte_IL6_Produktion': 'Erhöhte IL6-Produktion — der Entzündungsbotenstoff Interleukin-6 wird vermehrt ausgeschüttet. Das heizt Entzündungsprozesse im Körper an.',
      'verringerte_Fettoxidation': 'Reduzierte Fettverbrennung — der Körper holt sich Energie lieber aus Kohlenhydraten als aus Fett. Fettreserven werden langsamer abgebaut.',
      'verringerte_Lipolyse': 'Reduzierte Fettfreisetzung — Fettdepots geben gespeichertes Fett langsamer ans Blut ab. Bei Sport oder Fasten kann der Körper schwer auf Fettreserven zugreifen.',
      'erhoehte_Triglyceride': 'Erhöhte Blutfett-Werte — der Körper baut Nahrungsfette langsamer ab. Die Triglyceride im Blut können ansteigen, ein Risikofaktor für Herz-Kreislauf.',
      'erhoehtes_LDL_bei_gesaettigten_Fetten': 'Erhöhtes LDL bei gesättigten Fetten — der Körper reagiert empfindlicher auf gesättigte Fettsäuren. Bei fettreicher Ernährung steigt das LDL-Cholesterin stärker an.',
      'verringerte_mitochondriale_Antioxidans': 'Reduzierte Antioxidans-Abwehr in den Zellkraftwerken. Die Zellen sind anfälliger für oxidativen Stress.',
      'beeintraechtigte_mitochondriale_Funktion': 'Beeinträchtigte Mitochondrien-Funktion — die Zellkraftwerke arbeiten weniger effizient. Das kann sich in geringerer Energie und schnellerer Ermüdung äußern.',
      'verringerte_mitochondriale_Biogenese': 'Reduzierte Neubildung von Mitochondrien — der Körper kann weniger neue Zellkraftwerke bauen.',
      'verringerte_CoQ10_Regeneration': 'Reduzierte CoQ10-Regeneration — Coenzym Q10 wird schlechter recycelt. Es fehlt in den Mitochondrien als Energielieferant.',
      'langsamer_Koffein_Stoffwechsel': 'Langsamer Koffein-Abbau — Koffein bleibt 3-4x länger im Blut. Eine Tasse Kaffee am Mittag kann noch abends den Schlaf stören.',
      'veraenderter_Koffein_Stoffwechsel': 'Veränderter Koffein-Abbau — die Geschwindigkeit, mit der Koffein abgebaut wird, weicht vom Durchschnitt ab.',
      'erhoehte_Phase1_Aktivitaet': 'Erhöhte Phase-1-Entgiftung — die erste Stufe der Leber-Entgiftung läuft schneller. Das kann mehr aggressive Zwischenprodukte erzeugen.',
      'verringerte_Glutathion_Peroxidase': 'Reduzierte Glutathion-Aktivität — ein wichtiges Antioxidans-Enzym arbeitet langsamer.',
      'verringerte_LDL_Oxidationsschutz': 'Reduzierter Schutz vor LDL-Oxidation — das LDL-Cholesterin wird leichter geschädigt.',
      'verringerte_NO_Produktion': 'Reduzierte Stickstoffmonoxid-Produktion — die Blutgefäße können sich schlechter entspannen.',
      'verringerte_VitaminC_Rueckresorption': 'Reduzierte Vitamin-C-Rückresorption — die Nieren können Vitamin C schlechter zurückhalten. Der Bedarf steigt.',
      'verringerte_Beta_Carotin_Umwandlung': 'Reduzierte Beta-Carotin-Umwandlung — der Körper kann pflanzliches Beta-Carotin schlechter in aktives Vitamin A umwandeln.',
      'verringerte_B6_Nutzung': 'Reduzierte Vitamin-B6-Nutzung — B6 wird für über 100 Enzymreaktionen gebraucht. Die Wirksamkeit ist herabgesetzt.',
      'verringerte_DHA_Synthese': 'Reduzierte DHA-Eigenproduktion — DHA ist die wichtigste Omega-3-Fettsäure für Gehirn und Augen.',
      'verringerte_Fast_Twitch_Fasern': 'Weniger schnelle Muskelfasern — der Anteil an explosiven, kraftvollen Muskelfasern ist genetisch niedriger.',
      'verringerte_ATP_Regeneration': 'Verlangsamte ATP-Regeneration — die Energie-Reserven der Muskeln werden nach Belastung langsamer wieder aufgefüllt.',
      'veraenderte_Dopamin_Regulation': 'Veränderte Dopamin-Regulation — Dopamin ist ein Botenstoff für Motivation, Belohnung und Antrieb.',
      'veraenderte_Dopamin_Rezeptordichte': 'Veränderte Dopamin-Rezeptordichte — die Anzahl der Andockstellen für Dopamin im Gehirn ist verändert.',
      'verlangsamter_Katecholamin_Abbau': 'Verlangsamter Abbau von Stressbotenstoffen — Adrenalin und Noradrenalin bleiben länger im Blut.',
      'veraenderte_Katecholamin_Ansprechbarkeit': 'Veränderte Ansprechbarkeit auf Stresshormone — der Körper reagiert anders auf Adrenalin.',
      'COMT_Haplotyp_Bestimmung': 'COMT baut Dopamin und Stresshormone ab. Je nach Variante arbeiten Sie entweder fokussiert-ruhig oder flexibel-kreativ.',
      'erhoehtes_Risiko_fuer_Uebergewicht': 'Erhöhtes Risiko für Übergewicht — Appetit und Energieverbrauch werden genetisch beeinflusst.',
      'beeintraechtigter_Kohlenhydrat_Stoffwechsel': 'Beeinträchtigter Kohlenhydrat-Stoffwechsel — der Blutzucker wird nach kohlenhydratreichen Mahlzeiten langsamer reguliert.',
      'veraenderter_Fettstoffwechsel': 'Veränderter Fettstoffwechsel — die Verarbeitung von Nahrungsfetten und Cholesterin weicht vom Durchschnitt ab.',
      'veraenderter_Alkoholstoffwechsel': 'Veränderter Alkohol-Stoffwechsel — Alkohol wird anders abgebaut als normal.',
      'beeintraechtigter_Acetaldehyd_Abbau': 'Beeinträchtigter Acetaldehyd-Abbau — ein giftiges Abbauprodukt von Alkohol wird langsamer abgebaut.',
      'Laktase_Nicht_Persistenz': 'Laktase-Mangel — das Enzym für Milchzucker wird nach dem Kindesalter abgeschaltet. Milchprodukte können Blähungen und Bauchschmerzen auslösen.',
      'Zoeliakie_Risiko': 'Zöliakie-Risiko — das Immunsystem kann auf Gluten überreagieren und die Dünndarmschleimhaut angreifen.',
      'Zoeliakie_Risiko_DQ8': 'Zöliakie-Risiko (Typ DQ8) — eine der beiden Hauptrisiko-Varianten für Gluten-Unverträglichkeit.',
      'erhoehtes_Autoimmun_Risiko': 'Erhöhtes Autoimmun-Risiko — das Immunsystem kann dazu neigen, körpereigenes Gewebe anzugreifen.',
      'veraenderte_Immunregulation': 'Veränderte Immunregulation — die Balance zwischen Abwehr und Toleranz ist verschoben.',
      'APOE_epsilon2_niedrigeres_LDL': 'APOE ε2 — diese Variante ist mit niedrigerem LDL-Cholesterin verbunden, aber auch mit erhöhten Triglyceriden.',
      'verringerte_Histamin_Aktivitaet': 'Reduzierte Histamin-Aktivität — Histamin wird langsamer abgebaut. Nach histaminreichen Lebensmitteln können Kopfschmerzen oder Hautreaktionen auftreten.',
      'veraenderter_Transsulfurierungsweg': 'Veränderter Transsulfurierungsweg — dieser Weg baut Homocystein zu Glutathion ab. Ist er gestört, fehlt Antioxidans-Schutz.',
      'CYP2D6Star4_Nullaktivitaet': 'CYP2D6 *4 — dieser Genabschnitt ist komplett inaktiv. Medikamente werden langsamer abgebaut.',
      'CYP2D6Star10_ReduzierteAktivitaet': 'CYP2D6 *10 — reduziert die Enzymaktivität auf etwa 30%. Medikamente werden langsamer verarbeitet.',
      'CYP2D6Star41_VerminderteExpression': 'CYP2D6 *41 — verminderte Enzymproduktion auf etwa 50%. Medikamenten-Verarbeitung ist verlangsamt.',
      'Laktase_Persistenz': 'Laktase-Persistenz — das Enzym für Milchzucker bleibt ein Leben lang aktiv. Milchprodukte werden gut vertragen.',
    };

    if (labels[effect]) return labels[effect];

    // 2. Automatische Generierung für Expert-Effekte (384+)
    return this._autoEffectLabel(effect);
  },

  _autoEffectLabel(effect) {
    // Prefix-Übersetzungen
    const prefixMap = {
      'verringerte_': 'Reduzierte ',
      'verringertes_': 'Reduziertes ',
      'erhoehte_': 'Erhöhte ',
      'erhoehtes_': 'Erhöhtes ',
      'erhoehten_': 'Erhöhter ',
      'erhoehter_': 'Erhöhter ',
      'beeintraechtigte_': 'Beeinträchtigte ',
      'beeintraechtigter_': 'Beeinträchtigter ',
      'veraenderte_': 'Veränderte ',
      'veraenderter_': 'Veränderter ',
      'veraendertes_': 'Verändertes ',
      'verlangsamter_': 'Verlangsamter ',
      'verlangsamte_': 'Verlangsamte ',
      'fehlende_': 'Fehlende ',
      'fehlender_': 'Fehlender ',
      'reduced_': 'Reduced ',
      'accelerated_': 'Accelerated ',
      'altered_': 'Altered ',
    };

    // Suffix-Erklärungen für bekannte Endungen
    const suffixExplanations = {
      '_Aktivität': ' — das Enzym arbeitet anders als normal.',
      '_Aktivity': ' — the enzyme activity is altered.',
      '_Expression': ' — die Produktion dieses Proteins ist verändert.',
      '_Produktion': ' — die Produktion dieses Botenstoffs ist verändert.',
      '_Spiegel': ' — der Spiegel dieses Stoffes im Blut ist genetisch beeinflusst.',
      '_Synthese': ' — die körpereigene Herstellung ist verändert.',
      '_Stoffwechsel': ' — der Stoffwechselweg arbeitet anders als normal.',
      '_Aufnahme': ' — die Aufnahme dieses Nährstoffs ist verändert.',
      '_Abbau': ' — der Abbau dieses Stoffes läuft anders als normal.',
      '_Neigung': ' — die grundsätzliche Neigung ist genetisch erhöht.',
      '_Risiko': ' — das Risiko ist genetisch leicht erhöht.',
      '_Transport': ' — der Transport dieses Stoffes im Körper ist verändert.',
      '_Funktion': ' — die Funktion dieses Gens/Proteins ist verändert.',
      '_Signalweg': ' — der Signalweg in der Zelle ist verändert.',
      '_Wirkung': ' — die Wirkung dieses Botenstoffs ist verändert.',
      '_Aktivierung': ' — die Aktivierung dieser Substanz ist verändert.',
      '_Umwandlung': ' — die Umwandlung in die aktive Form ist verändert.',
      '_Oxidation': ' — der oxidative Abbau ist verändert.',
      '_Regeneration': ' — die Regeneration dieses Stoffes ist verändert.',
      '_Binding': ' — die Bindung an den Rezeptor ist verändert.',
      '_Regulation': ' — die Regulation dieses Prozesses ist verändert.',
      '_Ausscheidung': ' — die Ausscheidung über die Nieren ist verändert.',
      '_Veresterung': ' — die Veresterung dieses Stoffes ist verändert.',
      '_Hydroxylierung': ' — der Hydroxylierungs-Schritt ist verändert.',
      '_Inaktivierung': ' — die Inaktivierung ist verändert.',
      '_Rezeptordichte': ' — die Anzahl der Rezeptoren ist verändert.',
      '_Rezeptor': ' — der Rezeptor für diesen Botenstoff arbeitet anders.',
      '_Metabolismus': ' — der Metabolismus (Stoffwechsel) ist verändert.',
      '_Sensitivität': ' — die Empfindlichkeit gegenüber diesem Stoff ist verändert.',
    };

    let name = effect;

    // Prefix ersetzen
    for (const [prefix, replacement] of Object.entries(prefixMap)) {
      if (name.startsWith(prefix)) {
        name = replacement + name.slice(prefix.length);
        break;
      }
    }

    // Unterstriche durch Leerzeichen ersetzen für den Rest
    name = name.replace(/_/g, ' ').trim();

    // Großbuchstabe am Anfang
    name = name.charAt(0).toUpperCase() + name.slice(1);

    // Suffix-Erklärung suchen
    for (const [suffix, explanation] of Object.entries(suffixExplanations)) {
      const searchSuffix = suffix.replace(/_/g, ' ');
      if (effect.includes(suffix) && !name.includes(explanation)) {
        name += explanation;
        break;
      }
    }

    // Fallback: allgemeine Erklärung anhängen wenn noch keine
    if (!name.includes('—')) {
      name += ' — dieser genetische Marker wurde im Experten-Panel analysiert und weicht vom Durchschnitt ab.';
    }

    return name;
  },
};

// ── Bootstrap ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => App.init());

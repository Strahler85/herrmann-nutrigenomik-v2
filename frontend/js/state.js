/* ── State Management ────────────────────────────────────────────── */
const State = {
  _data: {
    serverStatus: null,
    results: null,
    bloodHistory: [],
    dnaLoaded: false,
    bloodLoaded: false,
    analysisDone: false,
    currentPage: 'dashboard',
    profile: { age: 35, weight: 75, gender: 'm', drugs: [] },
  },

  _listeners: {},

  get(key) {
    return this._data[key];
  },

  set(key, value) {
    this._data[key] = value;
    this._notify(key, value);
  },

  on(key, callback) {
    if (!this._listeners[key]) this._listeners[key] = [];
    this._listeners[key].push(callback);
  },

  _notify(key, value) {
    if (this._listeners[key]) {
      this._listeners[key].forEach(cb => cb(value));
    }
  },

  getRiskProfile() {
    return this._data.results?.risk_profile?.category_scores || {};
  },

  getSupplements() {
    return this._data.results?.supplement_plan || [];
  },

  getMethylation() {
    return this._data.results?.methylation_score || {};
  },

  getDrugWarnings() {
    return this._data.results?.drug_warnings || [];
  },

  getPhenotypes() {
    return this._data.results?.phenotypes || {};
  },

  getBloodResults() {
    return this._data.results?.blood_results || [];
  },

  getExpertData() {
    return this._data.results?.expert || null;
  },
};

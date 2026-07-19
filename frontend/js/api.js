/* ── API Client ──────────────────────────────────────────────────── */
const API = {
  async status() {
    const r = await fetch('/api/status');
    return r.json();
  },

  async analyze(formData, onProgress) {
    if (onProgress) onProgress('DNA wird analysiert...', 10);
    const r = await fetch('/api/analyze', { method: 'POST', body: formData });
    if (!r.ok) {
      const err = await r.json();
      throw new Error(err.error || 'Analyse fehlgeschlagen');
    }
    if (onProgress) onProgress('Daten werden verarbeitet...', 50);
    return r.json();
  },

  async drugSearch(q) {
    const r = await fetch(`/api/drugs/search?q=${encodeURIComponent(q)}`);
    return r.json();
  },

  async bloodHistory(biomarker, limit = 30) {
    const params = new URLSearchParams();
    if (biomarker) params.set('biomarker', biomarker);
    params.set('limit', limit);
    const r = await fetch(`/api/blood/history?${params}`);
    return r.json();
  },

  async bloodUpload(formData) {
    const r = await fetch('/api/blood/upload', { method: 'POST', body: formData });
    if (!r.ok) {
      const err = await r.json();
      throw new Error(err.error || 'Upload fehlgeschlagen');
    }
    return r.json();
  },

  async bloodSnapshot(values) {
    const r = await fetch('/api/blood/snapshot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ values }),
    });
    return r.json();
  },

  async bloodClear() {
    const r = await fetch('/api/blood/history', { method: 'DELETE' });
    return r.json();
  },

  async bloodTrend(biomarker) {
    const r = await fetch(`/api/blood/trend/${encodeURIComponent(biomarker)}`);
    return r.json();
  },

  async exportPdf(data) {
    const r = await fetch('/api/export/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!r.ok) throw new Error('PDF-Export fehlgeschlagen');
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'nutrigenomik_report.pdf';
    a.click();
    URL.revokeObjectURL(url);
  },
};

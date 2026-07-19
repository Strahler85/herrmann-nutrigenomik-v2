/* ── Charts — Plotly Radar & Bar ─────────────────────────────────── */
/* Uses Plotly.js loaded from CDN                                     */

const Charts = {
  /**
   * Render a radar chart for category risk scores.
   * @param {string} elementId - DOM element ID
   * @param {Object} categoryScores - { category: { score, tested_snps, missing_snps, genes } }
   * @param {Object} explanations - { category: 'description text' }
   * @param {Object} plainLang - { category: 'plain language text' }
   */
  renderRadar(elementId, categoryScores, explanations, plainLang) {
    const el = document.getElementById(elementId);
    if (!el || !categoryScores || Object.keys(categoryScores).length === 0) {
      if (el) el.innerHTML = '<div class="text-xs" style="padding:20px;text-align:center;color:var(--text-muted)">Keine Daten verfügbar</div>';
      return;
    }

    const labels = Object.keys(categoryScores);
    const values = labels.map(k => {
      const v = categoryScores[k]?.score;
      return v != null ? v : 0;
    });

    const hoverTexts = labels.map(k => {
      const d = categoryScores[k] || {};
      const tested = d.tested_snps || 0;
      const missing = d.missing_snps || 0;
      const expl = explanations[k] || '';
      const riskCat = d.category || '?';
      const score = d.score != null ? d.score : 0;
      return `<b>${k}</b><br>Score: ${score}/10 (${riskCat})<br>SNPs: ${tested}/${tested + missing}<br>${expl}`;
    });

    const color = '#6366f1';
    const fillColor = 'rgba(99, 102, 241, 0.15)';

    const data = [{
      type: 'scatterpolar',
      r: [...values, values[0]],
      theta: [...labels, labels[0]],
      fill: 'toself',
      name: 'Risikoprofil',
      line: { color, width: 2 },
      fillcolor: fillColor,
      hovertemplate: '%{text}<extra></extra>',
      text: [...hoverTexts, hoverTexts[0]],
    }];

    // Add threshold rings
    const thresholdAngles = [...labels, labels[0]].map((_, i) => {
      const degrees = (i / (labels.length || 1)) * 360;
      return degrees;
    });

    const layout = {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { color: '#8b8d9a', family: '-apple-system, sans-serif', size: 11 },
      polar: {
        bgcolor: 'transparent',
        radialaxis: {
          visible: true,
          range: [0, 10],
          tickfont: { size: 10, color: '#5c5e6b' },
          gridcolor: '#2a2c38',
          linecolor: '#2a2c38',
        },
        angularaxis: {
          tickfont: { size: 10, color: '#8b8d9a' },
          gridcolor: '#2a2c38',
          linecolor: '#2a2c38',
        },
      },
      margin: { l: 60, r: 60, t: 20, b: 20 },
      showlegend: false,
      height: 400,
    };

    const config = {
      responsive: true,
      displayModeBar: false,
    };

    Plotly.newPlot(elementId, data, layout, config);
  },

  /**
   * Render a horizontal bar chart for supplement doses.
   */
  renderSupplementsBars(elementId, supplements) {
    const el = document.getElementById(elementId);
    if (!el || !supplements || supplements.length === 0) {
      if (el) el.innerHTML = '<div class="text-xs" style="padding:20px;text-align:center;color:var(--text-muted)">Keine Supplemente</div>';
      return;
    }

    const names = supplements.map(s => s.name || s.id || '?');
    const doses = supplements.map(s => s.final_dose_mg || s.dose_mg || 0);

    const data = [{
      type: 'bar',
      x: doses,
      y: names,
      orientation: 'h',
      marker: {
        color: doses.map(d => d > 2000 ? '#ef4444' : d > 500 ? '#eab308' : '#22c55e'),
        opacity: 0.8,
      },
      hovertemplate: '%{y}: %{x} mg/Tag<extra></extra>',
    }];

    const layout = {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { color: '#8b8d9a', family: '-apple-system, sans-serif', size: 11 },
      xaxis: {
        title: 'mg/Tag',
        gridcolor: '#2a2c38',
        linecolor: '#2a2c38',
        tickfont: { size: 10, color: '#5c5e6b' },
      },
      yaxis: {
        gridcolor: '#2a2c38',
        linecolor: '#2a2c38',
        tickfont: { size: 11, color: '#e4e5ea' },
      },
      margin: { l: 160, r: 20, t: 10, b: 40 },
      height: Math.max(200, supplements.length * 36),
      showlegend: false,
    };

    const config = { responsive: true, displayModeBar: false };

    Plotly.newPlot(elementId, data, layout, config);
  },

  /**
   * Render a line chart for blood value history.
   */
  renderBloodTrend(elementId, history, biomarker) {
    const el = document.getElementById(elementId);
    if (!el || !history || history.length < 2) {
      if (el) {
        el.innerHTML = '<div class="text-xs" style="padding:20px;text-align:center;color:var(--text-muted)">Nicht genug Daten für Trend (min. 2 Messungen)</div>';
      }
      return;
    }

    const dates = history.map(h => h.date || h.timestamp?.slice(0, 10) || '');
    const values = history.map(h => {
      const v = h.values?.[biomarker]?.value;
      return v != null ? v : null;
    }).filter(v => v != null);

    if (values.length < 2) {
      el.innerHTML = '<div class="text-xs" style="padding:20px;text-align:center;color:var(--text-muted)">Nicht genug Datenpunkte</div>';
      return;
    }

    const validHistory = history.filter((_, i) => {
      const v = history[i].values?.[biomarker]?.value;
      return v != null;
    });

    const data = [{
      type: 'scatter',
      mode: 'lines+markers',
      x: validHistory.map(h => h.date || h.timestamp?.slice(0, 10) || ''),
      y: validHistory.map(h => h.values[biomarker].value),
      line: { color: '#6366f1', width: 2 },
      marker: { color: '#6366f1', size: 6 },
      hovertemplate: '%{x}<br>%{y} %{text}<extra></extra>',
      text: validHistory.map(h => h.values[biomarker]?.unit || ''),
    }];

    const layout = {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { color: '#8b8d9a', family: '-apple-system, sans-serif', size: 11 },
      xaxis: {
        gridcolor: '#2a2c38',
        linecolor: '#2a2c38',
        tickfont: { size: 10, color: '#5c5e6b' },
      },
      yaxis: {
        title: biomarker,
        gridcolor: '#2a2c38',
        linecolor: '#2a2c38',
        tickfont: { size: 10, color: '#5c5e6b' },
      },
      margin: { l: 60, r: 20, t: 10, b: 40 },
      height: 280,
      showlegend: false,
    };

    const config = { responsive: true, displayModeBar: false };
    Plotly.newPlot(elementId, data, layout, config);
  },

  cleanup(elementId) {
    const el = document.getElementById(elementId);
    if (el && el.data && el.layout) {
      Plotly.purge(elementId);
    }
  },
};

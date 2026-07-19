"""Report-Generator — Markdown/PDF-Export."""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


def generate_markdown_report(
    risk_profile: Dict,
    methylation_score: Dict,
    supplement_plan: List[Dict],
    blood_results: Optional[List[Dict]],
    profile: Dict,
    filename: str = 'nutrigenomik_report.md',
) -> str:
    """Generate comprehensive Markdown report."""
    now = datetime.now().strftime('%d.%m.%Y %H:%M')
    category_scores = risk_profile.get('category_scores', {})
    top_findings = risk_profile.get('top_findings', [])
    
    lines = []
    
    # Header
    lines += [
        '# Nutrigenomik & Supplement Report',
        '',
        f'**Erstellt**: {now}',
        f'**Profil**: {profile.get("age", "?")} Jahre, {profile.get("weight", "?")} kg, {profile.get("gender", "?")}',
        '',
        '> **Hinweis**: Dieser Report dient zu Bildungszwecken. Er ersetzt keine ärztliche Beratung.',
        '',
        '---',
        '',
    ]
    
    # Executive Summary
    lines += ['## Executive Summary', '']
    
    if top_findings:
        lines.append('**Top-Erkenntnisse:**')
        lines.append('')
        for f in top_findings[:5]:
            lines.append(f'- **{f["gene"]}** ({f["effect"]})')
        lines.append('')
    
    meth = methylation_score
    if meth.get('score') is not None:
        lines.append(f'**Methylierungs-Score**: {meth["score"]}/10 — {meth["level"]}')
        lines.append(f'*{meth["interpretation"]}*')
        lines.append('')
    
    # Score Overview
    lines += [
        '## Risikoprofil nach Kategorien',
        '',
        '| Kategorie | Score (0–10) | Risiko |',
        '|-----------|:------------:|:------:|',
    ]
    for cat, data in sorted(category_scores.items(), key=lambda x: -(x[1]['score'] or 0)):
        score = data['score'] if data['score'] is not None else 'N/A'
        cat_label = {'Niedrig': '🟢 Niedrig', 'Moderat': '🟡 Moderat',
                     'Erhöht': '🔴 Erhöht', 'Unbekannt': '⚪ Unbekannt'}.get(
            data.get('category', ''), '⚪')
        emoji = {'Niedrig': '🟢', 'Moderat': '🟡', 'Erhöht': '🔴', 'Unbekannt': '⚪'}.get(
            data.get('category', ''), '⚪')
        lines.append(f'| {cat} | {score} | {emoji} {data.get("category", "?")} |')
    lines += ['', '---', '']
    
    # Methylation detail
    lines += ['## Methylierungsstatus', '']
    if meth.get('score') is not None:
        lines.append(f'**Score**: {meth["score"]}/10')
        lines.append(f'**Level**: {meth["level"]}')
        lines.append(f'**Interpretation**: {meth["interpretation"]}')
        lines.append('')
        if meth.get('details'):
            lines += ['| Gen | rsID | Genotyp | Risikokopien | Beitrag |', 
                      '|-----|------|---------|:------------:|:------:|']
            for d in meth['details']:
                lines.append(f'| {d["gene"]} | {d["rsid"]} | {d["genotype"]} | {d["risk_count"]}/2 | {d["contribution"]} |')
            lines.append('')
    lines += ['---', '']
    
    # Detailed SNP findings
    lines += ['## Detaillierte SNP-Analyse', '']
    for cat, data in sorted(category_scores.items(), key=lambda x: -(x[1]['score'] or 0)):
        lines.append(f'### {cat} (Score: {data["score"]}/10 — {data.get("category", "?")})')
        lines.append('')
        if data.get('contributing_snps'):
            lines += ['| Gen | rsID | Genotyp | Risiko | Effekt |',
                      '|-----|------|---------|:------:|--------|']
            for s in data['contributing_snps']:
                risk_str = {0: '0/2 ✅', 1: '1/2 ⚠️', 2: '2/2 🔴'}.get(s['risk_count'], '?')
                lines.append(f'| {s["gene"]} | {s["rsid"]} | {s["genotype"]} | {risk_str} | {s.get("effect", "")} |')
            lines.append('')
        lines.append('')
    
    # Supplement Plan
    lines += [
        '---',
        '',
        '## Personalisierter Supplement-Plan',
        '',
        '| Supplement | Tagesdosis | Begründung |',
        '|------------|:----------:|------------|',
    ]
    for s in supplement_plan:
        dose = s.get('dose_display', f'{s["dose"]} {s["unit"]}')
        reasons = '; '.join(s.get('reasons', []))
        lines.append(f'| {s["name"]} | {dose} | {reasons} |')
    lines.append('')
    
    for s in supplement_plan:
        if s.get('cofactor'):
            lines.append(f'**{s["name"]}**: Cofaktor: {s["cofactor"]}')
        if s.get('safety'):
            lines.append(f'*Sicherheit*: {s["safety"]}')
    
    lines += ['', '---', '']
    
    # Blood values
    if blood_results:
        lines += ['## Blutwerte-Integration', '']
        for b in blood_results:
            status_emoji = {'optimal': '✅', 'suboptimal': '⚠️', 'niedrig': '🔴',
                           'hoch': '🔴', 'grenzwertig': '🟡', 'unbekannt': '⚪'}
            emoji = status_emoji.get(b.get('status', ''), '⚪')
            lines.append(f'- {emoji} {b["message"]}')
        lines.append('')
    
    # Alimentäre Empfehlungen
    lines += [
        '---', '',
        '## Ernährungsempfehlungen', '',
    ]
    if any(s['id'] == 'omega3' and s['dose'] > 1500 for s in supplement_plan):
        lines.append('- **Omega-3**: Fettreicher Fisch (Makrele, Lachs, Sardinen) 2-3x/Woche')
    if any(s['id'] == 'magnesium' and s['dose'] > 300 for s in supplement_plan):
        lines.append('- **Magnesium**: Kürbiskerne, Mandeln, dunkle Schokolade, grünes Blattgemüse')
    if any(s['id'] == 'mthfr' and s['dose'] >= 400 for s in supplement_plan):
        lines.append('- **Folat**: Grünes Blattgemüse, Hülsenfrüchte, Leber — plus aktives 5-MTHF')
    if any(s['id'] == 'vitamin_d3_k2' and s['dose'] > 2000 for s in supplement_plan):
        lines.append('- **Vitamin D**: Eier, fetter Fisch, Pilze. Vitamin-D-Spiegel optimieren')
    if methylation_score.get('score') and methylation_score['score'] > 5:
        lines.append('- **Methylierung**: Rote Bete, Eier (Cholin), Brokkoli, Rosenkohl')
    lines += [
        '', '---', '',
        '## Disclaimer', '',
        'Dieser Report wurde durch das Nutrigenomik-Dashboard automatisiert erstellt.',
        'Die Empfehlungen basieren auf wissenschaftlicher Literatur, ersetzen jedoch keine',
        'ärztliche oder pharmazeutische Beratung. Vor Beginn einer Supplementierung sollte',
        'ein Arzt oder Ernährungsmediziner konsultiert werden.',
        '',
    ]
    
    report_text = '\n'.join(lines)
    Path(filename).write_text(report_text, encoding='utf-8')
    return report_text


def generate_llm_prompt(
    risk_profile: Dict,
    methylation_score: Dict,
    supplement_plan: List[Dict],
    blood_results: Optional[List[Dict]],
    profile: Dict,
) -> str:
    """Generate prompt for optional LLM-based health report."""
    lines = [
        'Du bist ein freundlicher, deutschsprachiger Gesundheitsberater mit Fokus auf Nutrigenomik.',
        'Erstelle einen leicht verständlichen, persönlichen Gesundheitsbericht basierend auf folgenden Daten.',
        'Vermeide Panikmache — erkläre sachlich, aber einfühlsam.',
        'Fokussiere auf die 3-5 wichtigsten Handlungsempfehlungen.',
        '',
        '## Personendaten',
        f'- Alter: {profile.get("age", "N/A")} Jahre',
        f'- Gewicht: {profile.get("weight", "N/A")} kg',
        f'- Geschlecht: {profile.get("gender", "N/A")}',
        '',
        '## Genetische Risikoprofile',
    ]
    
    for cat, data in sorted(risk_profile.get('category_scores', {}).items(),
                            key=lambda x: -(x[1]['score'] or 0)):
        lines.append(f'- **{cat}**: Score {data["score"]}/10 ({data.get("category", "?")})')
        for s in data.get('contributing_snps', [])[:2]:
            if s.get('risk_count', 0) > 0:
                lines.append(f'  - {s["gene"]} ({s["rsid"]}): {s["risk_count"]}/2 Risikoallele — {s.get("effect", "")}')
    
    lines += ['', '## Methylierungsstatus',
              f'- Score: {methylation_score.get("score", "N/A")}/10',
              f'- Level: {methylation_score.get("level", "N/A")}',
              f'- {methylation_score.get("interpretation", "")}',
              '', '## Supplement-Empfehlungen']
    
    for s in supplement_plan:
        reasons = '; '.join(s.get('reasons', [])) or s.get('risk_level', '')
        lines.append(f'- **{s["name"]}**: {s["dose_display"]} ({reasons})')
    
    if blood_results:
        lines += ['', '## Blutwerte']
        for b in blood_results:
            lines.append(f'- {b["message"]}')
    
    lines += ['', '', 'Bitte erstelle einen persönlichen Bericht im Markdown-Format.',
              'Titel: "🧬 Mein persönlicher Nutrigenomik-Bericht"',
              'Gliederung: 1) Zusammenfassung 2) Methylierung 3) Stoffwechsel',
              '4) Supplement-Plan 5) Ernährungstipps 6) Nächste Schritte']
    
    return '\n'.join(lines)

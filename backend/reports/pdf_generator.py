"""PDF-Report-Generator — Erstellt PDFs via ReportLab."""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


def generate_pdf_report(
    risk_profile: Dict,
    methylation_score: Dict,
    supplement_plan: List[Dict],
    blood_results: Optional[List[Dict]],
    profile: Dict,
    drug_warnings: Optional[List[Dict]] = None,
    expert_mode: bool = False,
    filename: str = 'nutrigenomik_report.pdf',
) -> str:
    """Generate a styled PDF report with ReportLab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm, cm
        from reportlab.lib.colors import HexColor, black, white
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, HRFlowable, KeepTogether
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    except ImportError:
        raise ImportError('ReportLab benötigt: pip install reportlab')
    
    PRIMARY = HexColor('#2E86AB')
    SECONDARY = HexColor('#A23B72')
    ACCENT = HexColor('#F18F01')
    GREEN = HexColor('#27AE60')
    RED = HexColor('#E74C3C')
    ORANGE = HexColor('#F39C12')
    GRAY = HexColor('#666666')
    LIGHT_GRAY = HexColor('#F0F0F0')
    
    doc = SimpleDocTemplate(
        filename, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm,
        leftMargin=2*cm, rightMargin=2*cm,
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'],
        fontSize=22, textColor=PRIMARY, spaceAfter=4*mm, alignment=TA_CENTER,
        fontName='Helvetica-Bold')
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
        fontSize=10, textColor=GRAY, alignment=TA_CENTER, spaceAfter=10*mm)
    h1 = ParagraphStyle('H1', parent=styles['Heading1'],
        fontSize=14, textColor=PRIMARY, spaceBefore=6*mm, spaceAfter=4*mm,
        fontName='Helvetica-Bold')
    h2 = ParagraphStyle('H2', parent=styles['Heading2'],
        fontSize=12, textColor=SECONDARY, spaceBefore=4*mm, spaceAfter=3*mm,
        fontName='Helvetica-Bold')
    body = ParagraphStyle('Body', parent=styles['Normal'],
        fontSize=9, leading=13, spaceAfter=2*mm, alignment=TA_JUSTIFY)
    body_bold = ParagraphStyle('BodyBold', parent=body, fontName='Helvetica-Bold')
    small = ParagraphStyle('Small', parent=styles['Normal'],
        fontSize=7.5, textColor=GRAY, spaceAfter=1*mm)
    disclaimer = ParagraphStyle('Disclaimer', parent=body,
        fontSize=7.5, textColor=GRAY, fontName='Helvetica-Oblique')
    
    elements = []
    
    # ── Title Page ──────────────────────────────────────────────
    elements.append(Spacer(1, 3*cm))
    mode_label = 'Expertenmodus' if expert_mode else 'Standard'
    elements.append(Paragraph(f'🧬 Nutrigenomik & Supplement Report', title_style))
    elements.append(Paragraph(
        f'{mode_label} | {datetime.now().strftime("%d.%m.%Y %H:%M")}', subtitle_style))
    elements.append(Spacer(1, 5*mm))
    p = profile
    elements.append(Paragraph(
        f'Alter: {p.get("age", "?")} Jahre | Gewicht: {p.get("weight", "?")} kg | '
        f'Geschlecht: {p.get("gender", "?")}', body))
    elements.append(Spacer(1, 3*mm))
    elements.append(HRFlowable(width='100%', color=PRIMARY, thickness=1))
    elements.append(Paragraph(
        'Hinweis: Dieser Report dient zu Bildungszwecken. Er ersetzt keine ärztliche Beratung.',
        disclaimer))
    elements.append(PageBreak())
    
    # ── Executive Summary ───────────────────────────────────────
    elements.append(Paragraph('Zusammenfassung', h1))
    cat_scores = risk_profile.get('category_scores', {})
    
    top = risk_profile.get('top_findings', [])
    if top:
        elements.append(Paragraph('<b>Top-Erkenntnisse:</b>', body_bold))
        for f in top[:5]:
            elements.append(Paragraph(f'• <b>{f["gene"]}</b> — {f["effect"]}', body))
        elements.append(Spacer(1, 3*mm))
    
    meth = methylation_score
    if meth.get('score') is not None:
        elements.append(Paragraph(
            f'<b>Methylierungs-Score:</b> {meth["score"]}/10 — {meth["level"]}', body_bold))
        elements.append(Paragraph(meth['interpretation'], small))
    
    # Score table
    data = [['Kategorie', 'Score', 'Risiko']]
    for cat, d in sorted(cat_scores.items(), key=lambda x: -(x[1]['score'] or 0)):
        score = f'{d["score"]:.1f}/10' if d['score'] is not None else 'N/A'
        cat_lbl = d.get('category', '?')
        data.append([cat, score, cat_lbl])
    
    t = Table(data, colWidths=[100, 60, 60])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CCCCCC')),
        ('ALIGN', (1, 0), (2, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GRAY]),
    ]))
    elements.append(t)
    
    # Methylation details
    if meth.get('details'):
        elements.append(Spacer(1, 4*mm))
        elements.append(Paragraph('Methylierungs-Details', h2))
        m_data = [['Gen', 'rsID', 'Genotyp', 'Risiko', 'Beitrag']]
        for d in meth['details']:
            m_data.append([d['gene'], d['rsid'], d['genotype'],
                          f'{d["risk_count"]}/2', f'{d["contribution"]}'])
        mt = Table(m_data, colWidths=[55, 70, 55, 45, 45])
        mt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), SECONDARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CCCCCC')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_GRAY]),
        ]))
        elements.append(mt)
    
    elements.append(Spacer(1, 5*mm))
    
    # ── Supplement Plan ─────────────────────────────────────────
    elements.append(Paragraph('Personalisierter Supplement-Plan', h1))
    
    for s in supplement_plan:
        risk_color = RED if s['risk_level'] == 'hoch' else ORANGE
        dose_text = f'<b>{s["dose_display"]}</b>'
        reasons = '; '.join(s.get('reasons', [])) or 'Basisempfehlung'
        
        elements.append(Paragraph(
            f'{dose_text} — {s["name"]}', body_bold))
        elements.append(Paragraph(reasons, small))
        
        if s.get('cofactor'):
            elements.append(Paragraph(f'Cofaktor: {s["cofactor"]}', small))
        if s.get('safety'):
            elements.append(Paragraph(f'<font color="red">⚠ {s["safety"]}</font>', small))
        
        # Dose bar
        pct = min(s['dose'] / s['max_daily'] * 100, 100)
        bar_color = GREEN if pct < 50 else ORANGE if pct < 80 else RED
        bar = f'<font color="{bar_color}">{"█" * int(pct/5)}{"░" * (20-int(pct/5))}</font> {s["dose_display"]}'
        elements.append(Paragraph(bar, small))
        elements.append(Spacer(1, 2*mm))
    
    # ── Drug Interactions ───────────────────────────────────────
    if drug_warnings:
        elements.append(PageBreak())
        elements.append(Paragraph('Medikamenten-Interaktionen', h1))
        for dw in drug_warnings:
            icon = {'erhoeht': '🔴', 'verringert': '🟡', 'normal': '🟢', 'kontraindiziert': '⛔'}.get(
                dw.get('severity', ''), '⚪')
            elements.append(Paragraph(
                f'{icon} <b>{dw.get("drug", "")}</b> — {dw.get("gene", "")} ({dw.get("phenotype", "")})',
                body_bold))
            elements.append(Paragraph(dw.get('recommendation', ''), body))
            elements.append(Spacer(1, 2*mm))
    
    # ── Blood Values ────────────────────────────────────────────
    if blood_results:
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph('Blutwerte-Integration', h1))
        for b in blood_results:
            icon = {'optimal': '✅', 'suboptimal': '⚠️', 'niedrig': '🔴',
                   'hoch': '🔴', 'grenzwertig': '🟡', 'unbekannt': '⚪'}
            elements.append(Paragraph(f'{icon.get(b["status"], "⚪")} {b["message"]}', body))
    
    # ── Footer ──────────────────────────────────────────────────
    elements.append(Spacer(1, 1*cm))
    elements.append(HRFlowable(width='100%', color=GRAY, thickness=0.5))
    elements.append(Paragraph(
        'Erstellt mit dem Nutrigenomik & Supplement Dashboard. '
        'Keine medizinische Beratung. Konsultieren Sie bei Gesundheitsfragen einen Arzt.',
        disclaimer))
    
    doc.build(elements)
    return filename

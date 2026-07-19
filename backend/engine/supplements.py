"""Supplement-Empfehlungs-Engine.
Kombiniert genetisches Profil, Blutwerte, Medikation, Alter, Gewicht und Geschlecht
zu personalisierten Supplement-Dosierungen.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

SUPPLEMENT_DB_PATH = Path(__file__).parent.parent / 'data' / 'supplement_db.json'

# Supplement ↔ Medikament Interaktionen
# supplement_id -> [(pattern_oder_alias, effekt, empfehlung, severity)]
# Patterns werden bidirektional gematched gegen drug_check.py-Medikamente
SUPPLEMENT_DRUG_INTERACTIONS = {
    'vitamin_d3_k2': [
        ('Warfarin', 'Vitamin K2 antagonisiert Warfarin — Dosis stabil halten, INR engmaschig kontrollieren', 'INR häufiger messen, K2-Dosis nicht abrupt ändern', 'erhoeht'),
        ('Phenprocoumon', 'Vitamin K2 antagonisiert Phenprocoumon', 'INR häufiger messen', 'erhoeht'),
    ],
    'omega3': [
        ('Warfarin', 'Omega-3 >3 g/Tag erhöht Blutungsneigung bei Antikoagulantien', 'Dosis auf ≤2 g/Tag begrenzen bei Blutverdünnung', 'erhoeht'),
        ('Phenprocoumon', 'Omega-3 >3 g/Tag erhöht Blutungsneigung', 'Dosis auf ≤2 g/Tag begrenzen', 'erhoeht'),
        ('ASS', 'Omega-3 + ASS erhöht Blutungszeit', 'Bei >2 g/Tag auf Blutungszeichen achten', 'verringert'),
        ('Clopidogrel', 'Omega-3 kann anti-thrombotischen Effekt verstärken', 'Blutungsrisiko beachten bei Kombination', 'verringert'),
    ],
    'magnesium': [
        ('Magnesium', 'Magnesium + Mg-haltige Antazida → Hypermagnesiämie-Risiko', 'Nierenfunktion prüfen, Dosis anpassen', 'verringert'),
        ('Schleifendiuretika', 'Furosemid etc. erhöhen Mg-Ausscheidung → Bedarf steigt', 'Mg-Spiegel kontrollieren, Dosis erhöhen (Kompensation)', 'verringert'),
        ('Protonenpumpenhemmer', 'PPI (Omeprazol etc.) reduzieren Mg-Resorption bei Langzeiteinnahme', 'Mg-Bedarf um +50 mg erhöhen bei PPI-Dauertherapie', 'verringert'),
        ('Omeprazol', 'PPI reduzieren Mg-Resorption', 'Mg-Bedarf um +50 mg erhöhen bei PPI-Dauertherapie', 'verringert'),
        ('Pantoprazol', 'PPI reduzieren Mg-Resorption', 'Mg-Bedarf um +50 mg erhöhen bei PPI-Dauertherapie', 'verringert'),
        ('Esomeprazol', 'PPI reduzieren Mg-Resorption', 'Mg-Bedarf um +50 mg erhöhen bei PPI-Dauertherapie', 'verringert'),
        ('Tetracycline', 'Magnesium reduziert Tetracyclin-Resorption → zeitlich trennen', 'Mind. 2h Abstand zu Mg-Einnahme', 'verringert'),
        ('Ciprofloxacin', 'Magnesium reduziert Resorption', 'Mind. 2h Abstand', 'verringert'),
    ],
    'mthfr': [
        ('Methotrexat', '5-MTHF kann MTX-Wirkung abschwächen (Folat-Antagonismus)', 'Nur nach Rücksprache mit behandelndem Arzt', 'erhoeht'),
    ],
    'zink': [
        ('Tetracycline', 'Zink reduziert Tetracyclin-Resorption', 'Mind. 3h Abstand', 'verringert'),
        ('Ciprofloxacin', 'Zink reduziert Resorption', 'Mind. 2h Abstand', 'verringert'),
        ('Penicillamin', 'Zink reduziert Wirkung', 'Rücksprache mit Arzt', 'verringert'),
        ('Thiaziddiuretika', 'Erhöhen Zink-Ausscheidung → Bedarf steigt', 'Zink-Spiegel kontrollieren, +5 mg erwägen', 'verringert'),
    ],
    'selen': [
        ('Cisplatin', 'Cisplatin erhöht Selenverlust → Bedarf steigt', 'Selen-Spiegel kontrollieren', 'verringert'),
    ],
    'coq10': [
        ('Statine', 'Statine senken körpereigenes CoQ10 → Supplement sinnvoll', 'CoQ10 100-200 mg unterstützt mitochondriale Funktion', 'positiv'),
        ('Simvastatin', 'Statine senken CoQ10 → Supplement empfohlen', 'CoQ10 100-200 mg', 'positiv'),
        ('Atorvastatin', 'Statine senken CoQ10 → Supplement empfohlen', 'CoQ10 100-200 mg', 'positiv'),
        ('Warfarin', 'CoQ10 kann Warfarin-Wirkung abschwächen (selten)', 'INR kontrollieren bei Neueinnahme', 'verringert'),
    ],
    'b12': [
        ('Metformin', 'Metformin reduziert B12-Resorption bei Langzeiteinnahme', 'B12-Spiegel kontrollieren, Substitution erwägen', 'verringert'),
        ('Esomeprazol', 'PPI reduzieren B12-Resorption', 'B12-Spiegel kontrollieren', 'verringert'),
        ('Omeprazol', 'PPI reduzieren B12-Resorption', 'B12-Spiegel kontrollieren', 'verringert'),
        ('Pantoprazol', 'PPI reduzieren B12-Resorption', 'B12-Spiegel kontrollieren', 'verringert'),
    ],
}


def load_supplement_db(path: Optional[str] = None) -> List[Dict]:
    """Load supplement database."""
    p = Path(path) if path else SUPPLEMENT_DB_PATH
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def compute_supplement_plan(
    risk_profile: Dict,
    methylation_score: Dict,
    blood_values: Dict[str, Any],
    age: int,
    weight_kg: float,
    gender: str,
    supplement_db: List[Dict],
    drug_warnings: Optional[List[Dict]] = None,
) -> List[Dict]:
    """Generate personalised supplement recommendations.
    
    Args:
        drug_warnings: Ergebnisse aus compute_drug_interactions()
        Nutzt risk_profile['interactions'] fr SNP-SNP-Synergie-Boni
    """
    category_scores = risk_profile.get('category_scores', {})
    interactions = risk_profile.get('interactions', {})  # SNP-Interaktionen
    snp_calls_flat = {}
    for cat_data in category_scores.values():
        for snp in cat_data.get('contributing_snps', []):
            snp_calls_flat[snp['rsid']] = snp
    
    gene_risk_map = _build_gene_risk_map(category_scores)
    
    results = []
    for supp in supplement_db:
        dose = _compute_dose(supp, gene_risk_map, blood_values, weight_kg, age, gender,
                             methylation_score, snp_calls_flat, drug_warnings, interactions)
        if dose is not None:
            results.append(dose)
    
    return sorted(results, key=lambda x: x.get('priority', 5))


def _build_gene_risk_map(category_scores: Dict) -> Dict[str, float]:
    """Build gene -> risk level map (0-1)."""
    gene_map = {}
    for cat_data in category_scores.values():
        for snp in cat_data.get('contributing_snps', []):
            gene = snp['gene']
            risk = snp.get('raw_score', 0)
            if gene not in gene_map or risk > gene_map[gene]:
                gene_map[gene] = risk
    return gene_map


def _has_drug_match(drug_warnings: List[Dict], patterns: List[str]) -> bool:
    """Check if any drug warning matches one of the given patterns."""
    for w in drug_warnings:
        drug = w.get('drug', '').lower()
        for pat in patterns:
            if pat.lower() in drug:
                return True
    return False


def _compute_dose(
    supp: Dict,
    gene_risk_map: Dict[str, float],
    blood_values: Dict[str, Any],
    weight_kg: float,
    age: int,
    gender: str,
    methylation_score: Dict,
    snp_calls_flat: Dict,
    drug_warnings: Optional[List[Dict]] = None,
    interactions: Optional[Dict] = None,
) -> Optional[Dict]:
    """Compute personalised dose for a single supplement.
    Returns None if min_gene_risk threshold is not met (Expert-Modus-Supplements).
    """
    name = supp['name']
    supp_id = supp['id']
    base = supp['base_dose_mg']
    unit = supp['unit']
    max_daily = supp['max_daily_mg']
    min_risk = supp.get('min_gene_risk', 0)
    
    # Prüfe min_gene_risk-Schwelle (für Expert-Modus-Supplements)
    if min_risk > 0:
        max_gene_risk = max([gene_risk_map.get(g, 0) for g in supp.get('genes', [])] + [0])
        if max_gene_risk < min_risk:
            return None  # Wird von compute_supplement_plan gefiltert
    
    dose = float(base)
    reasons = []
    drug_alerts = []
    
    # 1. Genetische Anpassung
    for gene in supp.get('genes', []):
        risk = gene_risk_map.get(gene, 0)
        if risk >= 0.5:
            bonus = supp.get('gene_bonus_mg', 0)
            if bonus and risk >= 0.5:
                dose += bonus * risk
                reasons.append(f'{gene}-Variante: +{int(bonus * risk)} {unit}')
    
    # Spezielle MTHFR-Dosierung für Folat
    if supp['id'] == 'mthfr':
        mthfr_c677t_risk = 0
        mthfr_a1298c_risk = 0
        for rsid, call in snp_calls_flat.items():
            if call.get('gene') == 'MTHFR':
                if call.get('rsid') == 'rs1801133':
                    mthfr_c677t_risk = call.get('risk_count', 0)
                elif call.get('rsid') == 'rs1801131':
                    mthfr_a1298c_risk = call.get('risk_count', 0)
        
        if mthfr_c677t_risk >= 2:  # Homozygot
            dose = 800
            reasons.append('MTHFR C677T homozygot: 800 ug 5-MTHF (aktuelle Leitlinie)')
        elif mthfr_c677t_risk >= 1 or mthfr_a1298c_risk >= 2:
            dose = 400
            reasons.append('MTHFR-Variante: 400 µg 5-MTHF')
    
    # 2. Gewichtsabhängige Anpassung
    weight_factor = supp.get('weight_factor_per_20kg')
    if weight_factor:
        extra = (weight_kg / 20) * weight_factor
        dose += extra
        reasons.append(f'Gewicht ({weight_kg:.0f} kg): +{int(extra)} {unit}')
    
    weight_factor_mg = supp.get('weight_factor_mg_per_kg')
    if weight_factor_mg:
        extra = min(weight_kg * weight_factor_mg, supp.get('weight_max_mg', 999))
        dose += extra
        reasons.append(f'Gewicht ({weight_kg:.0f} kg): +{int(extra)} {unit}')
    
    # 3. Blutwert-basierte Anpassung
    markers = supp.get('blood_markers', {})
    for marker_name, config in markers.items():
        if marker_name in blood_values:
            bv = blood_values[marker_name]
            val = bv.get('value', 0)
            optimal = config.get('optimal', [0, 999])
            if val < optimal[0]:
                multiplier = config.get('low_dose_mult', 1.5)
                dose *= multiplier
                reasons.append(f'{marker_name} niedrig ({val}): ×{multiplier}')
            elif val > optimal[1]:
                multiplier = config.get('high_dose_mult', 0.5)
                dose *= multiplier
                reasons.append(f'{marker_name} optimal ({val}): reduziert')
    
    # 4. Methylierungs-Score für Methylierungs-Supplements
    if supp['category'] == 'methylierung':
        meth_score = methylation_score.get('score', 0)
        if meth_score and meth_score > 5:
            dose *= 1.3
            reasons.append(f'Methylierungs-Score ({meth_score}/10): +30%')
        elif meth_score and meth_score > 7.5:
            dose *= 1.5
            reasons.append(f'Methylierungs-Score ({meth_score}/10): +50%')
    
    # 5. (Entfällt — Altersanpassung erfolgt jetzt supplement-spezifisch in Schritt 9)
    
    # 6. Medikamenten-basierte Anpassung
    if drug_warnings and supp_id in SUPPLEMENT_DRUG_INTERACTIONS:
        supp_drug_interactions = SUPPLEMENT_DRUG_INTERACTIONS[supp_id]
        for drug_pattern, effect, recommendation, severity in supp_drug_interactions:
            pat_lower = drug_pattern.lower()
            for w in drug_warnings:
                drug_name = w.get('drug', '').lower()
                if pat_lower in drug_name or drug_name in pat_lower:
                    drug_alerts.append({
                        'drug': w['drug'],
                        'effect': effect,
                        'recommendation': recommendation,
                        'severity': severity,
                    })
                    if severity == 'erhoeht':
                        dose = min(dose, base)
                        reasons.append(f'⚠ {w["drug"]}: {effect} → Dosis begrenzt')
                    elif severity == 'verringert' and 'erhöhen' in recommendation.lower():
                        dose += base * 0.3
                        reasons.append(f'⚠ {w["drug"]}: {recommendation}')
                    else:
                        reasons.append(f'⚠ {w["drug"]}: {recommendation}')
    
    # 7. SNP-SNP-Interaktions-Synergie (Epistasis) — ENTFERNT aus Dosierung
    # Die Epistasis wird bereits im Risiko-Score und Gene-Bonus berücksichtigt.
    # Eine zusätzliche Multiplikation würde FADS1/FADS2 doppelt bewerten.
    # (Die Interaktionen sind weiterhin im Risikoprofil sichtbar.)
    
    # 8. Geschlechts-spezifische Anpassung
    gender_factors = supp.get('gender_factors', {})
    if gender_factors and gender in gender_factors:
        gf = gender_factors[gender]
        gender_label = {'m': 'Mann', 'w': 'Frau', 'd': 'divers'}.get(gender, gender)
        if gf == 0.0:
            return None
        if gf != 1.0:
            dose *= gf
            reasons.append(f'Geschlecht ({gender_label}): ×{gf:.2f}')
    
    # 9. Alters-basierte Anpassung
    age_adjustments = supp.get('age_adjustments', [])
    if age_adjustments:
        for adj in sorted(age_adjustments, key=lambda x: x['min'], reverse=True):
            if age >= adj['min']:
                dose *= adj['factor']
                reasons.append(f'Alter ({age}): ×{adj["factor"]:.1f} ({adj["reason"]})')
                break
    
    # Dosis begrenzen
    final_dose = min(dose, max_daily)
    if final_dose < dose:
        reasons.append(f'Auf Tageshoechstdosis ({int(max_daily)} {unit}) begrenzt')
    
    # EPA/DHA-Aufteilung fuer Omega-3 ⭐
    epa_dha_display = None
    if supp_id == 'omega3':
        dha_ratio = supp.get('gender_dha_ratio', {}).get(gender, 0.35)
        dha_mg = round(final_dose * dha_ratio)
        epa_mg = round(final_dose - dha_mg)
        epa_dha_display = {'epa': epa_mg, 'dha': dha_mg, 'ratio': dha_ratio}
    
    # Priorität
    max_gene_risk = max([gene_risk_map.get(g, 0) for g in supp.get('genes', [])] + [0])
    has_drug_interaction = len(drug_alerts) > 0
    priority = 1 if has_drug_interaction and any(a['severity'] == 'erhoeht' for a in drug_alerts) else \
               3 if max_gene_risk >= 0.5 else 5
    
    risk_level = 'hoch' if (max_gene_risk >= 0.5 or has_drug_interaction) else \
                 'mittel' if max_gene_risk >= 0.25 else 'niedrig'
    
    return {
        'name': name,
        'id': supp_id,
        'dose': round(final_dose, 0),
        'unit': unit,
        'dose_display': f'{int(round(final_dose, 0))} {unit}',
        'base_dose': base,
        'max_daily': max_daily,
        'priority': priority,
        'risk_level': risk_level,
        'reasons': reasons,
        'drug_alerts': drug_alerts,  # ⭐ NEU
        'form': supp.get('preferred_form', ''),
        'forms': supp.get('forms', []),
        'cofactor': supp.get('cofactor', ''),
        'interactions': supp.get('interactions', []),
        'safety': supp.get('safety', ''),
        'category': supp.get('category', ''),
        'epa_dha': epa_dha_display,
    }

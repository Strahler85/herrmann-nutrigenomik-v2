"""Methylierungs-Score — Gewichteter Index des Methylzyklus.
Optional mit Homocystein-Adjustierung (falls Blutwert vorhanden).
"""
from typing import Dict, Any, List, Optional


def compute_methylation_score(category_scores: Dict[str, Dict],
                               snp_calls: Dict,
                               blood_values: Optional[Dict] = None) -> Dict[str, Any]:
    """Compute comprehensive methylation index.
    
    Fliesst direkt in Supplement-Empfehlungen ein.
    Berücksichtigt: MTHFR, MTR, MTRR, BHMT, PEMT, COMT, CBS
    Wenn Homocystein-Blutwert vorhanden, wird der Score adjustiert.
    """
    methylation_snps = {
        'rs1801133': 0.85,  # MTHFR C677T
        'rs1801131': 0.55,  # MTHFR A1298C
        'rs1805087': 0.50,  # MTR
        'rs1801394': 0.45,  # MTRR
        'rs3733890': 0.35,  # BHMT
        'rs7946':    0.30,  # PEMT
        'rs4680':    0.50,  # COMT
        'rs2253206': 0.40,  # CBS
    }
    
    weighted_sum = 0.0
    max_possible = 0.0
    details = []
    
    for rsid, weight in methylation_snps.items():
        call = snp_calls.get(rsid)
        if call and call['status'] == 'found' and call['risk_count'] is not None:
            from .scoring import snp_raw_score
            raw = snp_raw_score(call['risk_count'])
            weighted_sum += raw * weight
            max_possible += weight
            details.append({
                'rsid': rsid,
                'gene': call['gene'],
                'genotype': call.get('normalised', call['genotype']),
                'risk_count': call['risk_count'],
                'contribution': round(raw * weight, 3),
            })
    
    if max_possible > 0:
        score = round((weighted_sum / max_possible) * 10, 1)
    else:
        score = None
    
    # Homocystein-Adjustierung ⭐
    homocysteine_adjusted = False
    if blood_values:
        hcy = None
        for key in ('homocystein', 'homocysteine', 'hcy'):
            if key in blood_values:
                hcy = blood_values[key].get('value')
                break
        if hcy is not None:
            homocysteine_adjusted = True
            if hcy > 12:
                score = min(score + 2.0, 10) if score else 5.0
            elif hcy > 9:
                score = min(score + 1.0, 10) if score else 4.0
            elif hcy < 5:
                score = max(score - 1.0, 0) if score else 1.0
    
    if score is None:
        level = 'Nicht bestimmbar'
        interpretation = 'Nicht genügend Daten für den Methylierungs-Score.'
    elif score <= 2.5:
        level = 'Optimal'
        interpretation = 'Effizienter Methylzyklus. Standard-Folat-und-B12-Versorgung ausreichend.'
    elif score <= 5.0:
        level = 'Leicht eingeschränkt'
        interpretation = 'Leichte Methylierungseinschränkung. Aktive B-Vitamine (5-MTHF, Methylcobalamin) empfohlen.'
    elif score <= 7.5:
        level = 'Eingeschränkt'
        interpretation = ('Moderate Methylierungseinschränkung. '
                          '5-MTHF (400-800 µg), Methylcobalamin, Betain/Cholin empfohlen. '
                          'Homocystein-Spiegel testen lassen.')
    else:
        level = 'Stark eingeschränkt'
        interpretation = ('Starke Methylierungseinschränkung. '
                          '5-MTHF (800 µg), Methylcobalamin (1000-2000 µg), '
                          'Betain/Cholin und Magnesium dringend empfohlen. '
                          'Homocystein-Kontrolle beim Arzt.')
    
    return {
        'score': score,
        'level': level,
        'interpretation': interpretation,
        'details': details,
        'max_score': 10,
        'homocysteine_adjusted': homocysteine_adjusted,
    }

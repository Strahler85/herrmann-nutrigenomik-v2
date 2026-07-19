"""Expertenmodus — Erweiterte SNP-Abdeckung (500+ SNPs)."""
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Any

EXPERT_PANEL_PATH = Path(__file__).parent.parent / 'data' / 'snp_panel_expert.json'


def load_expert_panel(path: Optional[str] = None) -> List[Dict]:
    """Load the expert SNP panel (500+ SNPs)."""
    p = Path(path) if path else EXPERT_PANEL_PATH
    if not p.exists():
        return []
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def get_expert_subcategories(panel: List[Dict]) -> Dict[str, List[str]]:
    """Get available subcategories from the expert panel."""
    subcats = {}
    for entry in panel:
        cat = entry.get('category', 'allgemein')
        sub = entry.get('subcategory', 'allgemein')
        if cat not in subcats:
            subcats[cat] = []
        if sub not in subcats[cat]:
            subcats[cat].append(sub)
    for cat in subcats:
        subcats[cat].sort()
    return subcats


def filter_expert_panel(
    panel: List[Dict],
    categories: Optional[List[str]] = None,
    subcategories: Optional[List[str]] = None,
    genes: Optional[List[str]] = None,
    min_weight: float = 0.0,
) -> List[Dict]:
    """Filter the expert panel by criteria."""
    results = panel
    if categories:
        results = [e for e in results if e.get('category') in categories]
    if subcategories:
        results = [e for e in results if e.get('subcategory') in subcategories]
    if genes:
        results = [e for e in results if e.get('gene') in genes]
    if min_weight > 0:
        results = [e for e in results if (e.get('weight') or 0) >= min_weight]
    return results


def extract_expert_genotypes(
    genotype_table: Dict[str, str],
    expert_panel: List[Dict],
) -> Dict[str, Dict]:
    """Extract genotypes for the expert panel."""
    COMPLEMENT = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
    
    results = {}
    for snp in expert_panel:
        rsid = snp['rsid']
        risk_allele = snp['risk_allele']
        
        if rsid not in genotype_table:
            results[rsid] = {
                'rsid': rsid, 'gene': snp['gene'],
                'status': 'not_tested', 'genotype': None,
                'risk_allele': risk_allele, 'risk_count': None,
                'category': snp['category'],
                'subcategory': snp.get('subcategory', ''),
            }
            continue
        
        raw = genotype_table[rsid].upper()
        if not raw or len(raw) < 2:
            results[rsid] = {
                'rsid': rsid, 'gene': snp['gene'],
                'status': 'no_call', 'genotype': raw,
                'risk_allele': risk_allele, 'risk_count': None,
                'category': snp['category'],
                'subcategory': snp.get('subcategory', ''),
            }
            continue
        
        norm = raw
        if risk_allele not in raw:
            flipped = ''.join(COMPLEMENT.get(b, b) for b in raw)
            if risk_allele in flipped:
                norm = flipped
        
        risk_count = norm.count(risk_allele)
        results[rsid] = {
            'rsid': rsid, 'gene': snp['gene'],
            'status': 'found', 'genotype': raw, 'normalised': norm,
            'risk_allele': risk_allele, 'risk_count': risk_count,
            'category': snp['category'],
            'subcategory': snp.get('subcategory', ''),
        }
    
    return results


def snp_raw_score(risk_count: int) -> float:
    """Convert risk allele count to a 0–1 dosage score."""
    if risk_count is None:
        return None
    return {0: 0.0, 1: 0.5, 2: 1.0}.get(risk_count, 0.0)


def compute_expert_category_scores(
    snp_calls: Dict,
    expert_panel: List[Dict],
) -> Dict[str, Dict]:
    """Compute category-level risk scores from the expert panel.
    
    Gleiche Logik wie scoring.compute_category_scores(),
    aber mit expert_panel-Struktur (category + subcategory).
    """
    panel_index = {s['rsid']: s for s in expert_panel}
    
    category_snps = defaultdict(list)
    for snp in expert_panel:
        category_snps[snp['category']].append(snp['rsid'])
    
    results = {}
    for category, rsids in category_snps.items():
        weighted_sum = 0.0
        max_possible = 0.0
        contributing = []
        tested = 0
        missing = 0
        
        for rsid in rsids:
            call = snp_calls.get(rsid)
            entry = panel_index[rsid]
            weight = entry.get('weight', 0.5)
            
            if call is None or call['status'] not in ('found',):
                missing += 1
                continue
            
            raw = snp_raw_score(call['risk_count'])
            if raw is None:
                missing += 1
                continue
            
            tested += 1
            weighted_sum += raw * weight
            max_possible += weight
            contributing.append({
                'rsid': rsid,
                'gene': entry['gene'],
                'genotype': call.get('normalised', call['genotype']),
                'risk_count': call['risk_count'],
                'raw_score': raw,
                'weight': weight,
                'effect': entry.get('effect_direction', ''),
                'description': entry.get('description', ''),
                'recommendation': entry.get('recommendation', ''),
            })
        
        if max_possible > 0:
            score = round((weighted_sum / max_possible) * 10, 2)
        elif tested == 0 and missing > 0:
            score = None
        else:
            score = 0.0
        
        if score is None:
            category_label = 'Unbekannt'
        elif score < 3.5:
            category_label = 'Niedrig'
        elif score < 6.5:
            category_label = 'Moderat'
        else:
            category_label = 'Erhöht'
        
        results[category] = {
            'score': score,
            'category': category_label,
            'contributing_snps': contributing,
            'tested_snps': tested,
            'missing_snps': missing,
        }
    
    return results


def merge_risk_profiles(
    standard_scores: Dict[str, Dict],
    expert_scores: Dict[str, Dict],
) -> Dict[str, Dict]:
    """Merge expert category scores into standard scores.
    
    - Neue Kategorien (hormone, herz_kreislauf, knochen_gelenke) werden hinzugefügt
    - Bei überlappenden Kategorien (entgiftung, entzuendung) wird der höhere Score
      aus beiden Panels übernommen (Expert-Panel hat feinere Granularität)
    """
    merged = dict(standard_scores)
    
    for cat, expert_data in expert_scores.items():
        if cat in merged:
            # Überschneidung: nimm Score aus dem Panel mit mehr Test-SNPs
            std = merged[cat]
            if expert_data.get('tested_snps', 0) > std.get('tested_snps', 0):
                merged[cat] = expert_data
            # Sonst Standard belassen
        else:
            # Neue Kategorie aus Expertenpanel
            merged[cat] = expert_data
    
    return merged

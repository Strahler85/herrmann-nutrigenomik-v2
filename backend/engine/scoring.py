"""Scoring-Engine — Genetische Risikoberechnung nach Kategorien.
Inklusive SNP-SNP-Interaktionen (Epistasis).
"""
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Any

SNP_PANEL_PATH = Path(__file__).parent.parent / 'data' / 'snp_panel.json'

# Bekannte SNP-SNP-Interaktionen (Epistasis)
# (gene_a, gene_b, rsid_a, rsid_b, synergy_factor, beschreibung)
# synergy_factor > 1.0 = verstärkend, < 1.0 = abschwächend
SNP_INTERACTIONS = [
    # Methylierung: MTHFR + MTRR + COMT verstärken sich gegenseitig
    ("MTHFR", "MTRR", "rs1801133", "rs1801394", 1.4, 
     "MTHFR C677T + MTRR A66G: Synergistische Homocystein-Erhöhung, 40% hherer Methylierungs-Bedarf"),
    ("MTHFR", "MTR", "rs1801133", "rs1805087", 1.3,
     "MTHFR + MTR: Beide im Folat-Zyklus, kombinierte Reduktion der Methionin-Synthese"),
    ("MTHFR", "COMT", "rs1801133", "rs4680", 1.3,
     "MTHFR C677T + COMT V158M: Erhhte Belastung des Methylgruppen-Pools, hherer Folat-/Magnesium-Bedarf"),
    ("MTRR", "COMT", "rs1801394", "rs4680", 1.2,
     "MTRR + COMT: Reduzierte Methylgruppe-Verfgbarkeit fr Neurotransmitter"),
    ("BHMT", "PEMT", "rs3733890", "rs7946", 1.3,
     "BHMT + PEMT: Cholin/Betain-Stoffwechsel doppelt beeintrchtigt"),

    # Fettstoffwechsel: FADS1 + FADS2 + ELOVL2
    ("FADS1", "FADS2", "rs174546", "rs1535", 1.5,
     "FADS1 + FADS2: Stark reduzierte EPA/DHA-Synthese, 50% hherer Omega-3-Bedarf"),
    ("FADS1", "ELOVL2", "rs174546", "rs953413", 1.3,
     "FADS1 + ELOVL2: DHA-Synthese auf zwei Ebenen gestrt, Algenl-Empfehlung"),
    ("FADS2", "ELOVL2", "rs1535", "rs953413", 1.3,
     "FADS2 + ELOVL2: Omega-3-Verlngerungskaskade doppelt beeintrchtigt"),
    ("APOE", "APOA5", "rs429358", "rs662799", 1.4,
     "APOE4 + APOA5: Erheblich erhhtes LDL/Triglycerid-Risiko, strenge Ditempfehlung"),

    # Vitamin D: VDR + GC
    ("VDR", "GC", "rs2228570", "rs4588", 1.5,
     "VDR FokI + GC: Vitamin-D-Aufnahme UND Transport beeintrchtigt, 50% hherer D3-Bedarf"),
    ("VDR", "GC", "rs731236", "rs7041", 1.3,
     "VDR TaqI + GC: Kombinierte Vitamin-D-Insuffizienz-Wahrscheinlichkeit erhht"),

    # Entgiftung: GSTP1 + SOD2 + CYP1A2
    ("GSTP1", "SOD2", "rs1695", "rs4880", 1.3,
     "GSTP1 + SOD2: Reduzierte Entgiftung UND erhter oxidativer Stress"),
    ("GSTP1", "GPX1", "rs1695", "rs1050450", 1.2,
     "GSTP1 + GPX1: Beide Glutathion-abhngig, kombinierte Reduktion der Entgiftungskapazitt"),
    ("SOD2", "GPX1", "rs4880", "rs1050450", 1.3,
     "SOD2 + GPX1: Antioxidans-Kaskade (SOD produziert H2O2, GPX baut es ab) doppelt beeintrchtigt"),

    # Entzndung: TNF + IL6 + CRP
    ("TNF", "IL6", "rs1800629", "rs1800795", 1.4,
     "TNF-a + IL6: Pro-inflammatorische Zytokine beide erhht, 40% hheres Entzndungsrisiko"),

    # Stoffwechsel: FTO + TCF7L2 + PPARG
    ("FTO", "TCF7L2", "rs9939609", "rs7903146", 1.4,
     "FTO + TCF7L2: Adipositas- UND Diabetes-Risiko kombiniert, strenge Lebensstil-Mannahme"),
    ("PPARG", "ADRB3", "rs1801282", "rs4994", 1.2,
     "PPARG + ADRB3: Reduzierte Fettoxidation UND Lipolyse, erhhtes Gewichtsmanagement-Risiko"),
]


def load_snp_panel(path: Optional[str] = None) -> List[Dict]:
    """Load SNP panel from JSON file."""
    p = Path(path) if path else SNP_PANEL_PATH
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def snp_raw_score(risk_count: int) -> float:
    """Convert risk allele count to a 0-1 dosage score.
    0 copies -> 0.0 (homozygot Referenz)
    1 copy   -> 0.5 (heterozygot)
    2 copies -> 1.0 (homozygot Risiko)
    """
    if risk_count is None:
        return None
    return {0: 0.0, 1: 0.5, 2: 1.0}.get(risk_count, 0.0)


def complement_base(base: str) -> str:
    """Return complement of a single nucleotide base."""
    COMP = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
    return COMP.get(base, base)


def extract_snp_genotypes(genotype_table: Dict[str, str], snp_panel: List[Dict]) -> Dict[str, Dict]:
    """Extract SNP genotypes from parsed data against the panel.
    
    Verbesserte Version mit ref_allele-check vor Strand-Flip.
    Verhindert Fehlklassifikation bei C/G- und A/T-SNPs.
    """
    results = {}
    
    for snp in snp_panel:
        rsid = snp['rsid']
        risk_allele = snp['risk_allele']
        ref_allele = snp.get('ref_allele', '')
        
        if rsid not in genotype_table:
            results[rsid] = {
                'rsid': rsid, 'gene': snp['gene'],
                'status': 'not_tested', 'genotype': None,
                'risk_allele': risk_allele, 'risk_count': None,
                'category': snp['category'],
            }
            continue
        
        raw = genotype_table[rsid].upper()
        if not raw or len(raw) < 2:
            results[rsid] = {
                'rsid': rsid, 'gene': snp['gene'],
                'status': 'no_call', 'genotype': raw,
                'risk_allele': risk_allele, 'risk_count': None,
                'category': snp['category'],
            }
            continue
        
        # 1. Direkter Match: risk_allele in raw Genotyp
        if risk_allele in raw:
            risk_count = raw.count(risk_allele)
            results[rsid] = {
                'rsid': rsid, 'gene': snp['gene'],
                'status': 'found', 'genotype': raw, 'normalised': raw,
                'risk_allele': risk_allele, 'risk_count': risk_count,
                'category': snp['category'],
            }
            continue
        
        # 2. Pruefe ref_allele: entspricht raw dem ref_allele?
        #    Wenn ja: kein Risiko, kein Flip noetig
        if ref_allele:
            ref_comp = complement_base(ref_allele)
            # Pruefe ob raw = ref_allele/ref_allele oder ref_allele/alternativ
            if ref_allele in raw:
                risk_count = raw.count(risk_allele)  # 0 wenn risk nicht in raw
                results[rsid] = {
                    'rsid': rsid, 'gene': snp['gene'],
                    'status': 'found', 'genotype': raw, 'normalised': raw,
                    'risk_allele': risk_allele, 'risk_count': risk_count,
                    'category': snp['category'],
                }
                continue
            # Pruefe ob raw komplementaer zu ref ist (dann strand-flip)
            if ref_comp in raw:
                flipped = ''.join(complement_base(b) for b in raw)
                risk_count = flipped.count(risk_allele)
                results[rsid] = {
                    'rsid': rsid, 'gene': snp['gene'],
                    'status': 'found', 'genotype': raw, 'normalised': flipped,
                    'risk_allele': risk_allele, 'risk_count': risk_count,
                    'category': snp['category'],
                }
                continue
        
        # 3. Fallback: Versuche Strand-Flip (ohne ref_allele)
        flipped = ''.join(complement_base(b) for b in raw)
        if risk_allele in flipped:
            risk_count = flipped.count(risk_allele)
            results[rsid] = {
                'rsid': rsid, 'gene': snp['gene'],
                'status': 'found', 'genotype': raw, 'normalised': flipped,
                'risk_allele': risk_allele, 'risk_count': risk_count,
                'category': snp['category'],
            }
        else:
            # Weder direkt noch geflippt => 0 Risiko
            results[rsid] = {
                'rsid': rsid, 'gene': snp['gene'],
                'status': 'found', 'genotype': raw, 'normalised': raw,
                'risk_allele': risk_allele, 'risk_count': 0,
                'category': snp['category'],
            }
    
    return results


def compute_category_scores(snp_calls: Dict, snp_panel: List[Dict]) -> Dict[str, Dict]:
    """Compute category-level risk scores mit verbesserter Logik.
    
    Verwendet:
    - Additive gewichtete Summe fuer Basisscore (0-10)
    - Diminishing returns bei vielen Risiko-SNPs (log1p-Skalierung)
    - Konfidenzintervall basierend auf tested/missing-Ratio
    - Evidence-basierte Gewichte aus der Literatur
    """
    panel_index = {s['rsid']: s for s in snp_panel}
    
    # Group by category
    category_snps = defaultdict(list)
    for snp in snp_panel:
        category_snps[snp['category']].append(snp['rsid'])
    
    results = {}
    
    for category, rsids in category_snps.items():
        weighted_sum = 0.0
        max_possible = 0.0
        contributing = []
        tested = 0
        missing = 0
        risk_snp_count = 0  # Anzahl der SNPs mit risk_count > 0
        
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
            if call['risk_count'] > 0:
                risk_snp_count += 1
            
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
        
        # ---- Verbesserte Score-Berechnung ----
        if max_possible > 0:
            linear_score = (weighted_sum / max_possible) * 10
            # Diminishing returns: log1p-Skalierung fuer Kategorien mit vielen Risiko-SNPs
            # 1 SNP = linear, 2 SNPs = +80% des linearen, 3+ SNPs = degressiv
            if risk_snp_count >= 2:
                diminishing = 1 + ((risk_snp_count - 1) ** 0.5) / risk_snp_count
                score = round(min(linear_score * diminishing, 10), 2)
            else:
                score = round(linear_score, 2)
        elif tested == 0 and missing > 0:
            score = None
        else:
            score = 0.0
        
        # Konfidenz: je mehr SNPs getestet, desto zuverlaessiger
        total_expected = tested + missing
        if total_expected > 0:
            confidence = round(tested / total_expected * 100, 0)
        else:
            confidence = 0
        
        if score is None:
            category_label = 'Unbekannt'
        elif score < 3.5:
            category_label = 'Niedrig'
        elif score < 6.5:
            category_label = 'Moderat'
        else:
            category_label = 'Erhoeht'
        
        results[category] = {
            'score': score,
            'category': category_label,
            'confidence': confidence,
            'contributing_snps': contributing,
            'tested_snps': tested,
            'missing_snps': missing,
            'risk_snp_count': risk_snp_count,
        }
    
    return results


def compute_snp_interactions(
    snp_calls: Dict,
) -> Dict[str, Any]:
    """Berechne SNP-SNP-Interaktionen (Epistasis).
    
    Prüft alle bekannten Interaktions-Paare auf gleichzeitiges Vorliegen.
    Gibt gefundene Interaktionen + kumulativen Synergie-Score zurück.
    """
    found_interactions = []
    
    for gene_a, gene_b, rsid_a, rsid_b, factor, desc in SNP_INTERACTIONS:
        call_a = snp_calls.get(rsid_a, {})
        call_b = snp_calls.get(rsid_b, {})
        
        risk_a = call_a.get('risk_count', 0) if call_a else 0
        risk_b = call_b.get('risk_count', 0) if call_b else 0
        
        # Beide müssen mindestens heterozygot sein (risk_count >= 1)
        if risk_a and risk_b and risk_a >= 1 and risk_b >= 1:
            min_risk = min(risk_a, risk_b)
            synergy_score = round((factor - 1.0) * 10 * (min_risk / 2), 1)
            found_interactions.append({
                'gene_a': gene_a,
                'gene_b': gene_b,
                'rsid_a': rsid_a,
                'rsid_b': rsid_b,
                'genotype_a': call_a.get('normalised', call_a.get('genotype', '')),
                'genotype_b': call_b.get('normalised', call_b.get('genotype', '')),
                'risk_a': risk_a,
                'risk_b': risk_b,
                'synergy_factor': factor,
                'synergy_score': synergy_score,
                'description': desc,
            })
    
    total_synergy = sum(i['synergy_score'] for i in found_interactions)
    
    return {
        'found_interactions': found_interactions,
        'count': len(found_interactions),
        'total_synergy_score': round(total_synergy, 1),
    }


def compute_risk_profile(snp_calls: Dict, snp_panel: List[Dict]) -> Dict[str, Any]:
    """Compute full risk profile with all scores inkl. SNP-Interaktionen."""
    category_scores = compute_category_scores(snp_calls, snp_panel)
    
    # SNP-Interaktionen berechnen und in Kategorie-Scores einfließen lassen
    interactions = compute_snp_interactions(snp_calls)
    
    # Synergie-Score auf die passenden Kategorien verteilen
    for i in interactions['found_interactions']:
        # Finde die passende Kategorie für diese Interaktion
        for cat_name, cat_data in category_scores.items():
            genes_in_cat = {s['gene'] for s in cat_data.get('contributing_snps', [])}
            if i['gene_a'] in genes_in_cat or i['gene_b'] in genes_in_cat:
                # Synergie-Bonus zur Kategorie addieren
                bonus = i['synergy_score'] * 0.3  # 30% des Synergie-Scores fließt in Kategorie
                if cat_data['score'] is not None:
                    cat_data['score'] = round(min(cat_data['score'] + bonus, 10), 1)
                    if 'interaction_bonus' not in cat_data:
                        cat_data['interaction_bonus'] = 0
                    cat_data['interaction_bonus'] = round(
                        cat_data.get('interaction_bonus', 0) + bonus, 1)
    
    # Per-gene overview
    gene_scores = defaultdict(list)
    for snp in snp_panel:
        rsid = snp['rsid']
        call = snp_calls.get(rsid)
        if call and call['status'] == 'found':
            raw = snp_raw_score(call['risk_count'])
            gene_scores[call['gene']].append({
                'rsid': rsid,
                'genotype': call.get('normalised', call['genotype']),
                'risk_count': call['risk_count'],
                'score': raw * 10,
                'weight': snp.get('weight', 0.5),
                'risk_allele': call['risk_allele'],
            })
    
    # Top findings
    top_findings = []
    for cat, data in sorted(category_scores.items(), key=lambda x: -(x[1]['score'] or 0)):
        if data['score'] and data['score'] >= 5.0:
            for snp in data['contributing_snps'][:3]:
                if snp['risk_count'] and snp['risk_count'] >= 1:
                    top_findings.append({
                        'category': cat,
                        'gene': snp['gene'],
                        'rsid': snp['rsid'],
                        'risk_count': snp['risk_count'],
                        'effect': snp.get('effect', ''),
                        'recommendation': snp.get('recommendation', ''),
                    })
    
    return {
        'category_scores': category_scores,
        'gene_scores': dict(gene_scores),
        'top_findings': top_findings[:5],
        'interactions': interactions,
    }

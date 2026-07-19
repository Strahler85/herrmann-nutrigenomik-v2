"""Mikrobiom-Integration (16S rRNA) — Basiert auf Genus-Ebene-Daten."""
from typing import Dict, List, Optional, Any

# Bakterielle Taxa und ihre gesundheitliche Bedeutung
MICROBIOME_KNOWLEDGE = {
    'Faecalibacterium': {
        'function': 'Butyrat-Produzent, entzuendungshemmend',
        'optimal': (5, 15),
        'unit': '%',
        'low_risk': 'Reduzierte Butyrat-Produktion, erhoehtes Entzuendungsrisiko (IBD, metabolisches Syndrom)',
        'high_risk': 'Selten ueber 20% — kann auf Dysbiose hindeuten',
        'foods': 'Ballaststoffe: Hafer, Leinsamen, Aepfel (Pektin), resistente Staerke (Kartoffeln gekuehlt)',
        'supports': ['Omega-3', 'Butyrat', 'Ballaststoffe', 'Praebiotika'],
    },
    'Akkermansia': {
        'function': 'Mukus-Abbau, Darmbarriere-Schutz',
        'optimal': (1, 5),
        'unit': '%',
        'low_risk': 'Reduzierte Darmbarriere, erhoehtes Risiko fuer Adipositas, Typ-2-Diabetes, NAFLD',
        'high_risk': 'Sehr selten >5% — kann auf Entzuendung hindeuten',
        'foods': 'Polyphenole: Granatapfel, Traubenkerne, Gruener Tee, Preiselbeeren (Cranberrys)',
        'supports': ['Polyphenole', 'Omega-3', 'Metformin'],
    },
    'Lactobacillus': {
        'function': 'Milchsaeure-Produktion, Immunmodulation',
        'optimal': (0.5, 3),
        'unit': '%',
        'low_risk': 'Verminderte Immunabwehr, erhoehtes Risiko fuer Vaginose/Typ-1-Diabetes',
        'high_risk': 'Selten >5%, kann auf Ueberwucherung hindeuten',
        'foods': 'Fermentiertes: Joghurt, Kefir, Sauerkraut, Kimchi, Kombucha',
        'supports': ['Probiotika', 'Praebiotika'],
    },
    'Bifidobacterium': {
        'function': 'Ballaststoff-Abbau, Vitamin-B-Synthese, Immun-Toleranz',
        'optimal': (3, 10),
        'unit': '%',
        'low_risk': 'Verminderte Immun-Toleranz, Allergie-Risiko, verlangsamte Darmpassage',
        'high_risk': 'Selten >15%, oft durch Probiotika-Einnahme',
        'foods': 'Ballaststoffe, Humanmilch-Oligosaccharide (auch pflanzlich: Chicoree, Topinambur)',
        'supports': ['Inulin', 'FOS', 'GOS', 'Ballaststoffe'],
    },
    'Prevotella': {
        'function': 'Pflanzliche Ballaststoffe, Kohlenhydrat-Fermentation',
        'optimal': (5, 20),
        'unit': '%',
        'low_risk': 'Hochverarbeitete Ernaehrung, niedrige Ballaststoffzufuhr',
        'high_risk': '>30%: Assoziiert mit chronischer Entzuendung, rheumatoider Arthritis',
        'foods': 'Pflanzlich-hoch: Vollkorn, Obst, Gemuese, Huelsenfruechte',
        'supports': ['Ballaststoffe', 'Praebiotika'],
    },
    'Bacteroides': {
        'function': 'Hauptfermentierer, Vitamin-K-Produktion',
        'optimal': (15, 35),
        'unit': '%',
        'low_risk': 'Sehr selten <10%, oft bei veganer Ernaehrung (dann Prevotella hoeher)',
        'high_risk': '>40%: Assoziiert mit tierischer-fettreicher Ernaehrung',
        'foods': 'Tierisch: Fleisch, Milchprodukte, Eier (tierische Fette foerdern Bacteroides)',
        'supports': [],
    },
    'Roseburia': {
        'function': 'Butyrat-Produzent, anti-entzuendlich',
        'optimal': (3, 10),
        'unit': '%',
        'low_risk': 'Reduzierte Butyrat-Produktion, assoziiert mit Typ-2-Diabetes, Atherosklerose',
        'high_risk': 'Selten >15%',
        'foods': 'Resistente Staerke (Haferflocken, gruene Bananen, Huelsefruechte), Ballaststoffe',
        'supports': ['Resistente Staerke', 'Ballaststoffe', 'Omega-3'],
    },
    'Escherichia': {
        'function': 'Facultativ anaerob, Vitamin-K2-Produktion, aber auch pathogene Staemme',
        'optimal': (0.1, 1.5),
        'unit': '%',
        'low_risk': 'Selten <0.1% — normal bei gesunder Darmflora',
        'high_risk': '>2%: Moegliche Dysbiose, Entzuendung, IBS. >5%: Aerztlich abklaeren!',
        'foods': 'Keine spezifischen empfohlen. Bei Ueberwucherung: Zucker, Alkohol reduzieren.',
        'supports': [],
    },
    'Christensenella': {
        'function': 'Niedriges BMI-assoziiert, moeglicher Anti-Adipositas-Marker',
        'optimal': (0.1, 1.0),
        'unit': '%',
        'low_risk': 'Assoziiert mit hoeherem BMI und metabolischem Syndrom',
        'high_risk': 'Selten >2%',
        'foods': 'Ballaststoffreiche pflanzliche Ernaehrung, mediterrane Kost',
        'supports': [],
    },
}


def parse_microbiome_csv(filepath: str) -> Dict[str, Any]:
    """Parse microbiome data from CSV (Genus, Abundance)."""
    results = {}
    with open(filepath, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('Genus') or line.startswith('Bacteria'):
                continue
            parts = line.split(',')
            if len(parts) < 2:
                parts = line.split(';')
            if len(parts) < 2:
                continue
            genus = parts[0].strip()
            try:
                abundance = float(parts[1].strip().replace('%', '').replace(',', '.'))
                results[genus] = abundance
            except ValueError:
                continue
    return results


def analyze_microbiome(abundances: Dict[str, float]) -> Dict[str, Any]:
    """Analyze microbiome abundances against reference ranges."""
    findings = []
    total_identified = 0
    imbalances = 0
    
    for genus, pct in abundances.items():
        if genus in MICROBIOME_KNOWLEDGE:
            total_identified += 1
            info = MICROBIOME_KNOWLEDGE[genus]
            optimal = info['optimal']
            
            if pct < optimal[0]:
                imbalances += 1
                findings.append({
                    'genus': genus,
                    'abundance': pct,
                    'status': 'niedrig',
                    'function': info['function'],
                    'risk': info['low_risk'],
                    'foods': info.get('foods', ''),
                    'supports': info.get('supports', []),
                })
            elif pct > optimal[1]:
                imbalances += 1
                findings.append({
                    'genus': genus,
                    'abundance': pct,
                    'status': 'erhoeht',
                    'function': info['function'],
                    'risk': info['high_risk'],
                    'foods': info.get('foods', ''),
                    'supports': info.get('supports', []),
                })
    
    # Probiotika-Empfehlungen basierend auf Defiziten
    probiotics = []
    for f in findings:
        if f['status'] == 'niedrig' and f['supports']:
            for s in f['supports']:
                if s not in probiotics:
                    probiotics.append(s)
    
    return {
        'findings': findings,
        'imbalance_count': imbalances,
        'total_identified': total_identified,
        'probiotics': probiotics[:5],
        'diversity_estimate': min(len(abundances) / 15 * 100, 100) if abundances else 0,
    }

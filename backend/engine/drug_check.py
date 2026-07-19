"""Medikamenten-Interaktions-Check — CYP450 Diplotyping + Dosisanpassung (CPIC/PharmGKB Level A)."""
from typing import Dict, List, Optional


# ── Star-Allele Definitionen (CPIC) ────────────────────────────────
# Jedes Allel ist definiert durch eine Kombination von SNP-Risikokopien
CYP2D6_STAR_ALLELES = {
    '*1':      {'rs3892097': 0, 'rs1065852': 0, 'rs28371725': 0},  # Wildtyp, volle Aktivitaet
    '*4':      {'rs3892097': 2, 'rs1065852': 0, 'rs28371725': 0},  # Splicing-Defekt, null
    '*10':     {'rs3892097': 0, 'rs1065852': 2, 'rs28371725': 0},  # 30% Aktivitaet
    '*41':     {'rs3892097': 0, 'rs1065852': 0, 'rs28371725': 2},  # 50% Aktivitaet
    '*4x10':   {'rs3892097': 2, 'rs1065852': 2, 'rs28371725': 0},  # Compound
    '*4x41':   {'rs3892097': 2, 'rs1065852': 0, 'rs28371725': 2},
    '*10x41':  {'rs3892097': 0, 'rs1065852': 2, 'rs28371725': 2},
}

CYP2C19_STAR_ALLELES = {
    '*1':      {'rs4244285': 0, 'rs4986893': 0, 'rs12248560': 0},  # Wildtyp
    '*2':      {'rs4244285': 2, 'rs4986893': 0, 'rs12248560': 0},  # Splicing-Defekt, null
    '*3':      {'rs4244285': 0, 'rs4986893': 2, 'rs12248560': 0},  # Stop-Codon, null
    '*17':     {'rs4244285': 0, 'rs4986893': 0, 'rs12248560': 2},  # Erhoehte Expression, schnell
}

# Aktivitaets-Score pro Allel (0 = null, 0.5 = reduziert, 1.0 = normal, 2.0 = erhoeht)
CYP2D6_ACTIVITY = {'*1': 1.0, '*4': 0.0, '*10': 0.25, '*41': 0.5, 
                   '*4x10': 0.0, '*4x41': 0.0, '*10x41': 0.25}
CYP2C19_ACTIVITY = {'*1': 1.0, '*2': 0.0, '*3': 0.0, '*17': 2.0}


def determine_2d6_diplotype(snp_calls: Dict) -> tuple:
    """Bestimme CYP2D6-Diplotyp via Activity-Score (CPIC-Methode).
    Returns (label, phenotype, activity_score).
    """
    rs3892097 = snp_calls.get('rs3892097', {}).get('risk_count', 0) or 0  # *4
    rs1065852 = snp_calls.get('rs1065852', {}).get('risk_count', 0) or 0  # *10
    rs28371725 = snp_calls.get('rs28371725', {}).get('risk_count', 0) or 0  # *41
    
    # Aktivitaets-Score pro Allel
    # *1 = 1.0, *4 = 0.0, *10 = 0.25, *41 = 0.5
    # Max 2 Allele, jedes traegt zur Gesamtaktivitaet bei
    
    # Einfache Naeherung: Gesamtrisiko -> Activity Score
    # *4 homozygot: rs3892097=2 -> activity 0
    # *4 heterozygot: rs3892097=1 + *1=1 -> activity 0.5
    score4 = max(0, 2 - rs3892097)  # 2 bei 0, 1 bei 1, 0 bei 2
    score10 = max(0, 2 - rs1065852) * 0.125 + 0.5  # 0.5 bei 0, 0.625 bei 1, 0.75 bei 2? Nein.
    
    # Vereinfacht: Jeder SNP hat unabhaengigen Effekt auf Gesamtaktivitaet
    # *4 (rs3892097): -1.0 pro Risikoallel
    # *10 (rs1065852): -0.375 pro Risikoallel  
    # *41 (rs28371725): -0.25 pro Risikoallel
    activity = 2.0  # Start mit 2 Wildtyp-Allelen
    activity -= rs3892097 * 1.0   # *4: null-Aktivitaet (-1.0 pro Allel)
    activity -= rs1065852 * 0.75  # *10: 25% Aktivitaet (-0.75 pro Allel)
    activity -= rs28371725 * 0.5  # *41: 50% Aktivitaet (-0.5 pro Allel)
    activity = max(0, activity)
    
    # Bestimme Phaenotyp + Label
    if activity == 0:
        pheno = 'langsam (PM)'
        label = '*4/*4 (oder *4/*5)'
    elif activity <= 0.75:
        pheno = 'intermediaer (IM)'
        if rs3892097 == 1 and rs28371725 == 1:
            label = '*4/*41 (IM)'
        elif rs3892097 == 1:
            label = '*4/*1 (IM)'
        elif rs1065852 >= 1 and rs28371725 >= 1:
            label = '*10/*41 (IM)'
        else:
            label = '*10/*1 (IM)'
    elif activity <= 2.25:
        pheno = 'normal (EM)'
        if rs3892097 == 1:
            label = '*4/*1 (EM)'
        elif rs28371725 >= 1:
            label = '*41/*1 (EM)'
        else:
            label = '*1/*1 (EM)'
    else:
        pheno = 'schnell (UM)'
        label = '*1/*1xN (UM)'
    
    return label, pheno, round(activity, 2)


def determine_2c19_diplotype(snp_calls: Dict) -> tuple:
    """Bestimme CYP2C19-Diplotyp via Activity-Score."""
    rs4244285 = snp_calls.get('rs4244285', {}).get('risk_count', 0) or 0  # *2
    rs4986893 = snp_calls.get('rs4986893', {}).get('risk_count', 0) or 0  # *3
    rs12248560 = snp_calls.get('rs12248560', {}).get('risk_count', 0) or 0  # *17
    
    activity = 2.0
    activity -= rs4244285 * 1.0  # *2: null-Aktivitaet (-1.0 pro Allel)
    activity -= rs4986893 * 1.0  # *3: null-Aktivitaet (-1.0 pro Allel)
    activity += rs12248560 * 0.5  # *17: erhoehte Expression (+0.5 pro Allel)
    activity = max(0, activity)
    
    if activity == 0:
        pheno = 'langsam (PM)'
        label = '*2/*2 (oder *2/*3)' if rs4244285 > 0 else '*3/*3 (PM)'
    elif activity <= 1.25:
        pheno = 'intermediaer (IM)'
        label = '*1/*2 (IM)'
    elif activity <= 2.5:
        pheno = 'normal (EM)'
        label = '*1/*1 (EM)' if rs12248560 == 0 else '*1/*17 (schnell-EM)'
    else:
        pheno = 'schnell (UM)'
        label = '*17/*17 (UM)'
    
    return label, pheno, round(activity, 2)


# ── CPIC-Dosisempfehlungen (Level A) ──────────────────────────────
CPIC_DOSING = {
    'CYP2D6': {
        'langsam (PM)': {
            'Codein': 'KONTRAINDIZIERT: Keine Aktivierung zu Morphin. Alternative: Morphin, Nicht-Opioid.',
            'Tramadol': 'KONTRAINDIZIERT: Keine ausreichende Analgesie. Alternative: Nicht-Opioid.',
            'Tamoxifen': 'ALTERNATIVE: Stark reduziertes Endoxifen. Aromatasehemmer oder Fulvestrant erwaegen (CPIC Level A).',
            'Metoprolol': 'DOSISANPASSUNG: -75% Startdosis (2.5 mg/Tag). Beta-Blocker-Effekt verstaerkt.',
            'Amitriptylin': 'DOSISANPASSUNG: -50% Startdosis (25 mg). Spiegel kontrollieren.',
            'Fluoxetin': 'DOSISANPASSUNG: -50%. Lange HWZ beachten (4-6 Tage + Norfluoxetin).',
            'Paroxetin': 'DOSISANPASSUNG: -50%. Stark erhoehte Spiegel bei PM.',
            'Risperidon': 'DOSISANPASSUNG: -50%. Erhoehte Nebenwirkungsrate.',
        },
        'intermediaer (IM)': {
            'Codein': 'VORSICHT: Eingeschraenkte Aktivierung. Bei unzureichender Wirkung wechseln.',
            'Tamoxifen': 'VORSICHT: Reduziertes Endoxifen. Bei hohem Risiko Alternative erwaegen.',
            'Metoprolol': 'DOSISANPASSUNG: -25% Startdosis erwaehren.',
            'Amitriptylin': 'Beobachtung: Normale Startdosis, Spiegel nach 2 Wochen.',
        },
        'schnell (UM)': {
            'Codein': 'VORSICHT: Erhoehte Morphin-Bildung (Ueberdosierungs-Risiko!). Niedrigste Dosis.',
            'Tramadol': 'VORSICHT: Staerkere Opioid-Wirkung. Reduzierte Dosis.',
            'Metoprolol': 'DOSISANPASSUNG: +100% oder Alternative (Atenolol, Bisoprolol).',
            'Amitriptylin': 'DOSISANPASSUNG: +50%. Haefig subtherapeutische Spiegel.',
        },
    },
    'CYP2C19': {
        'langsam (PM)': {
            'Clopidogrel': 'ALTERNATIVE: Prasugrel oder Ticagrelor (CPIC Level A!). Keine prodrug-Aktivierung.',
            'Omeprazol': 'VORSICHT: 5-7x erhoehte AUC. Dosis -50% oder auf Pantoprazol wechseln.',
            'Pantoprazol': 'VORSICHT: 2-3x erhoehte AUC. Dosisreduktion -30% erwaegen.',
            'Citalopram': 'DOSISANPASSUNG: Max 20 mg/Tag (QT-Verlangerungs-Risiko bei erhoehtem Spiegel).',
        },
        'schnell (UM)': {
            'Clopidogrel': 'VORSICHT: Erhoehte Aktivierung (Blutungsrisiko). Normale Dosis, aber beobachten.',
            'Omeprazol': 'INFO: Verminderte Wirkung. Dosis erhoehen oder anderen PPI erwaegen.',
        },
    },
    'CYP2C9': {
        'langsam': {
            'Warfarin': 'DOSISANPASSUNG: Start -50% (2.5 mg). INR engmaschig. CPIC Level A.',
            'Phenprocoumon': 'DOSISANPASSUNG: Start -50%. VKORC1 ebenfalls beruecksichtigen.',
            'Celecoxib': 'VORSICHT: Erhoehte Spiegel. Niedrigste Dosis (100 mg).',
        },
        'intermediaer': {
            'Warfarin': 'DOSISANPASSUNG: Start -30% (3 mg). INR nach 3 Tagen.',
        },
    },
    'SLCO1B1': {
        'niedrig': {
            'Simvastatin': 'ALTERNATIVE: Max 20 mg. Rosuvastatin oder Pitavastatin bevorzugen (CPIC Level A).',
        },
    },
    'TPMT': {
        'langsam': {
            'Azathioprin': 'DOSISANPASSUNG: -90% (max 25 mg/Woche!) oder Alternative. CPIC Level A.',
            '6-Mercaptopurin': 'DOSISANPASSUNG: -90% oder Alternative. CPIC Level A.',
        },
        'intermediaer': {
            'Azathioprin': 'DOSISANPASSUNG: -50% Startdosis. Blutbild nach 2 Wochen.',
        },
    },
    'DPYD': {
        'langsam': {
            'Fluorouracil': 'KONTRAINDIZIERT: Hochrisiko fuer schwere Toxizitaet. Dosis -50% oder Alternative.',
            'Capecitabin': 'KONTRAINDIZIERT: Dosis -50%. Erhoehtes Risiko fuer Mukositis, Neutropenie.',
        },
    },
}


def get_standard_phenotype() -> Dict[str, str]:
    """Return default CYP phenotypes."""
    return {g: 'normal' for g in [
        'CYP2D6', 'CYP2C19', 'CYP2C9', 'CYP3A4', 'CYP1A2', 'CYP2B6',
        'DPYD', 'TPMT', 'NUDT15', 'VKORC1', 'SLCO1B1',
    ]}


def infer_phenotypes(snp_calls: Dict) -> Dict[str, str]:
    """Infer CYP phenotypes from SNP data — mit Star-Allele Diplotyping."""
    pheno = get_standard_phenotype()
    
    # ── CYP2D6 Star-Allele Diplotyping ⭐ ──
    d2_label, d2_pheno, d2_score = determine_2d6_diplotype(snp_calls)
    pheno['CYP2D6'] = d2_pheno
    pheno['CYP2D6_diplotype'] = d2_label
    pheno['CYP2D6_score'] = str(d2_score)
    
    # ── CYP2C19 Star-Allele Diplotyping ⭐ ──
    c19_label, c19_pheno, c19_score = determine_2c19_diplotype(snp_calls)
    pheno['CYP2C19'] = c19_pheno
    pheno['CYP2C19_diplotype'] = c19_label
    pheno['CYP2C19_score'] = str(c19_score)
    
    # CYP1A2
    call = snp_calls.get('rs762551', {})
    rc = call.get('risk_count') if call else None
    if rc == 2: pheno['CYP1A2'] = 'langsam'
    elif rc == 1: pheno['CYP1A2'] = 'intermediaer'
    elif rc == 0: pheno['CYP1A2'] = 'schnell'
    
    # CYP2C9
    risk = 0
    for rsid in ['rs1799853', 'rs1057910']:
        c = snp_calls.get(rsid, {})
        if c and c.get('risk_count'):
            risk += c['risk_count']
    if risk >= 3: pheno['CYP2C9'] = 'langsam'
    elif risk >= 1: pheno['CYP2C9'] = 'intermediaer'
    
    # VKORC1
    call = snp_calls.get('rs9923231', {})
    if call and call.get('risk_count'):
        pheno['VKORC1'] = 'empfindlich' if call['risk_count'] == 2 else 'intermediaer'
    
    # SLCO1B1
    call = snp_calls.get('rs4149056', {})
    if call and call.get('risk_count'):
        pheno['SLCO1B1'] = 'niedrig' if call['risk_count'] == 2 else 'intermediaer'
    
    # TPMT
    tpmt_risk = sum(snp_calls.get(rsid, {}).get('risk_count', 0) or 0
                    for rsid in ['rs1800460', 'rs1142345', 'rs1800462'])
    if tpmt_risk >= 2: pheno['TPMT'] = 'langsam'
    elif tpmt_risk >= 1: pheno['TPMT'] = 'intermediaer'
    
    return pheno


# Wirkstoff-Datenbank
DRUG_DATABASE = {
    'Omeprazol': {'gene': 'CYP2C19', 'details': 'Wird ueber CYP2C19 metabolisiert'},
    'Pantoprazol': {'gene': 'CYP2C19', 'details': 'Wird ueber CYP2C19 metabolisiert (weniger betroffen)'},
    'Esomeprazol': {'gene': 'CYP2C19', 'details': 'Wird ueber CYP2C19 metabolisiert'},
    'Clopidogrel': {'gene': 'CYP2C19', 'details': 'Prodrug — benoetigt CYP2C19 zur Aktivierung'},
    'Citalopram': {'gene': 'CYP2C19', 'details': 'Wird ueber CYP2C19 metabolisiert'},
    'Warfarin': {'gene': 'CYP2C9', 'details': 'Wird ueber CYP2C9 abgebaut', 'secondary_gene': 'VKORC1'},
    'Phenprocoumon': {'gene': 'CYP2C9', 'details': 'Wird ueber CYP2C9 abgebaut', 'secondary_gene': 'VKORC1'},
    'Metoprolol': {'gene': 'CYP2D6', 'details': 'Wird ueber CYP2D6 abgebaut'},
    'Amitriptylin': {'gene': 'CYP2D6', 'details': 'Wird ueber CYP2D6 abgebaut'},
    'Codein': {'gene': 'CYP2D6', 'details': 'Prodrug — benoetigt CYP2D6 zur Aktivierung zu Morphin'},
    'Tramadol': {'gene': 'CYP2D6', 'details': 'Teilweise via CYP2D6 aktiviert'},
    'Tamoxifen': {'gene': 'CYP2D6', 'details': 'Prodrug — benoetigt CYP2D6 fuer Endoxifen'},
    'Simvastatin': {'gene': 'SLCO1B1', 'details': 'Transport via OATP1B1; Myopathie-Risiko'},
    'Azathioprin': {'gene': 'TPMT', 'details': 'Prodrug — TPMT-Mangel erhoeht Myelotoxizitaet'},
    '6-Mercaptopurin': {'gene': 'TPMT', 'details': 'TPMT-Mangel erhoeht Toxizitaet'},
    'Fluorouracil': {'gene': 'DPYD', 'details': 'DPYD-Mangel: schwere Toxizitaet'},
    'Koffein': {'gene': 'CYP1A2', 'details': 'Wird ueber CYP1A2 abgebaut', 'category': 'genussmittel'},
    'Theophyllin': {'gene': 'CYP1A2', 'details': 'Wird ueber CYP1A2 abgebaut'},
    'Clozapin': {'gene': 'CYP1A2', 'details': 'Schmaler Index, CYP1A2-abhaengig'},
}


def compute_drug_interactions(
    phenotypes: Dict[str, str],
    drug_names: Optional[List[str]] = None,
    snp_calls: Optional[Dict] = None,
) -> List[Dict]:
    """Check drug-gene interactions mit CPIC-Dosisanpassung."""
    if snp_calls and not phenotypes:
        phenotypes = infer_phenotypes(snp_calls)
    elif not phenotypes:
        phenotypes = get_standard_phenotype()
    
    warnings = []
    targets = {k: v for k, v in DRUG_DATABASE.items() if drug_names is None or k in drug_names}
    
    for drug, info in targets.items():
        gene = info['gene']
        phenotype = phenotypes.get(gene, 'normal')
        
        if phenotype == 'normal' or 'normal' in str(phenotype):
            continue
        
        severity = 'normal'
        recommendation = ''
        dose_adjustment = ''
        
        # Hole CPIC-Empfehlung falls vorhanden
        if gene in CPIC_DOSING and phenotype in CPIC_DOSING[gene]:
            drug_recs = CPIC_DOSING[gene][phenotype]
            best_key = next((k for k in drug_recs if k.lower() in drug.lower()[:10]), None)
            if best_key:
                rec = drug_recs[best_key]
                if rec.startswith('DOSISANPASSUNG:'):
                    severity = 'erhoeht'
                    dose_adjustment = rec.replace('DOSISANPASSUNG:', '').strip()
                    recommendation = f'🟡 {dose_adjustment}'
                elif rec.startswith('ALTERNATIVE:'):
                    severity = 'erhoeht'
                    recommendation = f'🔴 {rec.replace("ALTERNATIVE:", "").strip()}'
                elif rec.startswith('KONTRAINDIZIERT:'):
                    severity = 'kontraindiziert'
                    recommendation = f'⛔ {rec.replace("KONTRAINDIZIERT:", "").strip()}'
                else:
                    severity = 'verringert'
                    recommendation = f'🟡 {rec}'
            else:
                # Fallback: generische Empfehlung
                severity = 'verringert'
                recommendation = f'🟡 {phenotype}-Phaenotyp. Dosisanpassung erwaegen.'
        
        # Fallback fuer nicht in CPIC_DOSING
        if not recommendation:
            if 'langsam' in phenotype:
                severity = 'verringert'
                recommendation = f'🟡 {phenotype}: Verlangsamter Abbau. Dosis um 30-50% reduzieren.'
            elif 'schnell' in phenotype:
                severity = 'verringert'
                recommendation = f'🟡 {phenotype}: Beschleunigter Abbau. Dosis um 50-100% erhoehen.'
        
        if severity not in ('normal',):
            w = {
                'drug': drug,
                'gene': gene,
                'phenotype': phenotype,
                'severity': severity,
                'details': info.get('details', ''),
                'secondary_gene': info.get('secondary_gene', ''),
                'recommendation': recommendation,
                'category': info.get('category', 'medikament'),
            }
            # Diplotype-Info fuer CYP2D6/2C19
            for key in ['CYP2D6_diplotype', 'CYP2D6_score', 'CYP2C19_diplotype', 'CYP2C19_score']:
                if key in phenotypes and gene in key:
                    w['diplotype'] = phenotypes[key]
            if dose_adjustment:
                w['dose_adjustment'] = dose_adjustment
            warnings.append(w)
    
    return sorted(warnings, key=lambda x: (
        {'kontraindiziert': 0, 'erhoeht': 1, 'verringert': 2}.get(x['severity'], 3),
        x['drug'],
    ))

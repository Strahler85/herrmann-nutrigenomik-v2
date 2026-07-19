"""DNA-Rohdaten-Parser: 23andMe, AncestryDNA, VCF."""
import csv
import re
import gzip
from pathlib import Path
from typing import Dict, Optional


def detect_format(filepath: str) -> str:
    """Auto-detect genetic file format from header/content."""
    try:
        open_func = gzip.open if filepath.endswith('.gz') else open
        mode = 'rt' if filepath.endswith('.gz') else 'r'
        with open_func(filepath, mode, encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line.startswith('##fileformat=VCF'):
                    return 'vcf'
                if '# rsid' in line.lower() or ('rsid' in line.lower()
                   and 'chromosome' in line.lower() and 'genotype' in line.lower()):
                    return '23andme'
                if 'rsid' in line.lower() and 'allele1' in line.lower():
                    return 'ancestry'
                if not line.startswith('#'):
                    break
    except Exception:
        pass
    ext = Path(filepath).suffix.lower()
    if ext == '.vcf' or filepath.endswith('.vcf.gz'):
        return 'vcf'
    if ext == '.csv':
        return 'ancestry'
    return '23andme'


def parse_23andme(filepath: str) -> Dict[str, str]:
    """Parse 23andMe raw data file. Returns {rsid: genotype}."""
    genotypes = {}
    open_func = gzip.open if filepath.endswith('.gz') else open
    mode = 'rt' if filepath.endswith('.gz') else 'r'
    with open_func(filepath, mode, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 4:
                continue
            rsid, genotype = parts[0], parts[3]
            if rsid.startswith('rs'):
                genotypes[rsid] = genotype.replace('-', '').replace('?', '')
    return genotypes


def parse_ancestry(filepath: str) -> Dict[str, str]:
    """Parse AncestryDNA raw data file. Returns {rsid: genotype}."""
    genotypes = {}
    lines = []
    with open(filepath, encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.startswith('#'):
                lines.append(line)
    reader = csv.DictReader(lines, delimiter='\t')
    for row in reader:
        rsid = row.get('rsid', '').strip()
        allele1 = row.get('allele1', '').strip()
        allele2 = row.get('allele2', '').strip()
        if rsid.startswith('rs') and allele1 and allele2:
            genotypes[rsid] = (allele1 + allele2).replace('-', '')
    return genotypes


def parse_vcf(filepath: str) -> Dict[str, str]:
    """Parse VCF file, extracting GT field. Returns {rsid: genotype_bases}."""
    genotypes = {}
    open_func = gzip.open if filepath.endswith('.gz') else open
    mode = 'rt' if filepath.endswith('.gz') else 'r'
    with open_func(filepath, mode, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.startswith('##'):
                continue
            if line.startswith('#CHROM'):
                continue
            parts = line.split('\t')
            if len(parts) < 10:
                continue
            rsid = parts[2]
            if not rsid.startswith('rs'):
                continue
            ref = parts[3]
            alts = parts[4].split(',')
            alleles = [ref] + alts
            fmt = parts[8].split(':')
            try:
                gt_idx = fmt.index('GT') if 'GT' in fmt else 0
            except ValueError:
                gt_idx = 0
            sample = parts[9].split(':')[gt_idx]
            indices = re.split(r'[|/]', sample)
            try:
                called = ''.join(alleles[int(i)] for i in indices if i != '.')
                genotypes[rsid] = called
            except (IndexError, ValueError):
                pass
    return genotypes


def parse_genetic_file(filepath: str, fmt: str = 'auto') -> Dict[str, str]:
    """Parse genetic data file in any supported format."""
    if fmt == 'auto':
        fmt = detect_format(filepath)
    parsers = {
        '23andme': parse_23andme,
        'ancestry': parse_ancestry,
        'vcf': parse_vcf,
    }
    if fmt not in parsers:
        raise ValueError(f'Unknown format: {fmt}. Choose from: {list(parsers.keys())}')
    return parsers[fmt](filepath)

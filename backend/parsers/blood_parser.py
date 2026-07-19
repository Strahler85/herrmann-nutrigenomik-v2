"""Blutwerte-Parser: CSV/Excel mit Biomarkern."""
import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Any


def parse_blood_values(filepath: str) -> Dict[str, Any]:
    """Parse blood values from CSV/Excel file.
    
    Erwartetes Format (CSV): biomarker, value, unit, date
    Oder: Biomarker, Ergebnis, Einheit, Referenzbereich
    
    Returns dict with biomarker name -> {value, unit, reference_range, date}
    """
    ext = Path(filepath).suffix.lower()
    if ext in ('.xlsx', '.xls'):
        return _parse_excel(filepath)
    return _parse_csv(filepath)


def _parse_csv(filepath: str) -> Dict[str, Any]:
    """Parse CSV blood values."""
    results = {}
    with open(filepath, encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # Try different delimiters
    for delimiter in [';', ',', '\t']:
        if delimiter in content:
            break
    
    reader = csv.DictReader(content.splitlines(), delimiter=delimiter)
    
    # Normalize column names
    col_map = {}
    for row in reader:
        if not col_map:
            col_map = _normalize_columns(row.keys())
        
        name = _get_col(row, col_map, ['biomarker', 'parameter', 'name', 'bezeichnung', 'biomarker'])
        if not name:
            continue
        
        value = _get_col(row, col_map, ['value', 'ergebnis', 'wert', 'result', 'concentration'])
        unit = _get_col(row, col_map, ['unit', 'einheit', 'maßeinheit'])
        ref = _get_col(row, col_map, ['reference', 'referenz', 'referenzbereich', 'range', 'normal'])
        date = _get_col(row, col_map, ['date', 'datum', 'date_of_test'])
        
        try:
            val = float(value.replace(',', '.').replace('<', '').replace('>', '').strip())
        except (ValueError, AttributeError):
            continue
        
        results[name.strip().lower()] = {
            'value': val,
            'raw': value.strip(),
            'unit': unit.strip() if unit else '',
            'reference': ref.strip() if ref else '',
            'date': date.strip() if date else '',
        }
    
    return results


def _parse_excel(filepath: str) -> Dict[str, Any]:
    """Parse Excel blood values (fallback)."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(filepath, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        headers = [str(h).lower() if h else '' for h in rows[0]]
        results = {}
        for row in rows[1:]:
            if not row or not row[0]:
                continue
            name = str(row[0]).strip().lower()
            try:
                val = float(str(row[1]).replace(',', '.').replace('<', '').strip())
            except (ValueError, IndexError, AttributeError):
                continue
            results[name] = {
                'value': val,
                'raw': str(row[1]) if len(row) > 1 else '',
                'unit': str(row[2]).strip() if len(row) > 2 else '',
                'reference': str(row[3]).strip() if len(row) > 3 else '',
                'date': str(row[4]).strip() if len(row) > 4 else '',
            }
        return results
    except ImportError:
        raise ImportError('openpyxl benötigt für Excel-Dateien. pip install openpyxl')
    except Exception as e:
        raise ValueError(f'Fehler beim Lesen der Excel-Datei: {e}')


def _normalize_columns(cols: List[str]) -> Dict[str, str]:
    """Map various column names to standard keys."""
    mapping = {}
    for col in cols:
        cl = col.strip().lower()
        orig = col.strip()
        if cl in ('biomarker', 'parameter', 'name', 'bezeichnung', 'test'):
            mapping['biomarker'] = orig
        elif cl in ('value', 'ergebnis', 'wert', 'result', 'concentration', 'konzentration'):
            mapping['value'] = orig
        elif cl in ('unit', 'einheit', 'maßeinheit'):
            mapping['unit'] = orig
        elif cl in ('reference', 'referenz', 'referenzbereich', 'range', 'normal', 'normalbereich'):
            mapping['reference'] = orig
        elif cl in ('date', 'datum', 'date_of_test', 'test_datum'):
            mapping['date'] = orig
    return mapping


def _get_col(row: Dict, col_map: Dict, keys: List[str]) -> Optional[str]:
    """Get column value by any of the given keys."""
    for key in keys:
        if key in col_map:
            return row.get(col_map[key], '')
    return None


# Referenzbereiche für häufige Biomarker
REFERENCE_RANGES = {
    'homocystein': {'unit': 'µmol/l', 'low': 5, 'optimal': (5, 9), 'high': 12},
    'vitamin d (25-oh)': {'unit': 'ng/ml', 'low': 20, 'optimal': (30, 60), 'high': 100},
    'vitamin b12': {'unit': 'pg/ml', 'low': 200, 'optimal': (400, 900), 'high': 1200},
    'ferritin': {'unit': 'ng/ml', 'low': 30, 'optimal': (50, 150), 'high': 300},
    'crp': {'unit': 'mg/l', 'low': 0, 'optimal': (0, 1), 'high': 3},
    'hs-crp': {'unit': 'mg/l', 'low': 0, 'optimal': (0, 1), 'high': 3},
    'magnesium': {'unit': 'mmol/l', 'low': 0.75, 'optimal': (0.85, 1.10), 'high': 1.2},
    'omega-3-index': {'unit': '%', 'low': 4, 'optimal': (8, 12), 'high': 15},
    'zink': {'unit': 'µg/l', 'low': 700, 'optimal': (800, 1200), 'high': 1500},
    'selen': {'unit': 'µg/l', 'low': 70, 'optimal': (80, 120), 'high': 150},
    'glucose': {'unit': 'mg/dl', 'low': 60, 'optimal': (70, 100), 'high': 110},
    'hba1c': {'unit': '%', 'low': 4, 'optimal': (4.5, 5.6), 'high': 6.0},
    'tsh': {'unit': 'mU/l', 'low': 0.3, 'optimal': (0.5, 2.5), 'high': 4.0},
    'cortisol': {'unit': 'µg/dl', 'low': 5, 'optimal': (6, 23), 'high': 25},
    'ldl-cholesterin': {'unit': 'mg/dl', 'low': 50, 'optimal': (60, 130), 'high': 160},
    'hdl-cholesterin': {'unit': 'mg/dl', 'low': 35, 'optimal': (45, 80), 'high': 100},
    'gesamt-cholesterin': {'unit': 'mg/dl', 'low': 120, 'optimal': (130, 200), 'high': 240},
    'triglyceride': {'unit': 'mg/dl', 'low': 50, 'optimal': (50, 150), 'high': 200},
    'kreatinin': {'unit': 'mg/dl', 'low': 0.5, 'optimal': (0.7, 1.2), 'high': 1.4},
    'gfr': {'unit': 'ml/min', 'low': 60, 'optimal': (90, 120), 'high': 150},
    'gpt (alt)': {'unit': 'U/l', 'low': 5, 'optimal': (10, 35), 'high': 50},
    'got (ast)': {'unit': 'U/l', 'low': 5, 'optimal': (10, 35), 'high': 50},
    'gamma-gt': {'unit': 'U/l', 'low': 5, 'optimal': (10, 40), 'high': 60},
    'eisen': {'unit': 'µg/dl', 'low': 40, 'optimal': (60, 160), 'high': 200},
    'transferrin-sättigung': {'unit': '%', 'low': 16, 'optimal': (20, 45), 'high': 50},
    'harnstoff': {'unit': 'mg/dl', 'low': 10, 'optimal': (15, 45), 'high': 55},
    'harnsäure': {'unit': 'mg/dl', 'low': 2.5, 'optimal': (3.5, 7.0), 'high': 8.0},
    'calcium': {'unit': 'mmol/l', 'low': 2.1, 'optimal': (2.2, 2.6), 'high': 2.7},
    'natrium': {'unit': 'mmol/l', 'low': 135, 'optimal': (136, 145), 'high': 148},
    'kalium': {'unit': 'mmol/l', 'low': 3.5, 'optimal': (3.6, 5.0), 'high': 5.2},
    'leukozyten': {'unit': 'G/l', 'low': 4, 'optimal': (4.5, 10.5), 'high': 12},
    'hämoglobin': {'unit': 'g/dl', 'low': 12, 'optimal': (13, 17), 'high': 18},
    'thrombozyten': {'unit': 'G/l', 'low': 150, 'optimal': (180, 360), 'high': 400},
    'homocystein': {'unit': 'µmol/l', 'low': 5, 'optimal': (5, 9), 'high': 12},
    'vitamin b6': {'unit': 'µg/l', 'low': 5, 'optimal': (10, 30), 'high': 50},
    'coq10': {'unit': 'mg/l', 'low': 0.5, 'optimal': (0.7, 1.5), 'high': 2.0},
}


def evaluate_biomarker(name: str, value: float) -> Dict[str, Any]:
    """Evaluate a biomarker value against reference ranges."""
    key = name.strip().lower()
    if key not in REFERENCE_RANGES:
        return {'status': 'unbekannt', 'message': 'Kein Referenzbereich definiert'}
    
    ref = REFERENCE_RANGES[key]
    optimal = ref['optimal']
    
    if value < ref['low']:
        status = 'niedrig'
        message = f'{name}: {value} {ref["unit"]} — unter dem optimalen Bereich ({optimal[0]}–{optimal[1]}).'
    elif ref['high'] and value > ref['high']:
        status = 'hoch'
        message = f'{name}: {value} {ref["unit"]} — über dem optimalen Bereich.'
    elif value < optimal[0]:
        status = 'suboptimal'
        message = f'{name}: {value} {ref["unit"]} — im Normbereich aber suboptimal ({optimal[0]}–{optimal[1]} optimal).'
    elif value > optimal[1]:
        status = 'grenzwertig'
        message = f'{name}: {value} {ref["unit"]} — grenzwertig, Optimierung empfohlen.'
    else:
        status = 'optimal'
        message = f'{name}: {value} {ref["unit"]} — im optimalen Bereich.'
    
    return {
        'status': status,
        'value': value,
        'unit': ref['unit'],
        'optimal_range': optimal,
        'message': message,
    }

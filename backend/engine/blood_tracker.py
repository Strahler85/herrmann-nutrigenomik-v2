"""Blutwerte-Langzeit-Tracking — Speichert Historie als JSON."""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

DATA_DIR = Path(__file__).parent.parent.parent / 'data'
HISTORY_FILE = DATA_DIR / 'blood_history.json'


def _load_history() -> List[Dict]:
    """Load blood value history from JSON file."""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []


def _save_history(history: List[Dict]) -> None:
    """Save blood value history to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def add_blood_snapshot(blood_values: Dict[str, Any]) -> Dict:
    """Add a new blood measurement snapshot with timestamp."""
    history = _load_history()
    snapshot = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'timestamp': datetime.now().isoformat(),
        'values': blood_values,
    }
    history.append(snapshot)
    _save_history(history)
    return snapshot


def get_blood_history(
    biomarker: Optional[str] = None,
    limit: int = 20,
) -> List[Dict]:
    """Get blood value history, optionally filtered by biomarker."""
    history = _load_history()
    history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    if biomarker:
        result = []
        for entry in history[:limit]:
            values = entry.get('values', {})
            bm_key = biomarker.strip().lower()
            if bm_key in values:
                result.append({
                    'date': entry['date'],
                    'timestamp': entry['timestamp'],
                    'value': values[bm_key].get('value'),
                    'unit': values[bm_key].get('unit', ''),
                })
        return result
    
    return history[:limit]


def get_biomarker_trend(
    biomarker: str,
    limit: int = 10,
) -> Dict:
    """Get trend data for a specific biomarker (last N measurements)."""
    history = get_blood_history(biomarker, limit)
    
    if not history:
        return {'biomarker': biomarker, 'values': [], 'trend': 'unbekannt',
                'count': 0, 'latest': None, 'earliest': None,
                'diff': 0, 'pct_change': 0}
    
    values = [h['value'] for h in history]
    dates = [h['date'] for h in history]
    
    if len(values) >= 2:
        diff = values[0] - values[-1]
        pct = (diff / values[-1] * 100) if values[-1] else 0
        if pct > 5:
            trend = 'steigend'
        elif pct < -5:
            trend = 'fallend'
        else:
            trend = 'stabil'
    else:
        trend = 'kein_trend'
        diff = 0
        pct = 0
    
    return {
        'biomarker': biomarker,
        'values': values,
        'dates': dates,
        'latest': values[0] if values else None,
        'earliest': values[-1] if values else None,
        'diff': round(diff, 2),
        'pct_change': round(pct, 1),
        'trend': trend,
        'count': len(values),
    }


def clear_history() -> None:
    """Clear all blood value history."""
    _save_history([])

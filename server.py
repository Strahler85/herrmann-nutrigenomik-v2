"""Flask API Server — Herrmann Nutrigenomik V2 (getbased-style)."""
import sys
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from backend.parsers.dna_parser import parse_genetic_file, detect_format
from backend.parsers.blood_parser import parse_blood_values, evaluate_biomarker
from backend.engine.scoring import load_snp_panel, extract_snp_genotypes, compute_risk_profile
from backend.engine.methylation import compute_methylation_score
from backend.engine.supplements import load_supplement_db, compute_supplement_plan
from backend.reports.report_generator import generate_markdown_report, generate_llm_prompt
from backend.reports.pdf_generator import generate_pdf_report
from backend.engine.drug_check import compute_drug_interactions, infer_phenotypes, DRUG_DATABASE
from backend.engine.expert_mode import (
    load_expert_panel, extract_expert_genotypes, get_expert_subcategories,
    compute_expert_category_scores, merge_risk_profiles,
)
from backend.engine.blood_tracker import (
    add_blood_snapshot, get_blood_history, get_biomarker_trend, clear_history,
)

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

# ── Load data once ──────────────────────────────────────────────────
SNP_PANEL = load_snp_panel()
SUPPLEMENT_DB = load_supplement_db()
EXPERT_PANEL = load_expert_panel()

DATA_DIR = Path(__file__).parent / 'backend' / 'data'
BLOOD_HISTORY_FILE = DATA_DIR / 'blood_history.json'

# In-Memory-Cache für geparste Genotypen (damit Re-Analyse ohne erneuten Upload funktioniert)
_genotype_cache = {}  # session_key -> {'genotypes': {}, 'format': '', 'filename': ''}

# ── API Routes ──────────────────────────────────────────────────────

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'ok',
        'panel_size': len(SNP_PANEL),
        'expert_panel_size': len(EXPERT_PANEL) if EXPERT_PANEL else 0,
        'supplements': len(SUPPLEMENT_DB),
        'drugs': len(DRUG_DATABASE),
    })


@app.route('/api/drugs/search')
def drug_search():
    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify({'results': list(DRUG_DATABASE)[:20]})
    matches = [d for d in DRUG_DATABASE if q in d.lower()]
    return jsonify({'results': matches[:10], 'total': len(matches)})


@app.route('/api/expert/categories')
def expert_categories():
    if not EXPERT_PANEL:
        return jsonify({'subcategories': {}})
    subcats = get_expert_subcategories(EXPERT_PANEL)
    return jsonify({'subcategories': subcats})


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Main analysis endpoint. Accepts DNA file, blood file, and profile data."""
    global _genotype_cache

    blood_file = request.files.get('blood')
    profile = json.loads(request.form.get('profile', '{}'))

    age = profile.get('age', 35)
    weight = profile.get('weight', 75)
    gender = profile.get('gender', 'm')
    drugs = profile.get('drugs', [])

    # ── Parse DNA (Datei oder Cache) ──
    if 'dna' in request.files:
        dna_file = request.files['dna']
        suffix = Path(dna_file.filename).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(dna_file.read())
            tmp_path = tmp.name

        try:
            fmt = detect_format(tmp_path)
            genotypes = parse_genetic_file(tmp_path, fmt='auto')
        except Exception as e:
            os.unlink(tmp_path)
            return jsonify({'error': f'DNA-Parse-Fehler: {e}'}), 400
        finally:
            os.unlink(tmp_path)

        # Im Cache speichern
        _genotype_cache = {
            'genotypes': genotypes,
            'format': fmt,
            'filename': dna_file.filename,
        }
    elif _genotype_cache:
        genotypes = _genotype_cache['genotypes']
        fmt = _genotype_cache.get('format', 'cached')
    else:
        return jsonify({'error': 'Keine DNA-Datei hochgeladen'}), 400

    # ── Parse blood values ──
    blood_values = {}
    if blood_file:
        b_suffix = Path(blood_file.filename).suffix
        with tempfile.NamedTemporaryFile(suffix=b_suffix, delete=False) as tmp:
            tmp.write(blood_file.read())
            btmp_path = tmp.name
        try:
            blood_values = parse_blood_values(btmp_path)
        except Exception:
            blood_values = {}
        finally:
            if Path(btmp_path).exists():
                os.unlink(btmp_path)

    # ── Run analysis ──
    snp_calls = extract_snp_genotypes(genotypes, SNP_PANEL)
    found = sum(1 for v in snp_calls.values() if v['status'] == 'found')

    risk_profile = compute_risk_profile(snp_calls, SNP_PANEL)

    methylation_score = compute_methylation_score(
        risk_profile['category_scores'], snp_calls, blood_values
    )

    # Drug interactions (MUSS vor Supplement-Engine laufen!)
    phenotypes = infer_phenotypes(snp_calls)
    drug_warnings = compute_drug_interactions(phenotypes, snp_calls=snp_calls)

    # Filter warnings to selected drugs
    if drugs:
        drug_warnings = [
            w for w in drug_warnings
            if w['drug'].lower() in [d.lower() for d in drugs]
        ]

    # Supplement plan
    supplement_plan = compute_supplement_plan(
        risk_profile, methylation_score, blood_values,
        age, weight, gender, SUPPLEMENT_DB,
        drug_warnings=drug_warnings,
    )

    # Blood evaluation
    blood_results = []
    for name, data in blood_values.items():
        result = evaluate_biomarker(name, data['value'])
        blood_results.append(result)
        result['name'] = name
        result['value'] = data['value']
        result['unit'] = data.get('unit', '')

    # Save blood snapshot
    if blood_values:
        add_blood_snapshot(blood_values)
    blood_history = get_blood_history(limit=30)

    # Expert mode (always runs with available SNPs)
    expert_snp_calls = None
    expert_found = 0
    expert_cat_scores = {}
    if EXPERT_PANEL:
        expert_snp_calls = extract_expert_genotypes(genotypes, EXPERT_PANEL)
        expert_found = sum(1 for v in expert_snp_calls.values() if v['status'] == 'found')
        expert_cat_scores = compute_expert_category_scores(expert_snp_calls, EXPERT_PANEL)
        merged = merge_risk_profiles(risk_profile['category_scores'], expert_cat_scores)
        risk_profile['category_scores'] = merged

        # Recalculate supplements with merged scores
        supplement_plan = compute_supplement_plan(
            risk_profile, methylation_score, blood_values,
            age, weight, gender, SUPPLEMENT_DB,
            drug_warnings=drug_warnings,
        )

    # Markdown report
    md_report = generate_markdown_report(
        risk_profile, methylation_score, supplement_plan,
        blood_results, profile,
    )

    return jsonify({
        'dna_file': _genotype_cache.get('filename', 'cached'),
        'format': fmt,
        'genotype_count': len(genotypes),
        'snp_found': found,
        'snp_total': len(SNP_PANEL),
        'supplement_plan': _supplements_with_aliases(supplement_plan),
        'risk_profile': {
            'category_scores': _serialize_scores(risk_profile['category_scores']),
            'interactions': risk_profile.get('interactions', []),
            'executive_summary': risk_profile.get('executive_summary', []),
        },
        'snp_calls': _snp_calls_safe(snp_calls),
        'methylation_score': methylation_score,
        'supplement_plan': supplement_plan,
        'blood_results': blood_results,
        'blood_history': blood_history,
        'drug_warnings': drug_warnings,
        'phenotypes': phenotypes,
        'expert': {
            'found': expert_found,
            'total': len(EXPERT_PANEL) if EXPERT_PANEL else 0,
            'snp_calls': expert_snp_calls,
            'category_scores': expert_cat_scores,
        } if EXPERT_PANEL else None,
        'markdown_report': md_report,
    })


@app.route('/api/blood/history', methods=['GET'])
def blood_history_route():
    biomarker = request.args.get('biomarker', None)
    limit = int(request.args.get('limit', 20))
    history = get_blood_history(biomarker=biomarker, limit=limit)
    return jsonify({'history': history})


@app.route('/api/blood/upload', methods=['POST'])
def blood_upload():
    if 'blood' not in request.files:
        return jsonify({'error': 'Keine Blutwert-Datei'}), 400

    blood_file = request.files['blood']
    suffix = Path(blood_file.filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(blood_file.read())
        tmp_path = tmp.name

    try:
        blood_values = parse_blood_values(tmp_path)
        snapshot = add_blood_snapshot(blood_values)
        return jsonify({
            'count': len(blood_values),
            'snapshot': snapshot,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        if Path(tmp_path).exists():
            os.unlink(tmp_path)


@app.route('/api/blood/history', methods=['DELETE'])
def blood_history_clear():
    clear_history()
    return jsonify({'status': 'cleared'})


@app.route('/api/blood/snapshot', methods=['POST'])
def blood_snapshot():
    data = request.get_json()
    if not data or 'values' not in data:
        return jsonify({'error': 'values required'}), 400
    snapshot = add_blood_snapshot(data['values'])
    return jsonify({'snapshot': snapshot})


@app.route('/api/blood/trend/<biomarker>')
def blood_trend(biomarker):
    trend = get_biomarker_trend(biomarker)
    return jsonify(trend)


@app.route('/api/export/pdf', methods=['POST'])
def export_pdf():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Analysis data required'}), 400

    risk_profile = data.get('risk_profile', {})
    methylation_score = data.get('methylation_score', {})
    supplement_plan = data.get('supplement_plan', [])
    blood_results = data.get('blood_results', [])
    profile = data.get('profile', {})

    pdf_path = str(DATA_DIR / 'temp_report.pdf')
    generate_pdf_report(risk_profile, methylation_score, supplement_plan,
                        blood_results, profile, pdf_path)

    return send_file(pdf_path, mimetype='application/pdf',
                     as_attachment=True, download_name='nutrigenomik_report.pdf')


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/<path:path>')
def static_files(path):
    return app.send_static_file(path)


# ── Helpers ─────────────────────────────────────────────────────────

def _serialize_scores(category_scores):
    """Convert category scores to JSON-safe format."""
    result = {}
    for cat, data in category_scores.items():
        result[cat] = {
            'score': data.get('score'),
            'category': data.get('category', 'Niedrig'),
            'tested_snps': data.get('tested_snps', 0),
            'missing_snps': data.get('missing_snps', 0),
            'genes': data.get('genes', []),
            'contributing_snps': [
                {
                    'rsid': s.get('rsid'),
                    'gene': s.get('gene'),
                    'genotype': s.get('normalised', s.get('genotype', '')),
                    'risk_count': s.get('risk_count'),
                    'raw_score': s.get('raw_score'),
                    'effect': s.get('effect_direction', ''),
                    'description': s.get('description', ''),
                    'recommendation': s.get('recommendation', ''),
                }
                for s in data.get('contributing_snps', [])
            ],
        }
    return result


def _snp_calls_safe(snp_calls):
    """Strip non-serializable fields from snp_calls."""
    safe = {}
    for rsid, call in snp_calls.items():
        safe[rsid] = {
            'rsid': call.get('rsid', rsid),
            'gene': call.get('gene', ''),
            'genotype': call.get('normalised', call.get('genotype', '')),
            'risk_count': call.get('risk_count'),
            'raw_score': call.get('raw_score'),
            'effect': call.get('effect_direction', ''),
            'description': call.get('description', ''),
            'recommendation': call.get('recommendation', ''),
        }
    return safe


def _supplements_with_aliases(plan):
    """Add convenience aliases for JS frontend compatibility."""
    result = []
    for s in plan:
        s['final_dose_mg'] = s.get('dose', 0)
        s['dose_mg'] = s.get('dose', 0)
        result.append(s)
    return result


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f'🧬 Herrmann Nutrigenomik V2 — Server on http://localhost:{port}')
    app.run(host='0.0.0.0', port=port, debug=True)

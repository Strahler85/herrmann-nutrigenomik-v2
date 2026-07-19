"""Optional: Ollama KI-Integration für natürlichsprachliche Reports."""
import json
import requests
from typing import Dict, List, Optional


def generate_health_report(
    prompt: str,
    base_url: str = 'http://localhost:11434',
    model: str = 'llama3.2',
    temperature: float = 0.3,
) -> Optional[str]:
    """Generate a health report using local Ollama LLM."""
    try:
        response = requests.post(
            f'{base_url}/api/generate',
            json={
                'model': model,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': temperature},
            },
            timeout=120,
        )
        if response.status_code == 200:
            return response.json().get('response', '')
        return None
    except requests.ConnectionError:
        return None
    except Exception as e:
        return f'Fehler: {e}'

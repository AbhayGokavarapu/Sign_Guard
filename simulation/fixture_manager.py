"""Compatibility entry point for the annotated v3 evaluation dataset."""
import json
from pathlib import Path
import config
from simulation.evaluation_dataset import generate_evaluation_dataset

MANIFEST_PATH = str(Path(config.DATASETS_DIR) / 'manifest.json')


def generate_dataset(force=False):
    path = Path(MANIFEST_PATH)
    if path.exists() and not force:
        data = json.loads(path.read_text())
        if data.get('version') == 3:
            return data
    data = generate_evaluation_dataset()
    path.write_text(json.dumps(data, indent=2))
    return data


def load_manifest():
    return generate_dataset()

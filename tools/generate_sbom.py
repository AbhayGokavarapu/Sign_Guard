"""Export installed Python components as CycloneDX JSON; not a vulnerability verdict."""
import importlib.metadata
import json
from pathlib import Path
import sys
from urllib.parse import quote


def generate():
    components=[]
    for distribution in sorted(importlib.metadata.distributions(),key=lambda d:d.metadata.get('Name','').lower()):
        name=distribution.metadata.get('Name','unknown');version=distribution.version
        components.append({'type':'library','name':name,'version':version,
            'purl':f'pkg:pypi/{quote(name.lower())}@{quote(version)}'})
    return {'bomFormat':'CycloneDX','specVersion':'1.5','version':1,'components':components}


if __name__=='__main__':
    output=Path(sys.argv[1] if len(sys.argv)>1 else 'benchmarks/python-sbom.json')
    output.write_text(json.dumps(generate(),indent=2))
    print('SBOM written:',output)

"""Capture the exact code, dependency and decision configuration used by an analysis."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import config


def capture(settings):
    base=Path(config.BASE_DIR)
    digest=hashlib.sha256()
    files=sorted([*base.glob('core/*.py'),*base.glob('reporting/*.py'),base/'config.py'])
    for path in files:
        digest.update(str(path.relative_to(base)).encode()+b'\0'+path.read_bytes()+b'\0')
    try:
        commit=subprocess.check_output(['git','-C',str(base),'rev-parse','HEAD'],stderr=subprocess.DEVNULL,text=True,timeout=3).strip()
        dirty=bool(subprocess.check_output(['git','-C',str(base),'status','--porcelain'],text=True,timeout=3).strip())
    except (OSError,subprocess.SubprocessError):commit='UNAVAILABLE';dirty=None
    packages={}
    for name in ('pyhanko','pyhanko-certvalidator','cryptography','PyMuPDF','opencv-python-headless','numpy','Pillow','scipy','reportlab','streamlit','filelock'):
        try:packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:packages[name]='UNAVAILABLE'
    thresholds={name:getattr(config,name) for name in dir(config)
                if name.startswith(('MAX_','ELA_','ORB_','RANSAC_','DIFF_','SHADOW_','PROCESSING_','WORKER_','RENDER_','THUMBNAIL_','RENDERER_','QUEUE_'))
                and isinstance(getattr(config,name),(str,int,float,bool,list))}
    roots=Path(config.TRUST_ROOTS_FILE) if config.TRUST_ROOTS_FILE else None
    roots_sha=hashlib.sha256(roots.read_bytes()).hexdigest() if roots and roots.is_file() else None
    return {'application_version':'3.2','git_commit':commit,'working_tree_modified':dirty,
            'engine_source_sha256':digest.hexdigest(),'python':platform.python_version(),
            'platform':platform.platform(),'dependencies':packages,'settings':settings,
            'thresholds_and_limits':thresholds,'trust_roots_sha256':roots_sha,
            'revocation_evidence_sha256':sorted(hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(config.REVOCATION_DIR).glob('*') if p.is_file() and p.stat().st_size<=2*1024*1024) if config.REVOCATION_DIR else [],
            'certificate_fetching':'disabled; operator-provided offline evidence only',
            'pair_selection':'appearance/geometry ranking with page-pair round-robin allocation'}

"""Streamlit Community Cloud entry point with public-demo privacy defaults."""
import os
from pathlib import Path
import runpy
os.environ['SIGNGUARD_PUBLIC_DEMO'] = '1'
os.environ.setdefault('SIGNGUARD_WORKER_MEMORY_MB', '2048')
# Execute on every Streamlit rerun; a cached `import app` would render a blank page.
runpy.run_path(str(Path(__file__).with_name('app.py')), run_name='__main__')

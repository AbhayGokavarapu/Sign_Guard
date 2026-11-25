"""Disposable PDF worker. IPC files contain only locally constructed Python data."""
import os
import pickle
import subprocess
import sys
import tempfile
from pathlib import Path
import config


def execute(raw, filename, options, timeout=None):
    from core.pipeline import _failure
    with tempfile.TemporaryDirectory(prefix='signguard-worker-') as folder:
        incoming, outgoing = Path(folder) / 'input', Path(folder) / 'result'
        limits = {name: getattr(config, name) for name in
                  ('MAX_PAGE_COUNT', 'MAX_PAGE_WIDTH_PX', 'MAX_PAGE_HEIGHT_PX',
                   'MAX_TOTAL_RENDER_PIXELS', 'WORKER_MEMORY_MB', 'MAX_REVISIONS',
                   'MAX_SIGNATURES', 'MAX_LOC_CANDIDATES', 'MAX_CANDIDATE_PAIRS',
                   'MAX_ANALYSIS_CANDIDATES')}
        incoming.write_bytes(pickle.dumps((raw, filename, options, limits)))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1',
                   OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
        try:
            completed = subprocess.run([sys.executable, '-m', 'core.worker', str(incoming), str(outgoing)],
                cwd=config.BASE_DIR, env=env, stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE, timeout=config.PROCESSING_TIMEOUT_S if timeout is None else timeout)
        except subprocess.TimeoutExpired:
            return _failure('Processing time limit exceeded; worker terminated.', filename)
        if completed.returncode or not outgoing.exists():
            return _failure('PDF worker failed or exceeded its memory limit; analysis incomplete.', filename)
        try:
            return pickle.loads(outgoing.read_bytes())
        except Exception:
            return _failure('Worker result could not be read; analysis incomplete.', filename)


def main():
    raw, filename, options, limits = pickle.loads(Path(sys.argv[1]).read_bytes())
    for key, value in limits.items():
        setattr(config, key, value)
    if sys.platform != 'win32':
        import resource
        budget = config.WORKER_MEMORY_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (budget, budget))
        resource.setrlimit(resource.RLIMIT_CPU, (config.PROCESSING_TIMEOUT_S, config.PROCESSING_TIMEOUT_S + 1))
    import cv2
    cv2.setNumThreads(1)
    from core.pipeline import _run, _failure
    try:
        result = _run(raw, filename, **options)
    except Exception as exc:
        result = _failure(f'Analysis failed: {type(exc).__name__}: {exc}', filename)
    if sys.platform == 'win32':
        result.coverage.setdefault('limitations', []).append('OS memory limit unavailable on Windows; timeout and render limits remain enforced.')
    Path(sys.argv[2]).write_bytes(pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL))


if __name__ == '__main__':
    main()

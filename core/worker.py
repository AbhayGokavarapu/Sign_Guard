"""Disposable, resource-limited workers shared by analysis, comparison and validator checks."""
import os
import pickle
import subprocess
import sys
import tempfile
from pathlib import Path
import config


def _run_process(command,env,timeout):
    """A job owns its process group, including native rendering/validator children."""
    with subprocess.Popen(command,cwd=config.BASE_DIR,env=env,stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE,start_new_session=os.name!='nt') as process:
        try:
            _,stderr=process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name!='nt':
                import signal
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
            else:process.kill()
            process.communicate()
            raise RuntimeError('Processing time limit exceeded; worker process group terminated.')
        return subprocess.CompletedProcess(command,process.returncode,b'',stderr)


def _execute(operation,payload,timeout=None):
    from core.processing_queue import admit
    with admit(), tempfile.TemporaryDirectory(prefix='signguard-worker-') as folder:
        incoming,outgoing=Path(folder)/'input',Path(folder)/'result'
        names=('MAX_PAGE_COUNT','MAX_PAGE_WIDTH_PX','MAX_PAGE_HEIGHT_PX','MAX_TOTAL_RENDER_PIXELS',
               'WORKER_MEMORY_MB','MAX_REVISIONS','MAX_SIGNATURES','MAX_LOC_CANDIDATES',
               'MAX_CANDIDATE_PAIRS','MAX_ANALYSIS_CANDIDATES','MAX_STATIC_OBJECTS',
               'MAX_TIMELINE_PAGE_COMPARISONS','MAX_RENDERER_PAGES')
        incoming.write_bytes(pickle.dumps((operation,payload,{n:getattr(config,n) for n in names})))
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
        env.pop('SIGNGUARD_EVIDENCE_SIGNING_KEY',None)
        process=_run_process([sys.executable,'-m','core.worker',str(incoming),str(outgoing)],env,
            config.PROCESSING_TIMEOUT_S if timeout is None else timeout)
        if process.returncode or not outgoing.exists():
            raise RuntimeError('PDF worker failed or exceeded its memory limit; analysis incomplete.')
        return pickle.loads(outgoing.read_bytes())


def execute(raw,filename,options,timeout=None):
    from core.pipeline import _failure
    try:return _execute('analyse',{'raw':raw,'filename':filename,**options},timeout)
    except (RuntimeError,TimeoutError) as exc:return _failure(str(exc),filename)


def execute_task(operation,payload,timeout=None):
    try:return _execute(operation,payload,timeout)
    except (RuntimeError,TimeoutError) as exc:return {'error':str(exc),'complete':False}


def main():
    operation,payload,limits=pickle.loads(Path(sys.argv[1]).read_bytes())
    for key,value in limits.items():setattr(config,key,value)
    if sys.platform!='win32':
        import resource
        budget=config.WORKER_MEMORY_MB*1024*1024
        resource.setrlimit(resource.RLIMIT_AS,(budget,budget))
        resource.setrlimit(resource.RLIMIT_CPU,(config.PROCESSING_TIMEOUT_S,config.PROCESSING_TIMEOUT_S+1))
    import cv2
    cv2.setNumThreads(1)
    try:
        if operation=='analyse':
            from core.pipeline import _run
            result=_run(**payload)
        elif operation=='compare':
            from core.document_diff import compare_raw
            result=compare_raw(**payload)
        elif operation=='verify_bundle':
            from reporting.evidence_bundle import verify_bundle
            result=verify_bundle(**payload)
        elif operation=='external_validate':
            from core.independent_checks import validate_with_poppler
            result=validate_with_poppler(**payload)
        else:raise ValueError('Unsupported worker operation')
    except Exception as exc:
        message=f'Analysis failed: {type(exc).__name__}: {exc}'
        if operation=='analyse':
            from core.pipeline import _failure
            result=_failure(message)
        else:result={'error':message,'complete':False}
    if operation=='analyse' and sys.platform=='win32':
        result.coverage.setdefault('limitations',[]).append('OS memory limit unavailable on Windows; timeout and render limits remain enforced.')
    Path(sys.argv[2]).write_bytes(pickle.dumps(result,protocol=pickle.HIGHEST_PROTOCOL))


if __name__=='__main__':main()

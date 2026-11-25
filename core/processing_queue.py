"""Cross-process bounded admission; saturated requests fail promptly rather than accumulate."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import tempfile
import time
from filelock import FileLock, Timeout
import config


@contextmanager
def admit():
    namespace=hashlib.sha256(str(Path(config.BASE_DIR).resolve()).encode()).hexdigest()[:16]
    folder=Path(tempfile.gettempdir())/('signguard-slots-'+namespace)
    folder.mkdir(mode=0o700,exist_ok=True)
    deadline=time.monotonic()+config.QUEUE_WAIT_S
    acquired=None
    while acquired is None:
        for slot in range(max(1,config.MAX_CONCURRENT_JOBS)):
            lock=FileLock(str(folder/f'{slot}.lock'))
            try:lock.acquire(timeout=0)
            except Timeout:continue
            acquired=lock;break
        if acquired is not None:break
        if time.monotonic()>=deadline:raise TimeoutError('Busy: all analysis workers are in use. Please retry shortly.')
        time.sleep(.05)
    try:yield
    finally:acquired.release()

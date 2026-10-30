"""Atomic filesystem transactions and per-instance mutation lock."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import base64
import json
import os
import tempfile
from .configuration import FrameworkError

def read_bytes(path):
    path=Path(path)
    if path.is_symlink():
        raise FrameworkError(f'Refusing final-file symlink: {path}')
    if path.exists() and not path.is_file():
        raise FrameworkError(f'Expected file: {path}')
    return path.read_bytes() if path.exists() else None

def encode(data):
    return None if data is None else base64.b64encode(data).decode('ascii')

def decode(data):
    return None if data is None else base64.b64decode(data,validate=True)

def atomic_write(path, content):
    path=Path(path)
    if path.is_symlink():
        raise FrameworkError(f'Refusing final-file symlink: {path}')
    if content is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    mode=path.stat().st_mode & 0o777 if path.exists() else 0o600
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
            temporary=Path(f.name)
            f.write(content); f.flush(); os.fsync(f.fileno())
        os.chmod(temporary,mode)
        os.replace(temporary,path)
    finally:
        if temporary and temporary.exists(): temporary.unlink()

@contextmanager
def locked(directory):
    directory.mkdir(parents=True,exist_ok=True)
    lock=directory/'mutation.lock'
    try:
        with lock.open('x',encoding='utf-8') as f:
            f.write(str(os.getpid())+'\n')
    except FileExistsError as exc:
        raise FrameworkError(f'Instance locked: {lock}; verify no installer is running before manually removing a stale lock') from exc
    try:
        yield
    finally:
        lock.unlink()

def transaction(directory, changes, before):
    """Persist recovery data before any payload writes; restore on errors."""
    for path in changes:
        if read_bytes(path) != before[path]:
            raise FrameworkError(f'File changed after planning: {path}')
    if not changes:
        return None
    backups=directory/'backups'
    backups.mkdir(parents=True,exist_ok=True)
    journal=backups/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'.json')
    atomic_write(journal,json.dumps({p:encode(v) for p,v in before.items()},indent=2).encode())
    written=[]
    try:
        for path,content in changes.items():
            if read_bytes(path) != before[path]:
                raise FrameworkError(f'File changed during transaction: {path}')
            atomic_write(path,content)
            written.append(path)
    except BaseException as exc:
        failures=[]
        for path in reversed(written):
            try: atomic_write(path,before[path])
            except OSError as rollback_error: failures.append(str(rollback_error))
        detail='; rollback failed: '+str(failures) if failures else '; previous contents restored'
        raise FrameworkError(f'Transaction failed: {exc}{detail}. Recovery journal: {journal}') from exc
    return str(journal)

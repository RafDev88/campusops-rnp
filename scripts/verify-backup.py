"""Create a protected local dump and prove restoration in a disposable database.

Run from the repository root with Docker running:
    .venv/Scripts/python scripts/verify-backup.py
Never restores over campusops. No passwords or row contents are printed.
"""
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def docker(*args, **kwargs):
    return subprocess.run(['docker', 'compose', 'exec', '-T', 'db', *args], cwd=ROOT,
                          check=True, stderr=subprocess.PIPE, **kwargs)


def main():
    target = 'campusops_restore_' + uuid4().hex
    assert re.fullmatch(r'campusops_restore_[0-9a-f]{32}', target)
    directory = ROOT / 'backups'
    directory.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dump = directory / f'verified-{stamp}-{uuid4().hex[:8]}.dump'
    created = False
    try:
        with dump.open('xb') as stream:
            docker('pg_dump', '-U', 'campusops', '-d', 'campusops', '-Fc', '--no-owner', '--no-acl', stdout=stream)
        docker('createdb', '-U', 'campusops', target, stdout=subprocess.DEVNULL)
        created = True
        with dump.open('rb') as stream:
            docker('pg_restore', '-U', 'campusops', '-d', target, '--no-owner', '--no-acl', '--exit-on-error', stdin=stream, stdout=subprocess.DEVNULL)
        sql = "SELECT json_build_object('revision',(SELECT version_num FROM alembic_version),'institutions',(SELECT count(*) FROM institutions),'publications',(SELECT count(*) FROM publications),'users',(SELECT count(*) FROM users),'runs',(SELECT count(*) FROM runs))"
        result = docker('psql', '-U', 'campusops', '-d', target, '-At', '-v', 'ON_ERROR_STOP=1', '-c', sql, stdout=subprocess.PIPE)
        restored = json.loads(result.stdout)
        assert restored['revision'], 'Missing migration revision'
        evidence = {'verified_at': datetime.now(timezone.utc).isoformat(), 'restore_succeeded': True,
                    'dump': dump.name, 'size_bytes': dump.stat().st_size, 'restored_counts': restored,
                    'scope': 'Restore of a consistent pg_dump snapshot into an isolated database, not a comparison against concurrently changing live data.'}
        dump.with_suffix('.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
        print(json.dumps(evidence, indent=2))
    finally:
        if created:
            # Generated, validated target only; never accept arbitrary user input here.
            docker('dropdb', '-U', 'campusops', '--force', target, stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    main()

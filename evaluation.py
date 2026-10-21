"""Local attempt audit. Passing checks is not a semantic correctness verdict."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

DB_PATH = Path(__file__).parent / 'evaluations.db'
PROMPT_VERSION = 'storydoor-2.1'
CHECK_VERSION = 'targeted-2.1'


def connection(path):
    conn = sqlite3.connect(path, timeout=5)
    conn.execute('CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, payload TEXT NOT NULL, review TEXT NOT NULL DEFAULT \'pending\', notes TEXT NOT NULL DEFAULT \'\')')
    return conn


def record_attempt(record, path=DB_PATH):
    record = dict(record, id=str(uuid4()), timestamp=datetime.now(timezone.utc).isoformat(), prompt_version=PROMPT_VERSION, check_version=CHECK_VERSION)
    conn = connection(path)
    try:
        with conn:
            conn.execute('INSERT INTO attempts (id,payload) VALUES (?,?)', (record['id'], json.dumps(record)))
    finally:
        conn.close()
    return record['id']


def read_attempts(path=DB_PATH):
    conn = connection(path)
    try:
        return [dict(json.loads(payload), human_review=review, human_notes=notes) for payload, review, notes in conn.execute('SELECT payload,review,notes FROM attempts ORDER BY rowid DESC')]
    finally:
        conn.close()


def review_attempt(attempt_id, review, notes, path=DB_PATH):
    if review not in {'pending', 'pass', 'fail'}:
        raise ValueError('Unknown review status')
    conn = connection(path)
    try:
        with conn:
            cursor = conn.execute('UPDATE attempts SET review=?,notes=? WHERE id=?', (review, notes, attempt_id))
            if cursor.rowcount != 1:
                raise ValueError('Unknown attempt')
    finally:
        conn.close()


def summarize(rows):
    returned = [r for r in rows if r['status'] != 'api_error']
    return {'attempts': len(rows), 'api_errors': sum(r['status']=='api_error' for r in rows), 'responses':len(returned), 'fallbacks':sum(r['fallback'] for r in returned), 'fallback_rate':sum(r['fallback'] for r in returned)/len(returned) if returned else None, 'human_pending':sum(r['human_review']=='pending' for r in rows)}

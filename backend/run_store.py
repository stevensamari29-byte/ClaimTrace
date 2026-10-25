"""Local SQLite run snapshots and compare-and-set human review history.

This is trusted local development storage, not shared authentication. No memory
correction is approved by reviewing a report.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID


class RunNotFound(Exception):
    pass


class ReviewConflict(Exception):
    pass


class RunIntegrityError(Exception):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def report_digest(report):
    return hashlib.sha256(canonical(report).encode('utf-8')).hexdigest()


class RunStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else Path(__file__).resolve().parents[1] / '.local' / 'investigations.sqlite3'

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys=ON')
        connection.executescript('''
            CREATE TABLE IF NOT EXISTS investigation_runs (
                run_id TEXT PRIMARY KEY, report_json TEXT NOT NULL, report_digest TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS investigation_reviews (
                run_id TEXT NOT NULL REFERENCES investigation_runs(run_id),
                version INTEGER NOT NULL, decision TEXT NOT NULL, comment TEXT NOT NULL,
                reviewer TEXT NOT NULL, reviewed_at TEXT NOT NULL,
                PRIMARY KEY (run_id, version)
            );
        ''')
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _read(connection, run_id):
        row = connection.execute('SELECT * FROM investigation_runs WHERE run_id=?', (run_id,)).fetchone()
        if row is None:
            raise RunNotFound
        try:
            report = json.loads(row['report_json'])
            if report['run_id'] != run_id or report_digest(report) != row['report_digest']:
                raise RunIntegrityError
        except (ValueError, TypeError, KeyError) as error:
            raise RunIntegrityError from error
        history = [dict(item) for item in connection.execute(
            'SELECT version, decision, comment, reviewer, reviewed_at FROM investigation_reviews WHERE run_id=? ORDER BY version', (run_id,))]
        if any(item['version'] != index + 1 or item['decision'] not in ('approved', 'rejected') for index, item in enumerate(history)):
            raise RunIntegrityError
        return {'schema_version': 'claimtrace.run.v1', 'run_id': run_id,
                'report_digest': row['report_digest'], 'report': report,
                'review': {'status': history[-1]['decision'] if history else 'required',
                           'version': len(history), 'history': history}}

    def save(self, report):
        run_id = str(UUID(report['run_id']))
        if run_id != report['run_id'] or report.get('schema_version') != 'claimtrace.investigation.v1':
            raise RunIntegrityError
        content = canonical(report)
        if len(content.encode('utf-8')) > 2_000_000:
            raise RunIntegrityError
        with self._connect() as connection:
            connection.execute('INSERT INTO investigation_runs VALUES (?,?,?)', (run_id, content, report_digest(report)))
            result = self._read(connection, run_id)
        return result

    def get(self, run_id):
        with self._connect() as connection:
            return self._read(connection, run_id)

    def review(self, run_id, digest, expected_version, decision, comment='', *, reviewer='local-human'):
        if (type(expected_version) is not int or expected_version < 0 or decision not in ('approved', 'rejected')
                or not isinstance(comment, str) or len(comment) > 2000 or reviewer != 'local-human'):
            raise ValueError('Invalid trusted review input')
        with self._connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            current = self._read(connection, run_id)
            if current['report_digest'] != digest or current['review']['version'] != expected_version:
                raise ReviewConflict
            connection.execute('INSERT INTO investigation_reviews VALUES (?,?,?,?,?,?)',
                (run_id, expected_version + 1, decision, comment, reviewer, datetime.now(timezone.utc).isoformat()))
            result = self._read(connection, run_id)
        return result

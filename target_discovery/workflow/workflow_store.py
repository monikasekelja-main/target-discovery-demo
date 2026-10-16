"""Small transactional SQLite store for local runs, immutable history and events."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def dump(value):
    return json.dumps(value,sort_keys=True,allow_nan=False)


class Store:
    def __init__(self, workspace):
        self.workspace=Path(workspace).resolve()
        self.workspace.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.workspace/'workflow.sqlite3',timeout=10,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY, state TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS assessments(run_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
                brief TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(run_id,assessment_id),
                FOREIGN KEY(run_id) REFERENCES runs(run_id));
            CREATE TABLE IF NOT EXISTS reviews(run_id TEXT NOT NULL, review_id TEXT NOT NULL,
                review TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(run_id,review_id),
                FOREIGN KEY(run_id) REFERENCES runs(run_id));
            CREATE TABLE IF NOT EXISTS events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL, created_at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(run_id));
            CREATE TABLE IF NOT EXISTS snapshots(run_id TEXT NOT NULL, revision INTEGER NOT NULL,
                relative_path TEXT NOT NULL, sha256 TEXT NOT NULL, source_text TEXT NOT NULL,
                PRIMARY KEY(run_id,revision,relative_path), FOREIGN KEY(run_id) REFERENCES runs(run_id));
        ''')

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def close(self):
        self.db.close()

    def exists(self,run_id):
        return self.db.execute('SELECT 1 FROM runs WHERE run_id=?',(run_id,)).fetchone() is not None

    def load(self,run_id):
        row=self.db.execute('SELECT state FROM runs WHERE run_id=?',(run_id,)).fetchone()
        if row is None: raise ValueError(f'Unknown run: {run_id}')
        return json.loads(row['state'])

    def save(self,state):
        self.db.execute('INSERT INTO runs VALUES(?,?,?) ON CONFLICT(run_id) DO UPDATE SET state=excluded.state,updated_at=excluded.updated_at',
                        (state['run_id'],dump(state),now()))

    def event(self,state,kind,payload):
        self.db.execute('INSERT INTO events(run_id,created_at,kind,payload) VALUES(?,?,?,?)',
                        (state['run_id'],now(),kind,dump(payload)))

    def events(self,run_id):
        return [{'event_id':r['event_id'],'created_at':r['created_at'],'kind':r['kind'],'payload':json.loads(r['payload'])}
                for r in self.db.execute('SELECT * FROM events WHERE run_id=? ORDER BY event_id',(run_id,))]

    def add_snapshots(self,state):
        for relative,snapshot in state['snapshots'].items():
            existing=self.db.execute('SELECT sha256 FROM snapshots WHERE run_id=? AND revision=? AND relative_path=?',
                (state['run_id'],state['revision'],relative)).fetchone()
            if existing and existing['sha256']!=snapshot['sha256']:
                raise ValueError('Cannot overwrite a recorded snapshot within the same revision')
            self.db.execute('INSERT OR IGNORE INTO snapshots VALUES(?,?,?,?,?)',
                (state['run_id'],state['revision'],relative,snapshot['sha256'],snapshot['text']))

    def snapshots(self,run_id):
        return [dict(r) for r in self.db.execute('SELECT revision,relative_path,sha256,source_text FROM snapshots WHERE run_id=? ORDER BY revision,relative_path',
                                                (run_id,))]

    def add_assessment(self,state,brief):
        self.db.execute('INSERT INTO assessments VALUES(?,?,?,?)',
                        (state['run_id'],brief['assessment_id'],dump(brief),now()))

    def assessment(self,run_id,assessment_id):
        row=self.db.execute('SELECT brief FROM assessments WHERE run_id=? AND assessment_id=?',(run_id,assessment_id)).fetchone()
        if row is None: raise ValueError('Unknown assessment')
        return json.loads(row['brief'])

    def assessments(self,run_id):
        return [json.loads(r['brief']) for r in self.db.execute('SELECT brief FROM assessments WHERE run_id=? ORDER BY rowid',(run_id,))]

    def add_review(self,state,review):
        self.db.execute('INSERT INTO reviews VALUES(?,?,?,?)',
                        (state['run_id'],review['review_id'],dump(review),now()))

    def reviews(self,run_id):
        return [json.loads(r['review']) for r in self.db.execute('SELECT review FROM reviews WHERE run_id=? ORDER BY rowid',(run_id,))]

import sqlite3
from contextlib import contextmanager
from settings import DB_PATH


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.executescript(
            """
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  consult_type TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transcript_chunks (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  audio_path TEXT,
  created_at TEXT NOT NULL,
  idempotency_key TEXT
);
CREATE TABLE IF NOT EXISTS suggestions (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  question TEXT NOT NULL,
  reason TEXT NOT NULL,
  priority TEXT NOT NULL,
  status TEXT NOT NULL,
  answer_found TEXT,
  related_diagnoses TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS differentials (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  diagnosis TEXT NOT NULL,
  rank INTEGER NOT NULL,
  confidence REAL NOT NULL,
  supporting_evidence TEXT,
  missing_information TEXT,
  suggested_questions TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analysis_jobs (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  status TEXT NOT NULL,
  task_path TEXT,
  output_path TEXT,
  error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
"""
        )
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

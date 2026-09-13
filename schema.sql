-- Campaigns Authoritative SQLite Schema

CREATE TABLE "Strikes" (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  created_at TEXT NOT NULL,
  execution_date TEXT NOT NULL,
  assigned TEXT DEFAULT 'Bhakta',
  status TEXT DEFAULT 'STANDBY',
  notes TEXT,
  task_id INTEGER DEFAULT NULL,
  subtask_id INTEGER DEFAULT NULL,
  reschedule_count INTEGER DEFAULT 0,
  recurrence_id TEXT DEFAULT NULL
);

CREATE TABLE Subtasks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      task_id INTEGER NOT NULL,
      title TEXT NOT NULL,
      creation_time TEXT NOT NULL,
      status TEXT NOT NULL,
      FOREIGN KEY (task_id) REFERENCES Tasks(id) ON DELETE CASCADE
    );

CREATE TABLE "Tags" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER DEFAULT NULL,
            tag_name TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES Tasks(id) ON DELETE CASCADE
          );

CREATE TABLE Tasks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      origin_date TEXT NOT NULL,
      modification_date TEXT,
      priority TEXT NOT NULL,
      state TEXT NOT NULL,
      stage TEXT NOT NULL,
      deadline TEXT,
      initiated_at TEXT,
      reschedule_count INTEGER DEFAULT 0,
      reschedule_1 TEXT,
      reschedule_2 TEXT,
      ended_date TEXT,
      end_note TEXT,
      days_spent INTEGER,
      is_breached_extracted INTEGER DEFAULT 0
    );

CREATE TABLE Treasury (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        flow_type TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'BORROWED',
        counterparty TEXT NOT NULL,
        amount REAL NOT NULL,
        paid_amount REAL DEFAULT 0.0,
        origin_date TEXT NOT NULL,
        promise_date TEXT,
        expected_date TEXT,
        settled_date TEXT,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        priority TEXT DEFAULT 'HIGH',
        tags TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime'))
      );

CREATE TABLE sqlite_sequence(name,seq);

CREATE INDEX idx_strikes_assigned ON Strikes(assigned);

CREATE INDEX idx_strikes_execution_date ON Strikes(execution_date);

CREATE INDEX idx_strikes_recurrence_id ON Strikes(recurrence_id);

CREATE INDEX idx_strikes_status ON Strikes(status);

CREATE INDEX idx_strikes_subtask_id ON Strikes(subtask_id);

CREATE INDEX idx_strikes_task_id ON Strikes(task_id);

CREATE INDEX idx_subtasks_task_id ON Subtasks(task_id);

CREATE INDEX idx_tags_tag_name ON Tags(tag_name);

CREATE INDEX idx_tags_task_id ON Tags(task_id);

CREATE INDEX idx_tasks_state ON Tasks(state);

CREATE INDEX idx_treasury_counterparty ON Treasury(counterparty);

CREATE INDEX idx_treasury_flow ON Treasury(flow_type, status);

CREATE INDEX idx_treasury_promise_date ON Treasury(promise_date);

CREATE INDEX idx_treasury_status ON Treasury(status);

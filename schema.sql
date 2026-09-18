-- ═══════════════════════════════════════════════════════════════════════════════
-- CAMPAIGNS AUTHORITATIVE SQLITE DATABASE BLUEPRINT
-- Standard: Zero-Time Strict DD-MM-YYYY Dates | Strict Capitalized Case | UPPERCASE Tags
-- Markdown-Lite: Multi-line rich text supported in all note/comment fields
-- ═══════════════════════════════════════════════════════════════════════════════

-- 1. COUNTERPARTIES (Directory & Trust Entity Layer)
CREATE TABLE IF NOT EXISTS Counterparties (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  name           TEXT NOT NULL UNIQUE,              -- Extensible Unique String ("Zerodha", "SBI", "Rahul", "Mom", "Client X")
  relation       TEXT NOT NULL DEFAULT 'Personal',  -- Extensible ('Personal', 'Friend', 'Family', 'Client', 'Vendor', 'Broker', 'Bank', 'Landlord', 'Other')
  activity       TEXT NOT NULL DEFAULT 'Active',    -- Strict Closed Enum: 'Active' | 'Dormant' | 'Banned' | 'Defaulted'
  contact        TEXT,                              -- Mobile / Email / Handle / UPI ID
  comment        TEXT,                              -- Markdown-Lite: Multi-line bullets, terms, bank/UPI details
  created_at     TEXT NOT NULL,                     -- Strict DD-MM-YYYY (Inception calendar date)
  updated_at     TEXT NOT NULL                      -- Strict DD-MM-YYYY (Last modified date)
);

-- 2. TREASURY (Unified Symmetrical Financial Ledger)
CREATE TABLE IF NOT EXISTS Treasury (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  counterparty_id    INTEGER NOT NULL,                  -- Foreign Key -> Counterparties(id) ON DELETE CASCADE
  title              TEXT NOT NULL,                     -- Extensible Obligation Purpose (e.g. "Laptop EMI", "Dinner Split")
  flow_type          TEXT NOT NULL DEFAULT 'Payable',   -- Strict Closed Enum: 'Payable' (Outflow) | 'Receivable' (Inflow)
  category           TEXT NOT NULL DEFAULT 'Borrowed',  -- Extensible ('Borrowed', 'Lent', 'Purchase', 'Investment', 'EMI', 'Service', 'Salary', 'Sip Investment', 'Service Bill', 'Advance Received', 'Money Lent', 'Client Invoice', 'Refund Pending', 'Reimbursement', 'Other')

  -- Financial Position
  amount             REAL NOT NULL,                     -- Total committed obligation in INR (> 0.0)
  paid_amount        REAL NOT NULL DEFAULT 0.0,         -- Cleared installment amount (0.0 to amount)
  priority           TEXT NOT NULL DEFAULT 'Medium',    -- Strict Closed Enum: 'High' | 'Medium' | 'Low'

  -- Lifecycle & State Machine
  state              TEXT NOT NULL DEFAULT 'Open',      -- Strict Closed Enum: 'Open' | 'Closed'
  status             TEXT NOT NULL DEFAULT 'In Progress',
  -- Under 'Open':   'In Progress' | 'Partially Paid' | 'Pending' | 'Disputed'
  -- Under 'Closed': 'Paid' (100% Cash) | 'Settled' (Barter/Haircut) | 'Defaulted' (Written-off)

  -- Symmetrical Opening Lifecycle
  opened_at          TEXT NOT NULL,                     -- Strict DD-MM-YYYY (Creation / handover date)
  opened_mode        TEXT NOT NULL DEFAULT 'UPI',       -- Extensible ('UPI', 'Cash', 'NetBanking', 'Card', 'Barter', 'Other')
  opened_reference   TEXT,                              -- Opening Bank UTR / Tx ID / Invoice # / Cheque #
  opened_note        TEXT,                              -- Markdown-Lite: Opening context, repayment terms, conditions

  -- Target Deadlines
  promise_date       TEXT,                              -- Hard committed return deadline (Strict DD-MM-YYYY)
  expected_date      TEXT,                              -- Soft realistic target forecast date (Strict DD-MM-YYYY)

  -- Symmetrical Closing Lifecycle
  closed_at          TEXT,                              -- Date finalized / settled (Strict DD-MM-YYYY)
  closed_mode        TEXT,                              -- Extensible ('UPI', 'Cash', 'NetBanking', 'Card', 'Barter', 'Other')
  closed_reference   TEXT,                              -- Closing settlement Bank UTR / Receipt / Tx ID
  closed_note        TEXT,                              -- Markdown-Lite: Settlement log, installment receipts, write-off reason

  -- Cross-System Grouping & Hook
  recurrence_id      TEXT DEFAULT NULL,                 -- UPPERCASE Group Tag (e.g. 'SIP-MONTHLY', 'RENT-2026')
  campaign_id        INTEGER DEFAULT NULL,              -- Optional Foreign Key -> Tasks(id) ON DELETE SET NULL

  updated_at         TEXT NOT NULL,                     -- Strict DD-MM-YYYY (Last modified date)

  FOREIGN KEY (counterparty_id) REFERENCES Counterparties(id) ON DELETE CASCADE,
  FOREIGN KEY (campaign_id) REFERENCES Tasks(id) ON DELETE SET NULL
);

-- 3. TASKS (Campaigns Master Ledger)
CREATE TABLE IF NOT EXISTS Tasks (
  id                    INTEGER PRIMARY KEY AUTOINCREMENT,
  title                 TEXT NOT NULL,                  -- Extensible Campaign Title (Auto-sanitized: No \ / : * ? " < > |)
  origin_date           TEXT NOT NULL,                  -- Strict DD-MM-YYYY (Inception calendar date)
  modification_date     TEXT,                           -- Strict DD-MM-YYYY (Last updated date)
  priority              TEXT NOT NULL,                  -- Strict Closed Enum: 'High' | 'Medium' | 'Low'
  state                 TEXT NOT NULL,                  -- Strict Closed Enum: 'Arsenal' | 'Execution' | 'Breach' | 'Archive'
  stage                 TEXT NOT NULL,                  -- Strict Closed Enum:
                                                        -- Arsenal:   'RawIntel' | 'Strategizing'
                                                        -- Execution: 'Active' | 'Executing' (Requires deadline)
                                                        -- Breach:    'Overdue' | 'Breach'
                                                        -- Archive:   'Victory' | 'Aborted'
  deadline              TEXT,                           -- Strict DD-MM-YYYY (Mandatory in Execution, >= origin_date)
  initiated_at          TEXT,                           -- Strict DD-MM-YYYY (Stamped on Execution entry)
  reschedule_count      INTEGER DEFAULT 0,              -- Non-negative postponement counter
  reschedule_1          TEXT,                           -- Strict DD-MM-YYYY (1st rescheduled deadline snapshot)
  reschedule_2          TEXT,                           -- Strict DD-MM-YYYY (2nd rescheduled deadline snapshot)
  ended_date            TEXT,                           -- Strict DD-MM-YYYY (Stamped on Archive entry)
  end_note              TEXT,                           -- Markdown-Lite: Multi-line victory report / post-mortem analysis (Keep short, clean, structured)
  days_spent            INTEGER,                        -- Total calendar days from origin to ended_date
  is_breached_extracted INTEGER DEFAULT 0,              -- Boolean: 0 | 1
  description           TEXT DEFAULT ""                 -- Markdown-Lite: Short, clean mission briefing / operational runbook (auto-seeds Obsidian manifest)
);

-- 4. SUBTASKS (Tactical Checkpoints)
CREATE TABLE IF NOT EXISTS Subtasks (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id        INTEGER NOT NULL,                      -- Foreign Key -> Tasks(id) ON DELETE CASCADE
  title          TEXT NOT NULL,                         -- Extensible Checkpoint Title (e.g. "Draft Syllabus @18-09-2026")
  created_at     TEXT NOT NULL,                         -- Strict DD-MM-YYYY (Strictly created_at, NOT creation_time)
  status         TEXT NOT NULL,                         -- Strict Closed Enum: 'Initiated' | 'Doing' | 'Completed' | 'Failed'
  FOREIGN KEY (task_id) REFERENCES Tasks(id) ON DELETE CASCADE
);

-- 5. STRIKES (Daily Tactical Directives)
CREATE TABLE IF NOT EXISTS Strikes (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  title              TEXT NOT NULL,                     -- Extensible Actionable Directive Title
  created_at         TEXT NOT NULL,                     -- Strict DD-MM-YYYY (Creation calendar date)
  execution_date     TEXT NOT NULL,                     -- Strict DD-MM-YYYY (or "" for Undated Holding Bay)
  assigned           TEXT DEFAULT 'Bhakta',             -- Strict Closed Enum: 'Adhipati' | 'Bhakta' | 'Antaryami' | 'Jigyasu' ('Shava' Locked)
  status             TEXT DEFAULT 'Standby',            -- Strict Closed Enum: 'Standby' | 'Engaged' | 'Neutralized' | 'Aborted' | 'Pending' | 'Template' | 'Undated'
                                                        -- Completion is strictly 'Neutralized' (never 'Completed' or 'Done')
  notes              TEXT,                              -- Markdown-Lite: Multi-line runbook bullets (- , 1. ), URLs, checklist
  task_id            INTEGER DEFAULT NULL,              -- Optional Foreign Key -> Tasks(id) ON DELETE CASCADE
  subtask_id         INTEGER DEFAULT NULL,              -- Optional Foreign Key -> Subtasks(id) ON DELETE CASCADE
  reschedule_count   INTEGER DEFAULT 0,                 -- Strike postponement counter
  recurrence_id      TEXT DEFAULT NULL,                 -- Habit / Fleet series ID (e.g. '30RC00001')
  FOREIGN KEY (task_id) REFERENCES Tasks(id) ON DELETE CASCADE,
  FOREIGN KEY (subtask_id) REFERENCES Subtasks(id) ON DELETE CASCADE
);

-- 6. TAGS (Classification Taxonomy)
CREATE TABLE IF NOT EXISTS Tags (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id        INTEGER DEFAULT NULL,                  -- Nullable Foreign Key -> Tasks(id) ON DELETE CASCADE (Null = Standalone system tag)
  tag_name       TEXT NOT NULL,                         -- STRICTLY UPPERCASE single-word with underscores (e.g. GOVT, MOTOR_WINDING)
  FOREIGN KEY (task_id) REFERENCES Tasks(id) ON DELETE CASCADE
);

-- Fast Production Indexes
CREATE INDEX IF NOT EXISTS idx_counterparties_name ON Counterparties(name);
CREATE INDEX IF NOT EXISTS idx_counterparties_activity ON Counterparties(activity);
CREATE INDEX IF NOT EXISTS idx_treasury_counterparty_id ON Treasury(counterparty_id);
CREATE INDEX IF NOT EXISTS idx_treasury_flow ON Treasury(flow_type, state, status);
CREATE INDEX IF NOT EXISTS idx_treasury_promise_date ON Treasury(promise_date);
CREATE INDEX IF NOT EXISTS idx_treasury_expected_date ON Treasury(expected_date);
CREATE INDEX IF NOT EXISTS idx_treasury_state ON Treasury(state);
CREATE INDEX IF NOT EXISTS idx_treasury_campaign ON Treasury(campaign_id);
CREATE INDEX IF NOT EXISTS idx_tasks_state ON Tasks(state);
CREATE INDEX IF NOT EXISTS idx_tags_task_id ON Tags(task_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag_name ON Tags(tag_name);
CREATE INDEX IF NOT EXISTS idx_subtasks_task_id ON Subtasks(task_id);
CREATE INDEX IF NOT EXISTS idx_strikes_execution_date ON Strikes(execution_date);
CREATE INDEX IF NOT EXISTS idx_strikes_status ON Strikes(status);
CREATE INDEX IF NOT EXISTS idx_strikes_assigned ON Strikes(assigned);
CREATE INDEX IF NOT EXISTS idx_strikes_task_id ON Strikes(task_id);
CREATE INDEX IF NOT EXISTS idx_strikes_subtask_id ON Strikes(subtask_id);
CREATE INDEX IF NOT EXISTS idx_strikes_recurrence_id ON Strikes(recurrence_id);

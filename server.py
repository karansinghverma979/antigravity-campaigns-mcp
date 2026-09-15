"""
Campaigns Model Context Protocol (MCP) Server
Authoritative, high-speed SQLite bridge for Karan's Campaigns Tactical Operating System.
Location: %APPDATA%\\Campaigns\\Database\\campaigns.sqlite
Strictly mirrors schema and security rules from Void/Campaigns
"""

import sys
import json
import os
import re
import sqlite3
import datetime
import traceback

DB_PATH = os.path.expandvars(r"%APPDATA%\Campaigns\Database\campaigns.sqlite")

# -----------------------------------------------------------------------------
# Strict Canonical Whitelist Definitions (From Void/Campaigns v4.0.0)
# -----------------------------------------------------------------------------

VALID_MINISTERS = ["Adhipati", "Bhakta", "Antaryami", "Jigyasu"]
VALID_STATES = ["Arsenal", "Execution", "Breach", "Archive"]

VALID_STATE_STAGES = {
    "Arsenal": ["RawIntel", "Strategizing"],
    "Execution": ["Active", "Executing"],
    "Breach": ["Overdue", "Breach"],
    "Archive": ["Victory", "Aborted"]
}

VALID_PRIORITIES = ["High", "Medium", "Low"]

# Strict Capitalized Case Standard for Database Invariants (Release-4.md)
VALID_STRIKE_STATUSES = ["Standby", "Engaged", "Neutralized", "Aborted", "Pending", "Template", "Undated"]
VALID_SUBTASK_STATUSES = ["Initiated", "Doing", "Completed", "Failed"]

# Financial / Treasury & Counterparties Whitelists
VALID_FLOW_TYPES = ["Payable", "Receivable"]
VALID_TREASURY_STATES = ["Open", "Closed", "Cancelled"]
VALID_TREASURY_STATUSES = ["In Progress", "Paid", "Partially Paid", "Settled", "Cancelled"]
VALID_RELATIONS = ["Personal", "Friend", "Family", "Client", "Vendor", "Broker", "Bank", "Other"]
VALID_ACTIVITIES = ["Active", "Dormant", "Archived"]
VALID_MODES = ["UPI", "Cash", "NetBanking", "Card", "Barter", "Other"]

VALID_TREASURY_CATEGORIES = [
    "Borrowed",
    "Sip Investment",
    "Service Bill",
    "Purchase Due",
    "Advance Received",
    "Money Lent",
    "Client Invoice",
    "Refund Pending",
    "Reimbursement",
    "Other"
]

def get_db():
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_today_str():
    return datetime.datetime.now().strftime("%d-%m-%Y")

# -----------------------------------------------------------------------------
# Security, Type-Checking & Sanitization Helpers
# -----------------------------------------------------------------------------

def sanitize_integer(val, field_name="id", required=False, allow_zero=False):
    if val is None or val == "":
        if required:
            raise ValueError(f"Security Error: '{field_name}' is required and must be a valid positive integer.")
        return None
    try:
        num = int(str(val).strip())
    except (ValueError, TypeError):
        raise ValueError(f"Security Error: '{field_name}' must be an integer, received '{val}'.")
    
    if not allow_zero and num <= 0:
        raise ValueError(f"Security Error: '{field_name}' must be a positive integer (> 0), received {num}.")
    elif allow_zero and num < 0:
        raise ValueError(f"Security Error: '{field_name}' cannot be negative, received {num}.")
    return num

def sanitize_float(val, field_name="amount", required=False, allow_zero=True):
    if val is None or val == "":
        if required:
            raise ValueError(f"Security Error: '{field_name}' is required and must be a valid numeric value.")
        return None
    try:
        num = float(str(val).strip().replace(",", ""))
    except (ValueError, TypeError):
        raise ValueError(f"Security Error: '{field_name}' must be a number, received '{val}'.")
    if not allow_zero and num <= 0:
        raise ValueError(f"Security Error: '{field_name}' must be positive (> 0), received {num}.")
    elif allow_zero and num < 0:
        raise ValueError(f"Security Error: '{field_name}' cannot be negative, received {num}.")
    return round(num, 2)

def sanitize_task_title(title):
    clean = sanitize_text(title, "title", required=True)
    clean = re.sub(r'[\\/:*?"<>|]', '', clean).strip()
    clean = re.sub(r'\s+', ' ', clean)
    if not clean:
        raise ValueError("Validation Error: Task title contains only illegal filename characters.")
    return clean

def sanitize_text(text, field_name="text", required=False, max_len=1000):
    if text is None:
        if required:
            raise ValueError(f"Validation Error: '{field_name}' is required.")
        return None
    clean = str(text).replace("\x00", "").strip()
    if required and not clean:
        raise ValueError(f"Validation Error: '{field_name}' cannot be empty or whitespace only.")
    if len(clean) > max_len:
        clean = clean[:max_len]
    return clean

def sanitize_tag_name(tag):
    if not tag:
        raise ValueError("Validation Error: Tag name cannot be empty.")
    clean = str(tag).strip().upper()
    clean = re.sub(r"[^A-Z0-9_\-\s]", "", clean).strip()
    clean = re.sub(r"\s+", "_", clean)
    if not clean:
        raise ValueError(f"Validation Error: Invalid tag name '{tag}'. Must contain alphanumeric characters.")
    if len(clean) > 50:
        clean = clean[:50]
    return clean

def parse_date_obj(date_str):
    if not date_str:
        return None
    parts = str(date_str).strip().split("-")
    if len(parts) != 3:
        return None
    try:
        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
        return datetime.date(y, m, d)
    except Exception:
        return None

def sanitize_date(date_str, field_name="date", required=False):
    if not date_str:
        if required:
            raise ValueError(f"Validation Error: '{field_name}' date is required.")
        return None
    clean = str(date_str).strip()
    parts = clean.replace("/", "-").replace(".", "-").split("-")
    if len(parts) != 3:
        raise ValueError(f"Validation Error: '{field_name}' must be formatted as DD-MM-YYYY, received '{date_str}'.")
    
    try:
        if len(parts[0]) == 4:  # YYYY-MM-DD
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        else:  # DD-MM-YYYY
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
    except (ValueError, TypeError):
        raise ValueError(f"Validation Error: '{field_name}' contains invalid non-numeric date components: '{date_str}'.")

    try:
        dt = datetime.date(year, month, day)
        return dt.strftime("%d-%m-%Y")
    except ValueError as e:
        raise ValueError(f"Security/Date Error: '{date_str}' is an invalid calendar date ({str(e)}).")

# -----------------------------------------------------------------------------
# Entity Relational Existence Checkers
# -----------------------------------------------------------------------------

def verify_task_exists(conn, task_id):
    if task_id is None:
        return
    row = conn.execute("SELECT id FROM Tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        raise ValueError(f"Relational Error: Task with ID {task_id} does not exist in the database.")

def verify_subtask_exists(conn, subtask_id):
    if subtask_id is None:
        return
    row = conn.execute("SELECT id, task_id FROM Subtasks WHERE id = ?", (subtask_id,)).fetchone()
    if not row:
        raise ValueError(f"Relational Error: Subtask with ID {subtask_id} does not exist in the database.")
    return row

def verify_strike_exists(conn, strike_id):
    if strike_id is None:
        return
    row = conn.execute("SELECT id FROM Strikes WHERE id = ?", (strike_id,)).fetchone()
    if not row:
        raise ValueError(f"Relational Error: Strike with ID {strike_id} does not exist in the database.")

def verify_counterparty_exists(conn, counterparty_id):
    if counterparty_id is None:
        return
    row = conn.execute("SELECT id, name FROM Counterparties WHERE id = ?", (counterparty_id,)).fetchone()
    if not row:
        raise ValueError(f"Relational Error: Counterparty with ID {counterparty_id} does not exist in the database.")
    return row

def verify_treasury_exists(conn, treasury_id):
    if treasury_id is None:
        return
    row = conn.execute("SELECT * FROM Treasury WHERE id = ?", (treasury_id,)).fetchone()
    if not row:
        raise ValueError(f"Relational Error: Treasury record with ID {treasury_id} does not exist in the database.")
    return row

# -----------------------------------------------------------------------------
# Strict Whitelist Validators & Intent Normalizers
# -----------------------------------------------------------------------------

def validate_minister(assigned):
    if not assigned:
        return "Bhakta"
    assigned_clean = str(assigned).strip().capitalize()
    if assigned_clean.lower() == "shava":
        raise ValueError("Tactical Absolute: 'Shava' represents Shunya (The Void). Directives cannot be assigned to Shava.")
    if assigned_clean not in VALID_MINISTERS:
        for m in VALID_MINISTERS:
            if m.lower() == assigned_clean.lower():
                return m
        raise ValueError(f"Invalid minister '{assigned}'. Allowed values: {VALID_MINISTERS}")
    return assigned_clean

def normalize_and_validate_strike_status(status):
    if not status:
        return "Standby"
    s_clean = str(status).strip().capitalize()
    alias_map = {
        "Completed": "Neutralized",
        "Done": "Neutralized",
        "Victory": "Neutralized",
        "Neutralize": "Neutralized",
        "Finish": "Neutralized",
        "Finished": "Neutralized",
        "Cancel": "Aborted",
        "Cancelled": "Aborted",
        "Failed": "Aborted",
        "Abort": "Aborted",
        "Doing": "Engaged",
        "Active": "Engaged",
        "Progress": "Engaged",
        "Plan": "Standby",
        "Todo": "Standby",
        "Holding": "Undated",
        "Holdingbay": "Undated",
        "Blueprint": "Template"
    }
    resolved = alias_map.get(s_clean, s_clean)
    if resolved not in VALID_STRIKE_STATUSES:
        raise ValueError(f"Invalid strike status '{status}'. Allowed values: {VALID_STRIKE_STATUSES}")
    return resolved

def normalize_and_validate_subtask_status(status):
    if not status:
        return "Initiated"
    s_clean = str(status).strip().capitalize()
    alias_map = {
        "Done": "Completed",
        "Finish": "Completed",
        "Finished": "Completed",
        "Neutralized": "Completed",
        "Active": "Doing",
        "Progress": "Doing",
        "In_progress": "Doing",
        "Aborted": "Failed",
        "Cancelled": "Failed",
        "Abandoned": "Failed",
        "Todo": "Initiated",
        "Plan": "Initiated",
        "Planned": "Initiated"
    }
    resolved = alias_map.get(s_clean, s_clean)
    if resolved not in VALID_SUBTASK_STATUSES:
        raise ValueError(f"Invalid subtask status '{status}'. Allowed values: {VALID_SUBTASK_STATUSES}")
    return resolved

def normalize_and_validate_priority(priority):
    if not priority:
        return "Medium"
    p_clean = str(priority).strip().capitalize()
    if p_clean in ["Med"]:
        return "Medium"
    if p_clean in ["Critical", "Urgent"]:
        return "High"
    if p_clean not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority '{priority}'. Allowed values: {VALID_PRIORITIES}")
    return p_clean

def normalize_and_validate_task_state_stage(state, stage):
    if not state:
        state = "Arsenal"
    state_clean = str(state).strip().capitalize()
    if state_clean not in VALID_STATES:
        raise ValueError(f"Invalid task state '{state}'. Allowed values: {VALID_STATES}")
    
    allowed_stages = VALID_STATE_STAGES[state_clean]
    if not stage:
        stage_clean = allowed_stages[0]
    else:
        stage_clean = str(stage).strip()
        matched = None
        for s in allowed_stages:
            if s.lower() == stage_clean.lower():
                matched = s
                break
        if not matched:
            raise ValueError(f"Invalid stage '{stage}' for state '{state_clean}'. Allowed stages for {state_clean}: {allowed_stages}")
        stage_clean = matched
        
    return state_clean, stage_clean

def normalize_and_validate_flow_type(flow_type):
    if not flow_type:
        return "Payable"
    ft = str(flow_type).strip().capitalize()
    alias_map = {"Pay": "Payable", "Due": "Payable", "Out": "Payable", "Recv": "Receivable", "In": "Receivable", "Lent": "Receivable"}
    resolved = alias_map.get(ft, ft)
    if resolved not in VALID_FLOW_TYPES:
        raise ValueError(f"Invalid flow_type '{flow_type}'. Allowed values: {VALID_FLOW_TYPES}")
    return resolved

def normalize_and_validate_treasury_category(category):
    if not category:
        return "Borrowed"
    c_clean = str(category).strip().title()
    for cat in VALID_TREASURY_CATEGORIES:
        if cat.lower() == c_clean.lower() or cat.replace(" / ", " ").lower() == c_clean.lower() or cat.replace(" ", "").lower() == c_clean.replace(" ", "").lower():
            return cat
    # Extensible: allow custom user categories in clean Capitalized/Title case
    return c_clean

def normalize_and_validate_treasury_state(state):
    if not state:
        return "Open"
    st = str(state).strip().capitalize()
    if st in ["Settled", "Paid", "Done", "Closed"]:
        return "Closed"
    if st in ["Cancelled", "Abort", "Aborted"]:
        return "Cancelled"
    if st not in VALID_TREASURY_STATES:
        raise ValueError(f"Invalid treasury state '{state}'. Allowed values: {VALID_TREASURY_STATES}")
    return st

def normalize_and_validate_payment_mode(mode):
    if not mode:
        return "UPI"
    m_clean = str(mode).strip()
    for valid in VALID_MODES:
        if valid.lower() == m_clean.lower():
            return valid
    # Extensible: allow custom user channels formatted cleanly
    return m_clean.capitalize() if len(m_clean) > 3 else m_clean.upper()

def normalize_and_validate_relation(relation):
    if not relation:
        return "Personal"
    r_clean = str(relation).strip().capitalize()
    for r in VALID_RELATIONS:
        if r.lower() == r_clean.lower():
            return r
    # Extensible: allow custom user relation categories in clean Capitalized case
    return r_clean

def normalize_and_validate_activity(activity):
    if not activity:
        return "Active"
    a_clean = str(activity).strip().capitalize()
    for a in VALID_ACTIVITIES:
        if a.lower() == a_clean.lower():
            return a
    if a_clean not in VALID_ACTIVITIES:
        raise ValueError(f"Invalid activity '{activity}'. Allowed values: {VALID_ACTIVITIES}")
    return a_clean

def extract_smart_tokens(title, execution_date=None, assigned=None):
    clean_title = sanitize_text(title, "title", required=True)
    
    # Extract #Minister
    for m in ["Adhipati", "Bhakta", "Antaryami", "Jigyasu", "Shava"]:
        match = re.search(r"#" + m + r"\b", clean_title, re.IGNORECASE)
        if match:
            assigned = m.capitalize()
            clean_title = re.sub(r"#" + m + r"\b", "", clean_title, flags=re.IGNORECASE).strip()
            break

    # Extract relative date keywords (@today, @tomorrow, @+Nd)
    now = datetime.datetime.now()
    if re.search(r"@(tomorrow|tom|tmrw)\b", clean_title, re.IGNORECASE):
        execution_date = (now + datetime.timedelta(days=1)).strftime("%d-%m-%Y")
        clean_title = re.sub(r"@(tomorrow|tom|tmrw)\b", "", clean_title, flags=re.IGNORECASE).strip()
    elif re.search(r"@(overmorrow|over|ovm)\b", clean_title, re.IGNORECASE):
        execution_date = (now + datetime.timedelta(days=2)).strftime("%d-%m-%Y")
        clean_title = re.sub(r"@(overmorrow|over|ovm)\b", "", clean_title, flags=re.IGNORECASE).strip()
    elif re.search(r"@(today|tod)\b", clean_title, re.IGNORECASE):
        execution_date = now.strftime("%d-%m-%Y")
        clean_title = re.sub(r"@(today|tod)\b", "", clean_title, flags=re.IGNORECASE).strip()
    else:
        offset_match = re.search(r"@\+(\d+)(?:d|days)?\b", clean_title, re.IGNORECASE)
        if offset_match:
            days = int(offset_match.group(1))
            execution_date = (now + datetime.timedelta(days=days)).strftime("%d-%m-%Y")
            clean_title = re.sub(r"@\+\d+(?:d|days)?\b", "", clean_title, flags=re.IGNORECASE).strip()

    clean_title = re.sub(r"\s+", " ", clean_title).strip()
    return clean_title, execution_date, assigned

# -----------------------------------------------------------------------------
# Tool Handlers (Tasks, Strikes, Subtasks, Tags)
# -----------------------------------------------------------------------------

def handle_get_dashboard(args):
    target_date = sanitize_date(args.get("target_date"), "target_date") or get_today_str()
    with get_db() as conn:
        strikes_rows = conn.execute(
            """SELECT s.*, t.title as task_title, sub.title as subtask_title
               FROM Strikes s
               LEFT JOIN Tasks t ON s.task_id = t.id
               LEFT JOIN Subtasks sub ON s.subtask_id = sub.id
               WHERE s.execution_date = ?
               ORDER BY s.id ASC""",
            (target_date,)
        ).fetchall()
        
        execution_tasks = conn.execute(
            """SELECT t.*, 
                      (SELECT COUNT(*) FROM Subtasks WHERE task_id = t.id) as subtask_count,
                      (SELECT COUNT(*) FROM Subtasks WHERE task_id = t.id AND status = 'Completed') as subtask_done_count
               FROM Tasks t
               WHERE t.state = 'Execution'
               ORDER BY t.priority DESC, t.id ASC"""
        ).fetchall()

        imminent_deadlines = conn.execute(
            """SELECT id, title, state, stage, deadline, priority
               FROM Tasks
               WHERE state IN ('Execution', 'Arsenal') AND deadline IS NOT NULL AND deadline != ''
               ORDER BY deadline ASC LIMIT 10"""
        ).fetchall()

        strikes_by_minister = {m: [] for m in VALID_MINISTERS}
        for s in strikes_rows:
            s_dict = dict(s)
            minister = s_dict.get("assigned") or "Bhakta"
            if minister in strikes_by_minister:
                strikes_by_minister[minister].append(s_dict)
            else:
                strikes_by_minister.setdefault(minister, []).append(s_dict)

        return {
            "target_date": target_date,
            "total_strikes_today": len(strikes_rows),
            "strikes_by_minister": strikes_by_minister,
            "execution_campaigns": [dict(t) for t in execution_tasks],
            "imminent_deadlines": [dict(d) for d in imminent_deadlines]
        }

def handle_list_tasks(args):
    state = args.get("state")
    stage = args.get("stage")
    priority = args.get("priority")
    search = sanitize_text(args.get("search"), "search")
    tag = args.get("tag")
    limit = sanitize_integer(args.get("limit", 50), "limit")

    query = """
        SELECT t.*, 
               (SELECT GROUP_CONCAT(tag_name, ', ') FROM Tags WHERE task_id = t.id) as tag_names,
               (SELECT COUNT(*) FROM Subtasks WHERE task_id = t.id) as total_subtasks,
               (SELECT COUNT(*) FROM Subtasks WHERE task_id = t.id AND status = 'Completed') as done_subtasks
        FROM Tasks t
        WHERE 1=1
    """
    params = []
    if state:
        state_clean = str(state).strip().capitalize()
        if state_clean not in VALID_STATES:
            raise ValueError(f"Invalid task state '{state}'. Allowed: {VALID_STATES}")
        query += " AND t.state = ?"
        params.append(state_clean)
    if stage:
        query += " AND t.stage = ?"
        params.append(stage)
    if priority:
        query += " AND t.priority = ?"
        params.append(normalize_and_validate_priority(priority))
    if search:
        query += " AND (t.title LIKE ? OR t.end_note LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if tag:
        clean_tag = sanitize_tag_name(tag)
        query += " AND EXISTS (SELECT 1 FROM Tags WHERE task_id = t.id AND tag_name LIKE ?)"
        params.append(f"%{clean_tag}%")

    query += " ORDER BY t.id DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return {"count": len(rows), "tasks": [dict(r) for r in rows]}

def handle_get_task_details(args):
    task_id = sanitize_integer(args.get("task_id"), "task_id", required=True)

    with get_db() as conn:
        task = conn.execute("SELECT * FROM Tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            return {"error": f"Task with ID {task_id} not found."}

        tags = conn.execute("SELECT * FROM Tags WHERE task_id = ?", (task_id,)).fetchall()
        subtasks = conn.execute("SELECT * FROM Subtasks WHERE task_id = ? ORDER BY id ASC", (task_id,)).fetchall()
        strikes = conn.execute(
            """SELECT s.*, sub.title as subtask_title
               FROM Strikes s
               LEFT JOIN Subtasks sub ON s.subtask_id = sub.id
               WHERE s.task_id = ? OR s.subtask_id IN (SELECT id FROM Subtasks WHERE task_id = ?)
               ORDER BY s.id ASC""",
            (task_id, task_id)
        ).fetchall()

        return {
            "task": dict(task),
            "tags": [dict(t) for t in tags],
            "subtasks": [dict(st) for st in subtasks],
            "strikes": [dict(s) for s in strikes]
        }

def handle_create_task(args):
    raw_title = sanitize_task_title(args.get("title"))

    priority = args.get("priority")
    clean_title = raw_title
    for p in ["High", "Medium", "Low"]:
        pattern = rf"#{p}\b"
        if re.search(pattern, clean_title, re.IGNORECASE):
            priority = p
            clean_title = re.sub(pattern, "", clean_title, flags=re.IGNORECASE).strip()
            break

    priority = normalize_and_validate_priority(priority)
    state, stage = normalize_and_validate_task_state_stage(args.get("state", "Arsenal"), args.get("stage"))
    origin_date = sanitize_date(args.get("origin_date"), "origin_date") or get_today_str()
    modification_date = origin_date
    deadline = sanitize_date(args.get("deadline"), "deadline")
    initiated_at = sanitize_date(args.get("initiated_at"), "initiated_at")

    if state == "Execution":
        if not deadline:
            raise ValueError("Tactical Rule Violation: A task in 'Execution' state MUST have a valid deadline.")
        if not initiated_at:
            initiated_at = origin_date

    dt_origin = parse_date_obj(origin_date)
    if initiated_at:
        dt_init = parse_date_obj(initiated_at)
        if dt_init < dt_origin:
            raise ValueError(f"Chronological Error: 'initiated_at' ({initiated_at}) cannot be earlier than 'origin_date' ({origin_date}).")
    
    if deadline:
        dt_dl = parse_date_obj(deadline)
        base_dt = parse_date_obj(initiated_at) if initiated_at else dt_origin
        if dt_dl < base_dt:
            base_str = initiated_at if initiated_at else origin_date
            raise ValueError(f"Chronological Error: 'deadline' ({deadline}) cannot be earlier than inception/initiation date ({base_str}).")

    raw_tags = args.get("tags", [])
    tags = []
    if raw_tags and isinstance(raw_tags, list):
        for t in raw_tags:
            try:
                tags.append(sanitize_tag_name(t))
            except ValueError:
                pass

    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO Tasks (title, origin_date, modification_date, priority, state, stage, deadline, initiated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (clean_title, origin_date, modification_date, priority, state, stage, deadline, initiated_at)
        )
        task_id = cur.lastrowid

        for t in tags:
            conn.execute("INSERT INTO Tags (task_id, tag_name) VALUES (?, ?)", (task_id, t))

        conn.commit()
        return {
            "success": True,
            "task_id": task_id,
            "title": clean_title,
            "state": state,
            "stage": stage,
            "priority": priority,
            "origin_date": origin_date,
            "deadline": deadline,
            "initiated_at": initiated_at,
            "tags": tags
        }

def handle_update_task(args):
    task_id = sanitize_integer(args.get("task_id"), "task_id", required=True)
    fields = args.get("fields", {})
    if not fields or not isinstance(fields, dict):
        raise ValueError("Security Error: 'fields' must be a valid key-value object.")

    allowed_columns = [
        "title", "origin_date", "modification_date", "priority", "state", "stage",
        "deadline", "initiated_at", "reschedule_count", "reschedule_1", "reschedule_2",
        "ended_date", "end_note", "days_spent", "is_breached_extracted"
    ]

    with get_db() as conn:
        verify_task_exists(conn, task_id)
        curr = conn.execute("SELECT * FROM Tasks WHERE id = ?", (task_id,)).fetchone()

        merged_state = fields.get("state", curr["state"])
        merged_stage = fields.get("stage", curr["stage"])
        valid_state, valid_stage = normalize_and_validate_task_state_stage(merged_state, merged_stage)
        if "state" in fields or "stage" in fields:
            fields["state"] = valid_state
            fields["stage"] = valid_stage

        merged_origin = sanitize_date(fields.get("origin_date"), "origin_date") if "origin_date" in fields else curr["origin_date"]
        merged_initiated = sanitize_date(fields.get("initiated_at"), "initiated_at") if "initiated_at" in fields else curr["initiated_at"]
        merged_deadline = sanitize_date(fields.get("deadline"), "deadline") if "deadline" in fields else curr["deadline"]
        merged_ended = sanitize_date(fields.get("ended_date"), "ended_date") if "ended_date" in fields else curr["ended_date"]

        if valid_state == "Execution":
            if not merged_deadline:
                raise ValueError("Tactical Rule Violation: A task in 'Execution' state MUST have a valid deadline.")
            if not merged_initiated:
                merged_initiated = get_today_str()
                fields["initiated_at"] = merged_initiated

        if valid_state == "Archive":
            if not merged_ended:
                merged_ended = get_today_str()
                fields["ended_date"] = merged_ended
            if "days_spent" not in fields and (curr["days_spent"] is None or curr["days_spent"] == 0) and merged_origin:
                dt_o = parse_date_obj(merged_origin)
                dt_e = parse_date_obj(merged_ended)
                if dt_o and dt_e:
                    fields["days_spent"] = max(0, (dt_e - dt_o).days)

        dt_origin = parse_date_obj(merged_origin)
        if merged_initiated and dt_origin:
            dt_init = parse_date_obj(merged_initiated)
            if dt_init < dt_origin:
                raise ValueError(f"Chronological Error: 'initiated_at' ({merged_initiated}) cannot be earlier than 'origin_date' ({origin_date}).")

        if merged_deadline:
            dt_dl = parse_date_obj(merged_deadline)
            base_dt = parse_date_obj(merged_initiated) if merged_initiated else dt_origin
            if base_dt and dt_dl < base_dt:
                base_str = merged_initiated if merged_initiated else merged_origin
                raise ValueError(f"Chronological Error: 'deadline' ({merged_deadline}) cannot be earlier than inception/initiation date ({base_str}).")

        if merged_ended and dt_origin:
            dt_end = parse_date_obj(merged_ended)
            if dt_end < dt_origin:
                raise ValueError(f"Chronological Error: 'ended_date' ({merged_ended}) cannot be earlier than 'origin_date' ({origin_date}).")

        if "deadline" in fields and curr["deadline"] and fields["deadline"] != curr["deadline"]:
            if "reschedule_count" not in fields:
                fields["reschedule_count"] = (curr["reschedule_count"] or 0) + 1
            if not curr["reschedule_1"]:
                fields["reschedule_1"] = curr["deadline"]
            elif not curr["reschedule_2"]:
                fields["reschedule_2"] = curr["deadline"]

        updates = []
        params = []
        for col, val in fields.items():
            if col in allowed_columns:
                if col in ["deadline", "origin_date", "modification_date", "ended_date", "reschedule_1", "reschedule_2", "initiated_at"]:
                    val = sanitize_date(val, col)
                elif col == "priority":
                    val = normalize_and_validate_priority(val)
                elif col in ["reschedule_count", "days_spent", "is_breached_extracted"]:
                    val = sanitize_integer(val, col, allow_zero=True)
                elif col == "title":
                    val = sanitize_task_title(val)
                elif col == "end_note":
                    val = sanitize_text(val, col)
                updates.append(f"{col} = ?")
                params.append(val)

        if not updates:
            raise ValueError("No valid task columns provided in fields.")

        if "modification_date" not in fields:
            updates.append("modification_date = ?")
            params.append(get_today_str())

        params.append(task_id)
        query = f"UPDATE Tasks SET {', '.join(updates)} WHERE id = ?"
        conn.execute(query, params)
        conn.commit()
        return {"success": True, "task_id": task_id, "updated_fields": list(fields.keys())}

def handle_delete_task(args):
    task_id = sanitize_integer(args.get("task_id"), "task_id", required=True)

    with get_db() as conn:
        verify_task_exists(conn, task_id)
        conn.execute("DELETE FROM Tasks WHERE id = ?", (task_id,))
        conn.commit()
        return {"success": True, "task_id": task_id, "message": f"Task {task_id} and associated subtasks/tags deleted."}

def handle_list_strikes(args):
    execution_date = sanitize_date(args.get("execution_date"), "execution_date")
    assigned = args.get("assigned")
    status = args.get("status")
    task_id = sanitize_integer(args.get("task_id"), "task_id")
    subtask_id = sanitize_integer(args.get("subtask_id"), "subtask_id")
    limit = sanitize_integer(args.get("limit", 100), "limit")

    query = """
        SELECT s.*, t.title as task_title, sub.title as subtask_title
        FROM Strikes s
        LEFT JOIN Tasks t ON s.task_id = t.id
        LEFT JOIN Subtasks sub ON s.subtask_id = sub.id
        WHERE 1=1
    """
    params = []
    if execution_date:
        query += " AND s.execution_date = ?"
        params.append(execution_date)
    if assigned:
        query += " AND s.assigned = ?"
        params.append(validate_minister(assigned))
    if status:
        query += " AND s.status = ?"
        params.append(normalize_and_validate_strike_status(status))
    if task_id:
        query += " AND s.task_id = ?"
        params.append(task_id)
    if subtask_id:
        query += " AND s.subtask_id = ?"
        params.append(subtask_id)

    query += " ORDER BY s.id DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return {"count": len(rows), "strikes": [dict(r) for r in rows]}

def handle_create_strike(args):
    raw_title = sanitize_task_title(args.get("title"))

    clean_title, execution_date, assigned = extract_smart_tokens(
        raw_title,
        execution_date=args.get("execution_date"),
        assigned=args.get("assigned")
    )

    execution_date = sanitize_date(execution_date, "execution_date") or get_today_str()
    assigned = validate_minister(assigned)
    created_at = sanitize_date(args.get("created_at"), "created_at") or get_today_str()
    status = normalize_and_validate_strike_status(args.get("status", "Standby"))
    notes = sanitize_text(args.get("notes"), "notes")
    task_id = sanitize_integer(args.get("task_id"), "task_id")
    subtask_id = sanitize_integer(args.get("subtask_id"), "subtask_id")
    recurrence_id = sanitize_text(args.get("recurrence_id"), "recurrence_id", max_len=50)

    with get_db() as conn:
        if task_id:
            verify_task_exists(conn, task_id)
        if subtask_id:
            sub = verify_subtask_exists(conn, subtask_id)
            if not task_id:
                task_id = sub["task_id"]

        cur = conn.execute(
            """INSERT INTO Strikes (title, created_at, execution_date, assigned, status, notes, task_id, subtask_id, recurrence_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (clean_title, created_at, execution_date, assigned, status, notes, task_id, subtask_id, recurrence_id)
        )
        conn.commit()
        return {
            "success": True,
            "strike_id": cur.lastrowid,
            "title": clean_title,
            "execution_date": execution_date,
            "assigned": assigned,
            "status": status,
            "task_id": task_id,
            "subtask_id": subtask_id
        }

def handle_update_strike(args):
    strike_id = sanitize_integer(args.get("strike_id"), "strike_id", required=True)
    fields = args.get("fields", {})
    if not fields or not isinstance(fields, dict):
        raise ValueError("Security Error: 'fields' must be a valid key-value object.")

    allowed_columns = ["title", "execution_date", "assigned", "status", "notes", "task_id", "subtask_id", "reschedule_count", "recurrence_id"]

    with get_db() as conn:
        verify_strike_exists(conn, strike_id)

        updates = []
        params = []
        for col, val in fields.items():
            if col in allowed_columns:
                if col == "assigned":
                    val = validate_minister(val)
                elif col == "execution_date":
                    val = sanitize_date(val, col)
                elif col == "status":
                    val = normalize_and_validate_strike_status(val)
                elif col in ["task_id", "subtask_id"]:
                    val = sanitize_integer(val, col)
                    if col == "task_id":
                        verify_task_exists(conn, val)
                    elif col == "subtask_id":
                        verify_subtask_exists(conn, val)
                elif col == "reschedule_count":
                    val = sanitize_integer(val, col, allow_zero=True)
                elif col in ["title", "notes", "recurrence_id"]:
                    val = sanitize_text(val, col)
                updates.append(f"{col} = ?")
                params.append(val)

        if not updates:
            raise ValueError("No valid strike columns provided in fields.")

        params.append(strike_id)
        query = f"UPDATE Strikes SET {', '.join(updates)} WHERE id = ?"
        conn.execute(query, params)
        conn.commit()
        return {"success": True, "strike_id": strike_id, "updated_fields": list(fields.keys())}

def handle_delete_strike(args):
    strike_id = sanitize_integer(args.get("strike_id"), "strike_id", required=True)

    with get_db() as conn:
        verify_strike_exists(conn, strike_id)
        conn.execute("DELETE FROM Strikes WHERE id = ?", (strike_id,))
        conn.commit()
        return {"success": True, "strike_id": strike_id, "message": f"Strike {strike_id} deleted."}

def handle_manage_subtask(args):
    action = sanitize_text(args.get("action"), "action", required=True).lower()

    with get_db() as conn:
        if action == "create":
            task_id = sanitize_integer(args.get("task_id"), "task_id", required=True)
            verify_task_exists(conn, task_id)
            title = sanitize_text(args.get("title"), "title", required=True)
            created_at = sanitize_date(args.get("created_at") or args.get("creation_time"), "created_at") or get_today_str()
            status = normalize_and_validate_subtask_status(args.get("status", "Initiated"))
            cur = conn.execute(
                "INSERT INTO Subtasks (task_id, title, created_at, status) VALUES (?, ?, ?, ?)",
                (task_id, title, created_at, status)
            )
            conn.commit()
            return {"success": True, "subtask_id": cur.lastrowid, "task_id": task_id, "title": title, "status": status, "created_at": created_at}

        elif action == "update":
            subtask_id = sanitize_integer(args.get("subtask_id"), "subtask_id", required=True)
            verify_subtask_exists(conn, subtask_id)
            updates = []
            params = []
            if "title" in args:
                updates.append("title = ?")
                params.append(sanitize_text(args["title"], "title", required=True))
            if "status" in args:
                updates.append("status = ?")
                params.append(normalize_and_validate_subtask_status(args["status"]))
            if "created_at" in args:
                updates.append("created_at = ?")
                params.append(sanitize_date(args["created_at"], "created_at"))
            if not updates:
                raise ValueError("title, status, or created_at required to update subtask")
            params.append(subtask_id)
            conn.execute(f"UPDATE Subtasks SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            return {"success": True, "subtask_id": subtask_id}

        elif action == "delete":
            subtask_id = sanitize_integer(args.get("subtask_id"), "subtask_id", required=True)
            verify_subtask_exists(conn, subtask_id)
            conn.execute("DELETE FROM Subtasks WHERE id = ?", (subtask_id,))
            conn.commit()
            return {"success": True, "subtask_id": subtask_id}

        elif action == "list":
            task_id = sanitize_integer(args.get("task_id"), "task_id", required=True)
            verify_task_exists(conn, task_id)
            rows = conn.execute("SELECT * FROM Subtasks WHERE task_id = ? ORDER BY id ASC", (task_id,)).fetchall()
            return {"count": len(rows), "subtasks": [dict(r) for r in rows]}

        else:
            raise ValueError(f"Unknown subtask action '{action}'. Allowed: ['create', 'update', 'delete', 'list']")

def handle_manage_tag(args):
    action = sanitize_text(args.get("action"), "action", required=True).lower()

    with get_db() as conn:
        if action == "add":
            task_id = sanitize_integer(args.get("task_id"), "task_id")
            if task_id:
                verify_task_exists(conn, task_id)
            tag_name = sanitize_tag_name(args.get("tag_name"))
            cur = conn.execute("INSERT INTO Tags (task_id, tag_name) VALUES (?, ?)", (task_id, tag_name))
            conn.commit()
            return {"success": True, "tag_id": cur.lastrowid, "task_id": task_id, "tag_name": tag_name}

        elif action == "remove":
            tag_id = sanitize_integer(args.get("tag_id"), "tag_id")
            task_id = sanitize_integer(args.get("task_id"), "task_id")
            tag_name = args.get("tag_name")
            if tag_id:
                cur = conn.execute("DELETE FROM Tags WHERE id = ?", (tag_id,))
            elif task_id and tag_name:
                clean_tag = sanitize_tag_name(tag_name)
                cur = conn.execute("DELETE FROM Tags WHERE task_id = ? AND tag_name = ?", (task_id, clean_tag))
            elif tag_name:
                clean_tag = sanitize_tag_name(tag_name)
                cur = conn.execute("DELETE FROM Tags WHERE tag_name = ?", (clean_tag,))
            else:
                raise ValueError("tag_id, (task_id and tag_name), or tag_name required for remove")
            conn.commit()
            return {"success": cur.rowcount > 0, "deleted_rows": cur.rowcount}

        elif action == "list_all":
            rows = conn.execute("SELECT DISTINCT tag_name FROM Tags ORDER BY tag_name ASC").fetchall()
            return {"tags": [r["tag_name"] for r in rows]}

        elif action == "rename":
            old_name = sanitize_tag_name(args.get("old_name"))
            new_name = sanitize_tag_name(args.get("new_name"))
            cur = conn.execute("UPDATE Tags SET tag_name = ? WHERE tag_name = ?", (new_name, old_name))
            conn.commit()
            return {"success": True, "renamed_rows": cur.rowcount, "old_name": old_name, "new_name": new_name}

        else:
            raise ValueError(f"Unknown tag action '{action}'. Allowed: ['add', 'remove', 'list_all', 'rename']")

# -----------------------------------------------------------------------------
# Financial & Treasury Tool Handlers
# -----------------------------------------------------------------------------

def handle_get_treasury_dashboard(args):
    reference_date_str = sanitize_date(args.get("reference_date"), "reference_date") or get_today_str()
    ref_dt = parse_date_obj(reference_date_str)

    with get_db() as conn:
        all_treasury = conn.execute("""
            SELECT t.*, c.name as counterparty_name, c.relation as counterparty_relation
            FROM Treasury t
            LEFT JOIN Counterparties c ON t.counterparty_id = c.id
        """).fetchall()

        total_payable_due = 0.0
        total_receivable_due = 0.0
        total_payable_settled = 0.0
        total_receivable_settled = 0.0
        open_payables = []
        open_receivables = []
        overdue_payables = []
        overdue_receivables = []

        for row in all_treasury:
            t = dict(row)
            amount = float(t.get("amount") or 0.0)
            paid_amount = float(t.get("paid_amount") or 0.0)
            balance = max(0.0, amount - paid_amount)
            t["balance_due"] = balance

            is_open = (t.get("state") or '').capitalize() == "Open"
            flow = (t.get("flow_type") or '').capitalize()

            if flow == "Payable":
                if is_open:
                    total_payable_due += balance
                    open_payables.append(t)
                    p_date = t.get("promise_date")
                    if p_date:
                        p_dt = parse_date_obj(p_date)
                        if p_dt and p_dt < ref_dt:
                            t["days_overdue"] = (ref_dt - p_dt).days
                            overdue_payables.append(t)
                else:
                    total_payable_settled += paid_amount
            elif flow == "Receivable":
                if is_open:
                    total_receivable_due += balance
                    open_receivables.append(t)
                    e_date = t.get("expected_date")
                    if e_date:
                        e_dt = parse_date_obj(e_date)
                        if e_dt and e_dt < ref_dt:
                            t["days_overdue"] = (ref_dt - e_dt).days
                            overdue_receivables.append(t)
                else:
                    total_receivable_settled += paid_amount

        net_position = total_receivable_due - total_payable_due
        cp_count = conn.execute("SELECT COUNT(*) as c FROM Counterparties").fetchone()["c"]

        return {
            "reference_date": reference_date_str,
            "metrics": {
                "total_payable_due": round(total_payable_due, 2),
                "total_receivable_due": round(total_receivable_due, 2),
                "net_position": round(net_position, 2),
                "total_payable_settled": round(total_payable_settled, 2),
                "total_receivable_settled": round(total_receivable_settled, 2),
                "open_payables_count": len(open_payables),
                "open_receivables_count": len(open_receivables),
                "overdue_payables_count": len(overdue_payables),
                "overdue_receivables_count": len(overdue_receivables),
                "total_counterparties_count": cp_count
            },
            "overdue_payables": overdue_payables[:10],
            "overdue_receivables": overdue_receivables[:10]
        }

def handle_list_treasury(args):
    flow_type = args.get("flow_type")
    state = args.get("state")
    category = args.get("category")
    counterparty_id = sanitize_integer(args.get("counterparty_id"), "counterparty_id")
    search = sanitize_text(args.get("search"), "search")
    limit = sanitize_integer(args.get("limit", 100), "limit")

    query = """
        SELECT t.*, 
               c.name as counterparty_name, 
               c.relation as counterparty_relation,
               c.activity as counterparty_activity,
               c.contact as counterparty_contact
        FROM Treasury t
        LEFT JOIN Counterparties c ON t.counterparty_id = c.id
        WHERE 1=1
    """
    params = []
    if flow_type:
        query += " AND t.flow_type = ?"
        params.append(normalize_and_validate_flow_type(flow_type))
    if state:
        query += " AND t.state = ?"
        params.append(normalize_and_validate_treasury_state(state))
    if category:
        query += " AND t.category = ?"
        params.append(normalize_and_validate_treasury_category(category))
    if counterparty_id:
        query += " AND t.counterparty_id = ?"
        params.append(counterparty_id)
    if search:
        query += " AND (t.title LIKE ? OR t.opened_note LIKE ? OR t.closed_note LIKE ? OR c.name LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])

    query += " ORDER BY t.id DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            amt = float(d.get("amount") or 0.0)
            paid = float(d.get("paid_amount") or 0.0)
            d["balance_due"] = max(0.0, round(amt - paid, 2))
            result.append(d)
        return {"count": len(result), "records": result}

def handle_manage_treasury(args):
    action = sanitize_text(args.get("action"), "action", required=True).lower()

    with get_db() as conn:
        if action == "create":
            counterparty_id = sanitize_integer(args.get("counterparty_id"), "counterparty_id")
            counterparty_name = sanitize_text(args.get("counterparty_name"), "counterparty_name")
            
            if not counterparty_id and counterparty_name:
                existing_cp = conn.execute("SELECT id FROM Counterparties WHERE name = ?", (counterparty_name,)).fetchone()
                if existing_cp:
                    counterparty_id = existing_cp["id"]
                else:
                    cur_cp = conn.execute(
                        "INSERT INTO Counterparties (name, relation, activity, created_at, updated_at) VALUES (?, 'Personal', 'Active', ?, ?)",
                        (counterparty_name, get_today_str(), get_today_str())
                    )
                    counterparty_id = cur_cp.lastrowid
            
            if not counterparty_id:
                raise ValueError("Validation Error: Either 'counterparty_id' or 'counterparty_name' is required.")
            
            verify_counterparty_exists(conn, counterparty_id)
            title = sanitize_text(args.get("title"), "title", required=True)
            flow_type = normalize_and_validate_flow_type(args.get("flow_type", "Payable"))
            category = normalize_and_validate_treasury_category(args.get("category", "Borrowed"))
            amount = sanitize_float(args.get("amount"), "amount", required=True, allow_zero=False)
            paid_amount = sanitize_float(args.get("paid_amount", 0.0), "paid_amount", allow_zero=True)
            priority = normalize_and_validate_priority(args.get("priority", "Medium"))
            state = normalize_and_validate_treasury_state(args.get("state", "Open"))
            status = "Paid" if state == "Closed" else ("Partially Paid" if paid_amount > 0 else "In Progress")
            opened_at = sanitize_date(args.get("opened_at"), "opened_at") or get_today_str()
            opened_mode = normalize_and_validate_payment_mode(args.get("opened_mode", "UPI"))
            opened_reference = sanitize_text(args.get("opened_reference"), "opened_reference")
            opened_note = sanitize_text(args.get("opened_note"), "opened_note")
            promise_date = sanitize_date(args.get("promise_date"), "promise_date")
            expected_date = sanitize_date(args.get("expected_date"), "expected_date")
            closed_at = sanitize_date(args.get("closed_at"), "closed_at")
            closed_mode = normalize_and_validate_payment_mode(args.get("closed_mode")) if args.get("closed_mode") else None
            closed_reference = sanitize_text(args.get("closed_reference"), "closed_reference")
            closed_note = sanitize_text(args.get("closed_note"), "closed_note")
            recurrence_id = sanitize_text(args.get("recurrence_id"), "recurrence_id", max_len=50)
            campaign_id = sanitize_integer(args.get("campaign_id"), "campaign_id")
            if campaign_id:
                verify_task_exists(conn, campaign_id)
            updated_at = get_today_str()

            cur = conn.execute("""
                INSERT INTO Treasury (
                    counterparty_id, title, flow_type, category, amount, paid_amount,
                    priority, state, status, opened_at, opened_mode, opened_reference,
                    opened_note, promise_date, expected_date, closed_at, closed_mode,
                    closed_reference, closed_note, recurrence_id, campaign_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                counterparty_id, title, flow_type, category, amount, paid_amount,
                priority, state, status, opened_at, opened_mode, opened_reference,
                opened_note, promise_date, expected_date, closed_at, closed_mode,
                closed_reference, closed_note, recurrence_id, campaign_id, updated_at
            ))
            conn.commit()
            return {"success": True, "treasury_id": cur.lastrowid, "title": title, "amount": amount, "flow_type": flow_type}

        elif action == "update":
            treasury_id = sanitize_integer(args.get("treasury_id"), "treasury_id", required=True)
            verify_treasury_exists(conn, treasury_id)
            fields = args.get("fields", {})
            if not fields or not isinstance(fields, dict):
                raise ValueError("Security Error: 'fields' dictionary is required.")

            allowed_cols = [
                "title", "flow_type", "category", "amount", "paid_amount", "priority",
                "state", "status", "opened_at", "opened_mode", "opened_reference",
                "opened_note", "promise_date", "expected_date", "closed_at",
                "closed_mode", "closed_reference", "closed_note", "recurrence_id",
                "campaign_id", "counterparty_id"
            ]
            updates = []
            params = []
            for col, val in fields.items():
                if col in allowed_cols:
                    if col == "counterparty_id":
                        val = sanitize_integer(val, col, required=True)
                        verify_counterparty_exists(conn, val)
                    elif col == "campaign_id":
                        val = sanitize_integer(val, col)
                        if val: verify_task_exists(conn, val)
                    elif col == "flow_type":
                        val = normalize_and_validate_flow_type(val)
                    elif col == "category":
                        val = normalize_and_validate_treasury_category(val)
                    elif col in ["amount", "paid_amount"]:
                        val = sanitize_float(val, col)
                    elif col == "priority":
                        val = normalize_and_validate_priority(val)
                    elif col == "state":
                        val = normalize_and_validate_treasury_state(val)
                    elif col in ["opened_mode", "closed_mode"]:
                        val = normalize_and_validate_payment_mode(val)
                    elif col in ["opened_at", "closed_at", "promise_date", "expected_date"]:
                        val = sanitize_date(val, col)
                    elif col in ["title", "opened_reference", "closed_reference", "opened_note", "closed_note", "recurrence_id"]:
                        val = sanitize_text(val, col)
                    updates.append(f"{col} = ?")
                    params.append(val)

            if not updates:
                raise ValueError("No valid treasury columns provided for update.")

            updates.append("updated_at = ?")
            params.append(get_today_str())
            params.append(treasury_id)
            conn.execute(f"UPDATE Treasury SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            return {"success": True, "treasury_id": treasury_id, "updated_fields": list(fields.keys())}

        elif action == "record_payment":
            treasury_id = sanitize_integer(args.get("treasury_id"), "treasury_id", required=True)
            t_curr = verify_treasury_exists(conn, treasury_id)
            
            payment_amount = sanitize_float(args.get("payment_amount"), "payment_amount", required=True, allow_zero=False)
            curr_paid = float(t_curr["paid_amount"] or 0.0)
            total_amount = float(t_curr["amount"] or 0.0)
            new_paid = curr_paid + payment_amount
            
            payment_mode = normalize_and_validate_payment_mode(args.get("payment_mode", "UPI"))
            payment_reference = sanitize_text(args.get("payment_reference"), "payment_reference")
            note = sanitize_text(args.get("note"), "note")
            today = get_today_str()

            is_settled = new_paid >= total_amount
            new_state = "Closed" if is_settled else "Open"
            new_status = "Paid" if is_settled else "Partially Paid"
            closed_at = today if is_settled else t_curr["closed_at"]
            closed_mode = payment_mode if is_settled else t_curr["closed_mode"]
            closed_ref = payment_reference if is_settled else t_curr["closed_reference"]

            existing_closed_note = t_curr["closed_note"] or ""
            payment_entry = f"• [Payment: ₹{payment_amount} via {payment_mode} on {today}" + (f" (Ref: {payment_reference})" if payment_reference else "") + (f"] {note}" if note else "")
            combined_note = (existing_closed_note + "\n" + payment_entry).strip()

            conn.execute("""
                UPDATE Treasury SET
                    paid_amount = ?,
                    state = ?,
                    status = ?,
                    closed_at = ?,
                    closed_mode = ?,
                    closed_reference = ?,
                    closed_note = ?,
                    updated_at = ?
                WHERE id = ?
            """, (new_paid, new_state, new_status, closed_at, closed_mode, closed_ref, combined_note, today, treasury_id))
            conn.commit()
            return {
                "success": True,
                "treasury_id": treasury_id,
                "paid_amount": new_paid,
                "total_amount": total_amount,
                "remaining_balance": max(0.0, total_amount - new_paid),
                "state": new_state,
                "status": new_status
            }

        elif action == "delete":
            treasury_id = sanitize_integer(args.get("treasury_id"), "treasury_id", required=True)
            verify_treasury_exists(conn, treasury_id)
            conn.execute("DELETE FROM Treasury WHERE id = ?", (treasury_id,))
            conn.commit()
            return {"success": True, "treasury_id": treasury_id, "message": f"Treasury record {treasury_id} deleted."}

        else:
            raise ValueError(f"Unknown treasury action '{action}'. Allowed: ['create', 'update', 'record_payment', 'delete']")

def handle_list_counterparties(args):
    search = sanitize_text(args.get("search"), "search")
    activity = args.get("activity")
    relation = args.get("relation")
    limit = sanitize_integer(args.get("limit", 100), "limit")

    query = """
        SELECT c.*,
               COUNT(t.id) as total_transactions,
               COALESCE(SUM(CASE WHEN t.flow_type = 'Payable' AND t.state = 'Open' THEN (t.amount - t.paid_amount) ELSE 0 END), 0) as total_payable_due,
               COALESCE(SUM(CASE WHEN t.flow_type = 'Receivable' AND t.state = 'Open' THEN (t.amount - t.paid_amount) ELSE 0 END), 0) as total_receivable_due
        FROM Counterparties c
        LEFT JOIN Treasury t ON c.id = t.counterparty_id
        WHERE 1=1
    """
    params = []
    if activity:
        query += " AND c.activity = ?"
        params.append(normalize_and_validate_activity(activity))
    if relation:
        query += " AND c.relation = ?"
        params.append(normalize_and_validate_relation(relation))
    if search:
        query += " AND (c.name LIKE ? OR c.contact LIKE ? OR c.comment LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    query += " GROUP BY c.id ORDER BY c.name ASC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["net_balance"] = round(float(d.get("total_receivable_due", 0)) - float(d.get("total_payable_due", 0)), 2)
            result.append(d)
        return {"count": len(result), "counterparties": result}

def handle_get_counterparty_dossier(args):
    counterparty_id = sanitize_integer(args.get("counterparty_id"), "counterparty_id")
    name = sanitize_text(args.get("name"), "name")

    with get_db() as conn:
        if counterparty_id:
            cp = conn.execute("SELECT * FROM Counterparties WHERE id = ?", (counterparty_id,)).fetchone()
        elif name:
            cp = conn.execute("SELECT * FROM Counterparties WHERE name LIKE ?", (f"%{name}%",)).fetchone()
        else:
            raise ValueError("Validation Error: Either 'counterparty_id' or 'name' is required.")

        if not cp:
            return {"error": "Counterparty not found."}

        cp_dict = dict(cp)
        ledger = conn.execute("""
            SELECT * FROM Treasury 
            WHERE counterparty_id = ? 
            ORDER BY id DESC
        """, (cp_dict["id"],)).fetchall()

        total_payable = 0.0
        total_receivable = 0.0
        total_paid_by_me = 0.0
        total_received_by_me = 0.0

        for r in ledger:
            amt = float(r["amount"] or 0.0)
            paid = float(r["paid_amount"] or 0.0)
            if r["flow_type"] == "Payable":
                total_payable += amt
                total_paid_by_me += paid
            else:
                total_receivable += amt
                total_received_by_me += paid

        return {
            "counterparty": cp_dict,
            "financial_summary": {
                "total_obligations_count": len(ledger),
                "total_payable_incurred": round(total_payable, 2),
                "total_paid_by_me": round(total_paid_by_me, 2),
                "current_payable_due": round(max(0.0, total_payable - total_paid_by_me), 2),
                "total_receivable_incurred": round(total_receivable, 2),
                "total_received_by_me": round(total_received_by_me, 2),
                "current_receivable_due": round(max(0.0, total_receivable - total_received_by_me), 2),
                "net_position": round((total_receivable - total_received_by_me) - (total_payable - total_paid_by_me), 2)
            },
            "ledger": [dict(r) for r in ledger]
        }

def handle_manage_counterparty(args):
    action = sanitize_text(args.get("action"), "action", required=True).lower()

    with get_db() as conn:
        if action == "create":
            name = sanitize_text(args.get("name"), "name", required=True)
            existing = conn.execute("SELECT id FROM Counterparties WHERE name = ?", (name,)).fetchone()
            if existing:
                raise ValueError(f"Relational Error: Counterparty with name '{name}' already exists (ID: {existing['id']}).")
            
            relation = normalize_and_validate_relation(args.get("relation", "Personal"))
            activity = normalize_and_validate_activity(args.get("activity", "Active"))
            contact = sanitize_text(args.get("contact"), "contact")
            comment = sanitize_text(args.get("comment"), "comment")
            created_at = sanitize_date(args.get("created_at"), "created_at") or get_today_str()
            updated_at = get_today_str()

            cur = conn.execute("""
                INSERT INTO Counterparties (name, relation, activity, contact, comment, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, relation, activity, contact, comment, created_at, updated_at))
            conn.commit()
            return {"success": True, "counterparty_id": cur.lastrowid, "name": name, "relation": relation, "activity": activity}

        elif action == "update":
            counterparty_id = sanitize_integer(args.get("counterparty_id"), "counterparty_id", required=True)
            verify_counterparty_exists(conn, counterparty_id)
            fields = args.get("fields", {})
            if not fields or not isinstance(fields, dict):
                raise ValueError("Security Error: 'fields' dictionary is required.")

            allowed_cols = ["name", "relation", "activity", "contact", "comment"]
            updates = []
            params = []
            for col, val in fields.items():
                if col in allowed_cols:
                    if col == "name":
                        val = sanitize_text(val, col, required=True)
                    elif col == "relation":
                        val = normalize_and_validate_relation(val)
                    elif col == "activity":
                        val = normalize_and_validate_activity(val)
                    elif col in ["contact", "comment"]:
                        val = sanitize_text(val, col)
                    updates.append(f"{col} = ?")
                    params.append(val)

            if not updates:
                raise ValueError("No valid counterparty fields provided for update.")

            updates.append("updated_at = ?")
            params.append(get_today_str())
            params.append(counterparty_id)
            conn.execute(f"UPDATE Counterparties SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            return {"success": True, "counterparty_id": counterparty_id, "updated_fields": list(fields.keys())}

        elif action == "delete":
            counterparty_id = sanitize_integer(args.get("counterparty_id"), "counterparty_id", required=True)
            verify_counterparty_exists(conn, counterparty_id)
            conn.execute("DELETE FROM Counterparties WHERE id = ?", (counterparty_id,))
            conn.commit()
            return {"success": True, "counterparty_id": counterparty_id, "message": f"Counterparty {counterparty_id} and all associated treasury entries deleted."}

        else:
            raise ValueError(f"Unknown counterparty action '{action}'. Allowed: ['create', 'update', 'delete']")

def handle_audit_health(args):
    reference_date_str = sanitize_date(args.get("reference_date"), "reference_date") or get_today_str()
    ref_dt = parse_date_obj(reference_date_str)

    with get_db() as conn:
        all_tasks = conn.execute("SELECT * FROM Tasks").fetchall()
        overdue_tasks = []
        missing_deadline_tasks = []
        schema_rule_violations = []
        
        for t in all_tasks:
            t_dict = dict(t)
            # 1. State & Stage validation
            state = t_dict.get("state")
            stage = t_dict.get("stage")
            priority = t_dict.get("priority")
            
            if state not in VALID_STATES:
                schema_rule_violations.append({"table": "Tasks", "id": t_dict["id"], "field": "state", "value": state, "issue": f"Invalid state '{state}'. Expected: {VALID_STATES}"})
            elif stage and stage not in VALID_STATE_STAGES.get(state, []):
                schema_rule_violations.append({"table": "Tasks", "id": t_dict["id"], "field": "stage", "value": stage, "issue": f"Invalid stage '{stage}' for state '{state}'."})
            
            if priority not in VALID_PRIORITIES:
                schema_rule_violations.append({"table": "Tasks", "id": t_dict["id"], "field": "priority", "value": priority, "issue": f"Invalid priority '{priority}'. Expected: {VALID_PRIORITIES}"})

            # 2. Date format checks
            for d_col in ["origin_date", "modification_date", "deadline", "initiated_at", "ended_date"]:
                val = t_dict.get(d_col)
                if val and parse_date_obj(val) is None:
                    schema_rule_violations.append({"table": "Tasks", "id": t_dict["id"], "field": d_col, "value": val, "issue": "Non-compliant date format. Expected strict DD-MM-YYYY."})

            if t_dict.get("state") == "Execution":
                dl = t_dict.get("deadline")
                if not dl:
                    missing_deadline_tasks.append(t_dict)
                else:
                    dl_dt = parse_date_obj(dl)
                    if dl_dt and dl_dt < ref_dt:
                        t_dict["days_overdue"] = (ref_dt - dl_dt).days
                        overdue_tasks.append(t_dict)

        all_strikes = conn.execute("SELECT * FROM Strikes").fetchall()
        stale_strikes = []
        
        for s in all_strikes:
            s_dict = dict(s)
            st_status = s_dict.get("status")
            st_assigned = s_dict.get("assigned")
            
            if st_status not in VALID_STRIKE_STATUSES:
                schema_rule_violations.append({"table": "Strikes", "id": s_dict["id"], "field": "status", "value": st_status, "issue": f"Invalid strike status '{st_status}'. Expected Capitalized Case: {VALID_STRIKE_STATUSES}"})
            if st_assigned == "Shava" or (st_assigned and st_assigned not in VALID_MINISTERS):
                schema_rule_violations.append({"table": "Strikes", "id": s_dict["id"], "field": "assigned", "value": st_assigned, "issue": f"Invalid or locked minister '{st_assigned}'."})

            for d_col in ["created_at", "execution_date"]:
                val = s_dict.get(d_col)
                if val and val != "" and parse_date_obj(val) is None:
                    schema_rule_violations.append({"table": "Strikes", "id": s_dict["id"], "field": d_col, "value": val, "issue": "Non-compliant date format. Expected strict DD-MM-YYYY."})

            ex_date = s_dict.get("execution_date")
            if ex_date:
                ex_dt = parse_date_obj(ex_date)
                if ex_dt and ex_dt < ref_dt and s_dict.get("status") in ["Standby", "Engaged", "Pending"]:
                    s_dict["days_stale"] = (ref_dt - ex_dt).days
                    stale_strikes.append(s_dict)

        # 3. Subtasks checks
        all_subtasks = conn.execute("SELECT * FROM Subtasks").fetchall()
        for sub in all_subtasks:
            sub_dict = dict(sub)
            sub_st = sub_dict.get("status")
            if sub_st not in VALID_SUBTASK_STATUSES:
                schema_rule_violations.append({"table": "Subtasks", "id": sub_dict["id"], "field": "status", "value": sub_st, "issue": f"Invalid subtask status '{sub_st}'. Expected: {VALID_SUBTASK_STATUSES}"})
            if sub_dict.get("created_at") and parse_date_obj(sub_dict.get("created_at")) is None:
                schema_rule_violations.append({"table": "Subtasks", "id": sub_dict["id"], "field": "created_at", "value": sub_dict.get("created_at"), "issue": "Non-compliant date format."})

        # 4. Tags UPPERCASE check
        all_tags = conn.execute("SELECT * FROM Tags").fetchall()
        for tg in all_tags:
            tg_dict = dict(tg)
            name = tg_dict.get("tag_name", "")
            if name != name.upper() or " " in name:
                schema_rule_violations.append({"table": "Tags", "id": tg_dict["id"], "field": "tag_name", "value": name, "issue": "Tags must be STRICTLY UPPERCASE single-word with underscores."})

        # 5. Treasury checks
        all_treasury = conn.execute("SELECT * FROM Treasury").fetchall()
        for tr in all_treasury:
            tr_dict = dict(tr)
            ft = tr_dict.get("flow_type")
            st = tr_dict.get("state")
            status = tr_dict.get("status")
            prio = tr_dict.get("priority")
            
            if ft not in VALID_FLOW_TYPES:
                schema_rule_violations.append({"table": "Treasury", "id": tr_dict["id"], "field": "flow_type", "value": ft, "issue": f"Invalid flow_type '{ft}'."})
            if st not in VALID_TREASURY_STATES:
                schema_rule_violations.append({"table": "Treasury", "id": tr_dict["id"], "field": "state", "value": st, "issue": f"Invalid state '{st}'."})
            if prio not in VALID_PRIORITIES:
                schema_rule_violations.append({"table": "Treasury", "id": tr_dict["id"], "field": "priority", "value": prio, "issue": f"Invalid priority '{prio}'."})

            for d_col in ["opened_at", "closed_at", "promise_date", "expected_date", "updated_at"]:
                val = tr_dict.get(d_col)
                if val and parse_date_obj(val) is None:
                    schema_rule_violations.append({"table": "Treasury", "id": tr_dict["id"], "field": d_col, "value": val, "issue": "Non-compliant date format."})

        # 6. Counterparties activity check
        all_cp = conn.execute("SELECT * FROM Counterparties").fetchall()
        for cp in all_cp:
            cp_dict = dict(cp)
            act = cp_dict.get("activity")
            if act not in VALID_ACTIVITIES:
                schema_rule_violations.append({"table": "Counterparties", "id": cp_dict["id"], "field": "activity", "value": act, "issue": f"Invalid activity '{act}'."})
            for d_col in ["created_at", "updated_at"]:
                val = cp_dict.get(d_col)
                if val and parse_date_obj(val) is None:
                    schema_rule_violations.append({"table": "Counterparties", "id": cp_dict["id"], "field": d_col, "value": val, "issue": "Non-compliant date format."})

        # 7. Production Index Presence Verification
        required_indexes = [
            "idx_counterparties_name", "idx_counterparties_activity",
            "idx_treasury_counterparty_id", "idx_treasury_flow", "idx_treasury_promise_date", "idx_treasury_expected_date", "idx_treasury_state",
            "idx_tasks_state", "idx_tags_task_id", "idx_tags_tag_name", "idx_subtasks_task_id",
            "idx_strikes_execution_date", "idx_strikes_status", "idx_strikes_assigned", "idx_strikes_task_id", "idx_strikes_subtask_id", "idx_strikes_recurrence_id"
        ]
        existing_indexes = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
        missing_indexes = [idx for idx in required_indexes if idx not in existing_indexes]

        # 8. Relational Integrity Checks (Foreign Keys)
        orphan_subtasks = conn.execute("""
            SELECT s.* FROM Subtasks s
            LEFT JOIN Tasks t ON s.task_id = t.id
            WHERE t.id IS NULL
        """).fetchall()

        orphan_strikes = conn.execute("""
            SELECT s.* FROM Strikes s
            LEFT JOIN Tasks t ON s.task_id = t.id
            WHERE s.task_id IS NOT NULL AND t.id IS NULL
        """).fetchall()

        orphan_treasury = conn.execute("""
            SELECT tr.* FROM Treasury tr
            LEFT JOIN Counterparties c ON tr.counterparty_id = c.id
            WHERE c.id IS NULL
        """).fetchall()

        orphan_tags = conn.execute("""
            SELECT tg.* FROM Tags tg
            LEFT JOIN Tasks t ON tg.task_id = t.id
            WHERE tg.task_id IS NOT NULL AND t.id IS NULL
        """).fetchall()

        issues_count = (
            len(overdue_tasks) + len(missing_deadline_tasks) + len(stale_strikes) +
            len(schema_rule_violations) + len(missing_indexes) +
            len(orphan_subtasks) + len(orphan_strikes) + len(orphan_treasury) + len(orphan_tags)
        )
        
        if issues_count == 0:
            health_status = "OPTIMAL_HEALTH"
            summary = "All campaigns, daily strikes, counterparties, treasury obligations, schema rules, and database indexes are 100% compliant and healthy."
        elif len(schema_rule_violations) > 0 or len(missing_indexes) > 0 or len(orphan_subtasks) > 0 or len(orphan_strikes) > 0 or len(orphan_treasury) > 0:
            health_status = "ATTENTION_REQUIRED"
            summary = f"Detected {len(schema_rule_violations)} schema violations, {len(missing_indexes)} missing indexes, {len(overdue_tasks)} overdue campaigns, and {len(stale_strikes)} stale strikes."
        else:
            health_status = "MINOR_DRIFT"
            summary = f"Detected {len(stale_strikes)} stale strikes or {len(overdue_tasks)} overdue tasks needing routine resolution."

        remediations = []
        if schema_rule_violations:
            remediations.append(f"Fix {len(schema_rule_violations)} column value/casing/date violations across tables.")
        if missing_indexes:
            remediations.append(f"Create {len(missing_indexes)} missing performance indexes: {missing_indexes}.")
        if overdue_tasks:
            remediations.append(f"Reschedule or transition {len(overdue_tasks)} overdue campaigns to Breach/Archive.")
        if stale_strikes:
            remediations.append(f"Neutralize, reschedule, or abort {len(stale_strikes)} past strikes.")
        if missing_deadline_tasks:
            remediations.append(f"Assign mandatory deadlines to {len(missing_deadline_tasks)} active execution campaigns.")
        if orphan_subtasks or orphan_strikes or orphan_treasury or orphan_tags:
            remediations.append("Prune or re-link orphaned records.")

        return {
            "reference_date": reference_date_str,
            "health_status": health_status,
            "issues_count": issues_count,
            "summary": summary,
            "schema_rule_violations": schema_rule_violations,
            "missing_indexes": missing_indexes,
            "overdue_tasks": overdue_tasks,
            "missing_deadline_tasks": missing_deadline_tasks,
            "stale_strikes": stale_strikes,
            "orphaned_entities": {
                "subtasks": [dict(r) for r in orphan_subtasks],
                "strikes": [dict(r) for r in orphan_strikes],
                "treasury": [dict(r) for r in orphan_treasury],
                "tags": [dict(r) for r in orphan_tags]
            },
            "remediation_actions": remediations
        }

def handle_execute_sql(args):
    query = sanitize_text(args.get("query"), "query", required=True, max_len=5000)
    params = args.get("params", [])
    if not isinstance(params, list):
        raise ValueError("Security Error: 'params' must be a JSON array of positional values.")
    write_operation = bool(args.get("write_operation", False))

    with get_db() as conn:
        try:
            cur = conn.execute(query, params)
            if write_operation:
                conn.commit()
                return {
                    "success": True,
                    "rows_affected": cur.rowcount,
                    "last_insert_id": cur.lastrowid
                }
            else:
                rows = cur.fetchall()
                return {
                    "success": True,
                    "count": len(rows),
                    "rows": [dict(r) for r in rows]
                }
        except Exception as e:
            if write_operation:
                conn.rollback()
            raise

# -----------------------------------------------------------------------------
# Tool Schemas with Strict Enum Constraints (20 Operations)
# -----------------------------------------------------------------------------

TOOLS = [
    {
        "name": "campaigns_audit_health",
        "description": "Perform an instant, comprehensive system health scan: detects overdue campaigns, stale pending strikes, missing deadlines, and broken relational foreign keys.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reference_date": {"type": "string", "description": "Optional DD-MM-YYYY reference date for audit. Defaults to today."}
            }
        }
    },
    {
        "name": "campaigns_get_dashboard",
        "description": "Get a comprehensive 1-shot situational briefing: strikes for target date grouped by Minister (Adhipati, Bhakta, Antaryami, Jigyasu), active Execution campaigns, and upcoming deadlines.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_date": {"type": "string", "description": "Optional DD-MM-YYYY date. Defaults to today."}
            }
        }
    },
    {
        "name": "campaigns_list_tasks",
        "description": "List and filter tactical campaigns across states (Arsenal, Execution, Breach, Archive), stages, priorities, or tags.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "state": {"type": "string", "enum": ["Arsenal", "Execution", "Breach", "Archive"], "description": "Filter by task state."},
                "stage": {"type": "string", "enum": ["RawIntel", "Strategizing", "Active", "Executing", "Overdue", "Victory", "Aborted"], "description": "Filter by stage."},
                "priority": {"type": "string", "enum": ["High", "Medium", "Low"], "description": "Filter by priority."},
                "search": {"type": "string", "description": "Substring search in task title or notes."},
                "tag": {"type": "string", "description": "Filter tasks containing this tag name."},
                "limit": {"type": "integer", "description": "Max tasks to return (default 50)."}
            }
        }
    },
    {
        "name": "campaigns_get_task_details",
        "description": "Fetch the full interconnected relational tree for a specific campaign: Task record, all subtasks, all strikes (direct and nested), and tags.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "Unique positive ID of the task."}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "campaigns_create_task",
        "description": "Create a new campaign task in the SQLite database with strict state/stage validation, calendar date bounds, priority extraction, and initial tag associations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title (supports inline #high, #med, #low)."},
                "priority": {"type": "string", "enum": ["High", "Medium", "Low", "high", "med", "low"], "default": "Medium", "description": "Priority level."},
                "state": {"type": "string", "enum": ["Arsenal", "Execution", "Breach", "Archive"], "default": "Arsenal"},
                "stage": {"type": "string", "enum": ["RawIntel", "Strategizing", "Active", "Executing", "Overdue", "Victory", "Aborted"], "default": "RawIntel"},
                "origin_date": {"type": "string", "description": "DD-MM-YYYY date. Defaults to today."},
                "deadline": {"type": "string", "description": "Optional DD-MM-YYYY deadline."},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "List of tag names (e.g. ['GOVT', 'RECRUITMENT'])."}
            },
            "required": ["title"]
        }
    },
    {
        "name": "campaigns_update_task",
        "description": "Update any column on an existing campaign task record with strict state/stage compatibility and relational verification.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "Task ID to update."},
                "fields": {
                    "type": "object",
                    "description": "Key-value dictionary of task columns to update.",
                    "properties": {
                        "title": {"type": "string"},
                        "state": {"type": "string", "enum": ["Arsenal", "Execution", "Breach", "Archive"]},
                        "stage": {"type": "string", "enum": ["RawIntel", "Strategizing", "Active", "Executing", "Overdue", "Victory", "Aborted"]},
                        "priority": {"type": "string", "enum": ["High", "Medium", "Low", "high", "med", "low"]},
                        "deadline": {"type": "string"},
                        "reschedule_count": {"type": "integer"},
                        "ended_date": {"type": "string"},
                        "end_note": {"type": "string"},
                        "days_spent": {"type": "integer"}
                    }
                }
            },
            "required": ["task_id", "fields"]
        }
    },
    {
        "name": "campaigns_delete_task",
        "description": "Permanently delete a campaign task and cascade delete its subtasks, tags, and linked records.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer", "description": "Task ID to delete."}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "campaigns_list_strikes",
        "description": "List strikes and daily tactical directives filtered by execution date, assigned Minister, status, or task/subtask connection.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "execution_date": {"type": "string", "description": "DD-MM-YYYY execution date."},
                "assigned": {"type": "string", "enum": ["Adhipati", "Bhakta", "Antaryami", "Jigyasu"], "description": "Assigned Minister entity."},
                "status": {"type": "string", "enum": ["Standby", "Engaged", "Neutralized", "Aborted", "Pending", "Template", "Undated"], "description": "Strike status."},
                "task_id": {"type": "integer", "description": "Filter by connected task ID."},
                "subtask_id": {"type": "integer", "description": "Filter by connected subtask ID."},
                "limit": {"type": "integer", "default": 100}
            }
        }
    },
    {
        "name": "campaigns_create_strike",
        "description": "Schedule a daily strike/directive. Enforces calendar date bounds, relational ID verification, strict Minister whitelist (Adhipati, Bhakta, Antaryami, Jigyasu), and valid statuses (Standby, Engaged, Neutralized, Aborted, Pending, Template, Undated).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Strike action title (supports inline @today, @tomorrow, #Minister)."},
                "execution_date": {"type": "string", "description": "DD-MM-YYYY target date (defaults to today or parsed from title)."},
                "assigned": {"type": "string", "enum": ["Adhipati", "Bhakta", "Antaryami", "Jigyasu"], "default": "Bhakta", "description": "Assigned Minister."},
                "status": {"type": "string", "enum": ["Standby", "Engaged", "Neutralized", "Aborted", "Pending", "Template", "Undated"], "default": "Standby"},
                "notes": {"type": "string", "description": "Optional tactical notes."},
                "task_id": {"type": "integer", "description": "Optional linked task ID."},
                "subtask_id": {"type": "integer", "description": "Optional linked subtask ID."},
                "recurrence_id": {"type": "string", "description": "Optional recurrence identifier."}
            },
            "required": ["title"]
        }
    },
    {
        "name": "campaigns_update_strike",
        "description": "Update any attribute of an existing strike with relational checking, strict status (Standby, Engaged, Neutralized, Aborted, Pending, Template, Undated) and Minister validation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "strike_id": {"type": "integer", "description": "Strike ID to update."},
                "fields": {
                    "type": "object",
                    "description": "Attributes to update.",
                    "properties": {
                        "status": {"type": "string", "enum": ["Standby", "Engaged", "Neutralized", "Aborted", "Pending", "Template", "Undated"]},
                        "assigned": {"type": "string", "enum": ["Adhipati", "Bhakta", "Antaryami", "Jigyasu"]},
                        "execution_date": {"type": "string"},
                        "title": {"type": "string"},
                        "notes": {"type": "string"},
                        "reschedule_count": {"type": "integer"},
                        "task_id": {"type": "integer"},
                        "subtask_id": {"type": "integer"}
                    }
                }
            },
            "required": ["strike_id", "fields"]
        }
    },
    {
        "name": "campaigns_delete_strike",
        "description": "Delete a strike / directive record by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "strike_id": {"type": "integer", "description": "Strike ID to delete."}
            },
            "required": ["strike_id"]
        }
    },
    {
        "name": "campaigns_manage_subtask",
        "description": "Create, update, delete, or list subtask milestones with strict relational existence checks and status validation (Initiated, Doing, Completed, Failed).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create", "update", "delete", "list"], "description": "Subtask action to perform."},
                "task_id": {"type": "integer", "description": "Parent task ID."},
                "subtask_id": {"type": "integer", "description": "Subtask ID (for update/delete)."},
                "title": {"type": "string", "description": "Subtask title."},
                "created_at": {"type": "string", "description": "DD-MM-YYYY creation date."},
                "status": {"type": "string", "enum": ["Initiated", "Doing", "Completed", "Failed"], "description": "Subtask status."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "campaigns_manage_tag",
        "description": "Manage categorical tags: add to task or dictionary, remove, rename globally, or list all distinct tags with alphanumeric sanitization.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["add", "remove", "list_all", "rename"], "description": "Tag action to perform."},
                "task_id": {"type": "integer", "description": "Task ID for add/remove."},
                "tag_name": {"type": "string", "description": "Tag name."},
                "tag_id": {"type": "integer", "description": "Tag record ID (for remove)."},
                "old_name": {"type": "string", "description": "Old tag name (for rename)."},
                "new_name": {"type": "string", "description": "New tag name (for rename)."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "campaigns_get_treasury_dashboard",
        "description": "Get high-level 1-shot financial situational HUD: total payables due, receivables due, net balance position, overdue obligations, and counterparties overview.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reference_date": {"type": "string", "description": "Optional DD-MM-YYYY date. Defaults to today."}
            }
        }
    },
    {
        "name": "campaigns_list_treasury",
        "description": "Query and filter financial obligations: filter by flow_type (Payable/Receivable), state (Open/Closed/Cancelled), category, counterparty_id, or search string.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "flow_type": {"type": "string", "enum": ["Payable", "Receivable"], "description": "Flow direction."},
                "state": {"type": "string", "enum": ["Open", "Closed", "Cancelled"], "description": "Financial state."},
                "category": {"type": "string", "description": "Obligation category."},
                "counterparty_id": {"type": "integer", "description": "Filter by counterparty record ID."},
                "search": {"type": "string", "description": "Search keyword in title, notes, or counterparty name."},
                "limit": {"type": "integer", "default": 100}
            }
        }
    },
    {
        "name": "campaigns_manage_treasury",
        "description": "Create, update, record payment (partial or full), or delete treasury obligations with strict 4-pillar relational schema enforcement.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create", "update", "record_payment", "delete"], "description": "Treasury action to perform."},
                "treasury_id": {"type": "integer", "description": "Treasury obligation ID (for update, record_payment, delete)."},
                "counterparty_id": {"type": "integer", "description": "Target counterparty ID (for create)."},
                "counterparty_name": {"type": "string", "description": "Counterparty name (for create, will find or auto-create if ID omitted)."},
                "title": {"type": "string", "description": "Obligation title / purpose."},
                "flow_type": {"type": "string", "enum": ["Payable", "Receivable"], "default": "Payable"},
                "category": {"type": "string", "description": "Category (e.g. Borrowed, Sip Investment, Service Bill, Client Invoice)."},
                "amount": {"type": "number", "description": "Total principal amount in INR."},
                "paid_amount": {"type": "number", "default": 0.0, "description": "Paid amount so far."},
                "priority": {"type": "string", "enum": ["High", "Medium", "Low"], "default": "Medium"},
                "state": {"type": "string", "enum": ["Open", "Closed", "Cancelled"], "default": "Open"},
                "opened_at": {"type": "string", "description": "DD-MM-YYYY creation date."},
                "opened_mode": {"type": "string", "enum": ["UPI", "Cash", "NetBanking", "Card", "Barter", "Other"], "default": "UPI"},
                "opened_reference": {"type": "string", "description": "Txn ID / invoice number."},
                "opened_note": {"type": "string", "description": "Inception context / terms."},
                "promise_date": {"type": "string", "description": "DD-MM-YYYY commitment date."},
                "expected_date": {"type": "string", "description": "DD-MM-YYYY expected realization date."},
                "payment_amount": {"type": "number", "description": "Amount being paid now (for record_payment action)."},
                "payment_mode": {"type": "string", "enum": ["UPI", "Cash", "NetBanking", "Card", "Barter", "Other"], "default": "UPI"},
                "payment_reference": {"type": "string", "description": "Txn reference for this payment."},
                "note": {"type": "string", "description": "Payment note."},
                "fields": {"type": "object", "description": "Key-value dictionary of fields to update (for update action)."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "campaigns_list_counterparties",
        "description": "List counterparties with live computed net balances, total payable dues, and total receivable dues.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search in counterparty name, contact, or comment."},
                "activity": {"type": "string", "enum": ["Active", "Dormant", "Archived"], "description": "Filter by activity."},
                "relation": {"type": "string", "enum": ["Personal", "Friend", "Family", "Client", "Vendor", "Broker", "Bank", "Other"], "description": "Filter by relation."},
                "limit": {"type": "integer", "default": 100}
            }
        }
    },
    {
        "name": "campaigns_get_counterparty_dossier",
        "description": "Fetch deep 360-degree relationship profile and full transactional ledger for a specific counterparty.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "counterparty_id": {"type": "integer", "description": "Counterparty ID."},
                "name": {"type": "string", "description": "Counterparty name (fuzzy match)."}
            }
        }
    },
    {
        "name": "campaigns_manage_counterparty",
        "description": "Create, update, or delete counterparties in the relational directory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create", "update", "delete"], "description": "Counterparty action."},
                "counterparty_id": {"type": "integer", "description": "Counterparty ID (for update, delete)."},
                "name": {"type": "string", "description": "Counterparty name (unique)."},
                "relation": {"type": "string", "enum": ["Personal", "Friend", "Family", "Client", "Vendor", "Broker", "Bank", "Other"], "default": "Personal"},
                "activity": {"type": "string", "enum": ["Active", "Dormant", "Archived"], "default": "Active"},
                "contact": {"type": "string", "description": "Phone / email / UPI handle."},
                "comment": {"type": "string", "description": "Context notes."},
                "fields": {"type": "object", "description": "Key-value dictionary of fields to update."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "campaigns_execute_sql",
        "description": "Execute unrestricted custom SQL queries or multi-table transactions directly on the campaigns.sqlite database with full schema access and transaction rollback safety.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SQL query string."},
                "params": {"type": "array", "description": "Positional parameter values for ? placeholders."},
                "write_operation": {"type": "boolean", "default": False, "description": "Set true for INSERT, UPDATE, DELETE, or DDL statements."}
            },
            "required": ["query"]
        }
    }
]

DISPATCH_MAP = {
    "campaigns_audit_health": handle_audit_health,
    "campaigns_get_dashboard": handle_get_dashboard,
    "campaigns_list_tasks": handle_list_tasks,
    "campaigns_get_task_details": handle_get_task_details,
    "campaigns_create_task": handle_create_task,
    "campaigns_update_task": handle_update_task,
    "campaigns_delete_task": handle_delete_task,
    "campaigns_list_strikes": handle_list_strikes,
    "campaigns_create_strike": handle_create_strike,
    "campaigns_update_strike": handle_update_strike,
    "campaigns_delete_strike": handle_delete_strike,
    "campaigns_manage_subtask": handle_manage_subtask,
    "campaigns_manage_tag": handle_manage_tag,
    "campaigns_get_treasury_dashboard": handle_get_treasury_dashboard,
    "campaigns_list_treasury": handle_list_treasury,
    "campaigns_manage_treasury": handle_manage_treasury,
    "campaigns_list_counterparties": handle_list_counterparties,
    "campaigns_get_counterparty_dossier": handle_get_counterparty_dossier,
    "campaigns_manage_counterparty": handle_manage_counterparty,
    "campaigns_execute_sql": handle_execute_sql
}

def send_json(payload):
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()

def handle_jsonrpc(line):
    if not line.strip():
        return
    try:
        req = json.loads(line)
    except Exception as e:
        send_json({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {str(e)}"}})
        return

    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})

    if method == "initialize":
        send_json({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "campaigns-mcp",
                    "version": "2.0.0"
                }
            }
        })
    elif method == "notifications/initialized":
        pass
    elif method == "tools/list":
        send_json({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS
            }
        })
    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        if tool_name not in DISPATCH_MAP:
            send_json({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool '{tool_name}' not found."}
            })
            return

        try:
            handler = DISPATCH_MAP[tool_name]
            res_data = handler(tool_args)
            send_json({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(res_data, indent=2, default=str)
                        }
                    ],
                    "isError": False
                }
            })
        except Exception as err:
            err_details = traceback.format_exc()
            send_json({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error in '{tool_name}': {str(err)}\n\n{err_details}"
                        }
                    ],
                    "isError": True
                }
            })
    elif method == "ping":
        send_json({"jsonrpc": "2.0", "id": req_id, "result": {}})
    else:
        if req_id is not None:
            send_json({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method '{method}' not implemented."}
            })

def main():
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    for line in sys.stdin:
        handle_jsonrpc(line)

if __name__ == "__main__":
    main()

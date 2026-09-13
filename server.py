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
# Strict Canonical Whitelist Definitions (From Void/Campaigns)
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
VALID_STRIKE_STATUSES = ["STANDBY", "ENGAGED", "NEUTRALIZED", "ABORTED", "PENDING", "TEMPLATE", "UNDATED"]
VALID_SUBTASK_STATUSES = ["Initiated", "Doing", "Completed", "Failed"]

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

def sanitize_task_title(title):
    clean = sanitize_text(title, "title", required=True)
    # Strip illegal Windows/Obsidian filename characters: \ / : * ? " < > |
    clean = re.sub(r'[\\/:*?"<>|]', '', clean).strip()
    clean = re.sub(r'\s+', ' ', clean)
    if not clean:
        raise ValueError("Validation Error: Task title contains only illegal filename characters.")
    return clean

def sanitize_text(text, field_name="text", required=False, max_len=500):
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

def is_valid_calendar_date(day, month, year):
    if not (1 <= month <= 12 and 1000 <= year <= 9999 and 1 <= day <= 31):
        return False
    # Days per month check
    days_in_month = [31, 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return day <= days_in_month[month - 1]

def parse_date_obj(date_str):
    if not date_str:
        return None
    d, m, y = [int(p) for p in date_str.split("-")]
    return datetime.date(y, m, d)

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
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
        else:  # DD-MM-YYYY
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])
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
        return "STANDBY"
    s_upper = str(status).strip().upper()
    alias_map = {
        "COMPLETED": "NEUTRALIZED",
        "DONE": "NEUTRALIZED",
        "VICTORY": "NEUTRALIZED",
        "NEUTRALIZE": "NEUTRALIZED",
        "FINISH": "NEUTRALIZED",
        "FINISHED": "NEUTRALIZED",
        "CANCEL": "ABORTED",
        "CANCELLED": "ABORTED",
        "FAILED": "ABORTED",
        "ABORT": "ABORTED",
        "DOING": "ENGAGED",
        "ACTIVE": "ENGAGED",
        "PROGRESS": "ENGAGED",
        "PLAN": "STANDBY",
        "TODO": "STANDBY"
    }
    resolved = alias_map.get(s_upper, s_upper)
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
# Tool Handlers
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

    # Tactical Invariant: Execution State Mandates a Valid Deadline
    if state == "Execution":
        if not deadline:
            raise ValueError("Tactical Rule Violation: A task in 'Execution' state MUST have a valid deadline.")
        if not initiated_at:
            initiated_at = origin_date

    # Chronological Invariant Verifications
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

        # Handle state/stage pairing
        merged_state = fields.get("state", curr["state"])
        merged_stage = fields.get("stage", curr["stage"])
        valid_state, valid_stage = normalize_and_validate_task_state_stage(merged_state, merged_stage)
        if "state" in fields or "stage" in fields:
            fields["state"] = valid_state
            fields["stage"] = valid_stage

        # Extract merged dates for chronological validation
        merged_origin = sanitize_date(fields.get("origin_date"), "origin_date") if "origin_date" in fields else curr["origin_date"]
        merged_initiated = sanitize_date(fields.get("initiated_at"), "initiated_at") if "initiated_at" in fields else curr["initiated_at"]
        merged_deadline = sanitize_date(fields.get("deadline"), "deadline") if "deadline" in fields else curr["deadline"]
        merged_ended = sanitize_date(fields.get("ended_date"), "ended_date") if "ended_date" in fields else curr["ended_date"]

        # Tactical Invariant: Moving into / remaining in Execution requires a Deadline
        if valid_state == "Execution":
            if not merged_deadline:
                raise ValueError("Tactical Rule Violation: A task in 'Execution' state MUST have a valid deadline.")
            if not merged_initiated:
                merged_initiated = get_today_str()
                fields["initiated_at"] = merged_initiated

        # Tactical Invariant: Moving into Archive auto-sets ended_date & days_spent
        if valid_state == "Archive":
            if not merged_ended:
                merged_ended = get_today_str()
                fields["ended_date"] = merged_ended
            if "days_spent" not in fields and (curr["days_spent"] is None or curr["days_spent"] == 0) and merged_origin:
                dt_o = parse_date_obj(merged_origin)
                dt_e = parse_date_obj(merged_ended)
                if dt_o and dt_e:
                    fields["days_spent"] = max(0, (dt_e - dt_o).days)

        # Chronological Invariant Verifications
        dt_origin = parse_date_obj(merged_origin)
        if merged_initiated and dt_origin:
            dt_init = parse_date_obj(merged_initiated)
            if dt_init < dt_origin:
                raise ValueError(f"Chronological Error: 'initiated_at' ({merged_initiated}) cannot be earlier than 'origin_date' ({merged_origin}).")

        if merged_deadline:
            dt_dl = parse_date_obj(merged_deadline)
            base_dt = parse_date_obj(merged_initiated) if merged_initiated else dt_origin
            if base_dt and dt_dl < base_dt:
                base_str = merged_initiated if merged_initiated else merged_origin
                raise ValueError(f"Chronological Error: 'deadline' ({merged_deadline}) cannot be earlier than inception/initiation date ({base_str}).")

        if merged_ended and dt_origin:
            dt_end = parse_date_obj(merged_ended)
            if dt_end < dt_origin:
                raise ValueError(f"Chronological Error: 'ended_date' ({merged_ended}) cannot be earlier than 'origin_date' ({merged_origin}).")

        # Reschedule Tracking: If deadline was modified
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
    status = normalize_and_validate_strike_status(args.get("status", "STANDBY"))
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
            creation_time = sanitize_date(args.get("creation_time"), "creation_time") or get_today_str()
            status = normalize_and_validate_subtask_status(args.get("status", "Initiated"))
            cur = conn.execute(
                "INSERT INTO Subtasks (task_id, title, creation_time, status) VALUES (?, ?, ?, ?)",
                (task_id, title, creation_time, status)
            )
            conn.commit()
            return {"success": True, "subtask_id": cur.lastrowid, "task_id": task_id, "title": title, "status": status}

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
            if not updates:
                raise ValueError("title or status required to update subtask")
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
            task_id = sanitize_integer(args.get("task_id"), "task_id", required=True)
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

def handle_audit_health(args):
    reference_date_str = sanitize_date(args.get("reference_date"), "reference_date") or get_today_str()
    ref_dt = parse_date_obj(reference_date_str)

    with get_db() as conn:
        # 1. Overdue Execution Campaigns (state == 'Execution' and deadline < reference_date)
        all_tasks = conn.execute("SELECT * FROM Tasks").fetchall()
        overdue_tasks = []
        missing_deadline_tasks = []
        
        for t in all_tasks:
            t_dict = dict(t)
            if t_dict["state"] == "Execution":
                dl = t_dict.get("deadline")
                if not dl:
                    missing_deadline_tasks.append(t_dict)
                else:
                    dl_dt = parse_date_obj(dl)
                    if dl_dt and dl_dt < ref_dt:
                        t_dict["days_overdue"] = (ref_dt - dl_dt).days
                        overdue_tasks.append(t_dict)

        # 2. Stale Strikes (execution_date < reference_date and status IN ('STANDBY', 'ENGAGED', 'PENDING'))
        all_strikes = conn.execute("SELECT * FROM Strikes").fetchall()
        stale_strikes = []
        
        for s in all_strikes:
            s_dict = dict(s)
            ex_date = s_dict.get("execution_date")
            if ex_date:
                ex_dt = parse_date_obj(ex_date)
                if ex_dt and ex_dt < ref_dt and s_dict.get("status") in ["STANDBY", "ENGAGED", "PENDING"]:
                    s_dict["days_stale"] = (ref_dt - ex_dt).days
                    stale_strikes.append(s_dict)

        # 3. Orphan Relational Integrity Checks
        orphan_subtasks = conn.execute(
            """SELECT s.* FROM Subtasks s
               LEFT JOIN Tasks t ON s.task_id = t.id
               WHERE t.id IS NULL"""
        ).fetchall()

        orphan_strikes = conn.execute(
            """SELECT s.* FROM Strikes s
               LEFT JOIN Tasks t ON s.task_id = t.id
               WHERE s.task_id IS NOT NULL AND t.id IS NULL"""
        ).fetchall()

        orphan_tags = conn.execute(
            """SELECT tg.* FROM Tags tg
               LEFT JOIN Tasks t ON tg.task_id = t.id
               WHERE t.id IS NULL"""
        ).fetchall()

        # Compute System Health Assessment
        issues_count = len(overdue_tasks) + len(missing_deadline_tasks) + len(stale_strikes) + len(orphan_subtasks) + len(orphan_strikes) + len(orphan_tags)
        
        if issues_count == 0:
            health_status = "OPTIMAL_HEALTH"
            summary = "All campaigns, daily strikes, and relational foreign keys are 100% synchronized and healthy."
        elif len(overdue_tasks) > 0 or len(orphan_subtasks) > 0 or len(orphan_strikes) > 0:
            health_status = "ATTENTION_REQUIRED"
            summary = f"Detected {len(overdue_tasks)} overdue campaigns, {len(stale_strikes)} stale strikes, and {len(orphan_subtasks) + len(orphan_strikes)} orphan records."
        else:
            health_status = "MINOR_DRIFT"
            summary = f"Detected {len(stale_strikes)} stale strikes needing resolution."

        remediations = []
        if overdue_tasks:
            remediations.append(f"Reschedule or transition {len(overdue_tasks)} overdue campaigns to Breach/Archive.")
        if stale_strikes:
            remediations.append(f"Neutralize, reschedule, or abort {len(stale_strikes)} past strikes.")
        if missing_deadline_tasks:
            remediations.append(f"Assign mandatory deadlines to {len(missing_deadline_tasks)} active execution campaigns.")
        if orphan_subtasks or orphan_strikes or orphan_tags:
            remediations.append(f"Prune or re-link orphaned records.")

        return {
            "reference_date": reference_date_str,
            "health_status": health_status,
            "issues_count": issues_count,
            "summary": summary,
            "overdue_tasks": overdue_tasks,
            "missing_deadline_tasks": missing_deadline_tasks,
            "stale_strikes": stale_strikes,
            "orphaned_entities": {
                "subtasks": [dict(r) for r in orphan_subtasks],
                "strikes": [dict(r) for r in orphan_strikes],
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
# Tool Schemas with Strict Enum Constraints
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
                "status": {"type": "string", "enum": ["STANDBY", "ENGAGED", "NEUTRALIZED", "ABORTED", "PENDING", "TEMPLATE", "UNDATED"], "description": "Strike status."},
                "task_id": {"type": "integer", "description": "Filter by connected task ID."},
                "subtask_id": {"type": "integer", "description": "Filter by connected subtask ID."},
                "limit": {"type": "integer", "default": 100}
            }
        }
    },
    {
        "name": "campaigns_create_strike",
        "description": "Schedule a daily strike/directive. Enforces calendar date bounds, relational ID verification, strict Minister whitelist (Adhipati, Bhakta, Antaryami, Jigyasu), and valid statuses.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Strike action title (supports inline @today, @tomorrow, #Minister)."},
                "execution_date": {"type": "string", "description": "DD-MM-YYYY target date (defaults to today or parsed from title)."},
                "assigned": {"type": "string", "enum": ["Adhipati", "Bhakta", "Antaryami", "Jigyasu"], "default": "Bhakta", "description": "Assigned Minister."},
                "status": {"type": "string", "enum": ["STANDBY", "ENGAGED", "NEUTRALIZED", "ABORTED", "PENDING", "TEMPLATE", "UNDATED"], "default": "STANDBY"},
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
        "description": "Update any attribute of an existing strike with relational checking, strict status (STANDBY, ENGAGED, NEUTRALIZED, ABORTED, PENDING, TEMPLATE, UNDATED) and Minister validation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "strike_id": {"type": "integer", "description": "Strike ID to update."},
                "fields": {
                    "type": "object",
                    "description": "Attributes to update.",
                    "properties": {
                        "status": {"type": "string", "enum": ["STANDBY", "ENGAGED", "NEUTRALIZED", "ABORTED", "PENDING", "TEMPLATE", "UNDATED"]},
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
                "status": {"type": "string", "enum": ["Initiated", "Doing", "Completed", "Failed"], "description": "Subtask status."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "campaigns_manage_tag",
        "description": "Manage categorical tags: add to task, remove, rename globally, or list all distinct tags with alphanumeric sanitization.",
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
                    "version": "1.0.0"
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

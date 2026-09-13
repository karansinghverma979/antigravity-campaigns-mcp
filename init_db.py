#!/usr/bin/env python3
"""
Campaigns SQLite Database Bootstrapper
Initializes a clean schema and optional seed data for the Campaigns MCP ecosystem.
"""

import os
import sys
import sqlite3

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

def init_database(db_path=None, seed_demo=True):
    if not db_path:
        db_path = os.path.expandvars(r"%APPDATA%\Campaigns\Database\campaigns.sqlite")
    
    db_dir = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(db_dir, exist_ok=True)
    
    print(f"📦 Initializing Campaigns SQLite Database at: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    conn.executescript(schema_sql)
    print("✅ Schema DDL executed successfully.")
    
    if seed_demo:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM Tasks")
        if cur.fetchone()[0] == 0:
            print("🌱 Seeding demo tactical campaign...")
            cur.execute("""
                INSERT INTO Tasks (title, description, priority, state, stage, origin_date, initiated_at, deadline)
                VALUES ('Operation Sovereign Forge', 'Bootstrap and verify the autonomous Campaigns MCP ecosystem', 'High', 'Execution', 'Executing', '14-09-2026', '14-09-2026', '30-09-2026')
            """)
            task_id = cur.lastrowid
            
            cur.execute("""
                INSERT INTO Tags (task_id, tag_name)
                VALUES (?, 'INFRASTRUCTURE')
            """, (task_id,))
            
            cur.execute("""
                INSERT INTO Subtasks (task_id, title, status)
                VALUES (?, 'Verify SQLite triggers and integrity checks', 'Completed')
            """, (task_id,))
            
            cur.execute("""
                INSERT INTO Subtasks (task_id, title, status)
                VALUES (?, 'Connect AI agent via stdio FastMCP transport', 'Doing')
            """, (task_id,))
            
            cur.execute("""
                INSERT INTO Strikes (task_id, title, execution_date, assigned, status)
                VALUES (?, 'Run single-shot campaigns_audit_health check', '14-09-2026', 'Bhakta', 'STANDBY')
            """, (task_id,))
            
            conn.commit()
            print("✅ Demo campaign and tactical strike seeded successfully.")
    
    conn.close()
    print("🎉 Database setup complete and ready for Campaigns MCP Server!")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    init_database(target)

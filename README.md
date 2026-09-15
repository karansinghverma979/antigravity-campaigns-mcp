<div align="center">

# ⚔️ ANTIGRAVITY CAMPAIGNS MCP SERVER

### *Authoritative SQLite State-Machine, Multi-Minister Governance & Financial Treasury Suite for AI Agents*

<br/>

<a href="https://github.com/karansinghverma979/antigravity-campaigns-mcp">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&duration=3000&pause=1000&color=E53935&center=true&vCenter=true&multiline=true&width=750&height=100&lines=Tactical+Campaign+State-Machine+(4+Stages);Multi-Minister+Governance+(Adhipati%2C+Bhakta%2C+Antaryami%2C+Jigyasu);Financial+Treasury+%26+Counterparty+Ledger;Automated+Database+Integrity+%26+Health+Audits" alt="Typing SVG" />
</a>

<br/>
<br/>

<!-- Shields Row 1: Platform & Framework -->
<p align="center">
  <a href="https://modelcontextprotocol.io">
    <img src="https://img.shields.io/badge/MCP-Protocol_1.0-8A2BE2?style=for-the-badge&logo=anthropic&logoColor=white" alt="MCP Protocol" />
  </a>
  <a href="https://sqlite.org">
    <img src="https://img.shields.io/badge/SQLite-WAL_Mode-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
  </a>
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-00C853?style=for-the-badge" alt="MIT License" />
  </a>
</p>

<!-- Shields Row 2: Capabilities & Standards -->
<p align="center">
  <img src="https://img.shields.io/badge/Tools-20_Operations-FF3D00?style=for-the-badge&logo=hammer&logoColor=white" alt="20 MCP Tools" />
  <img src="https://img.shields.io/badge/Integrity-Foreign_Keys_ON-00E676?style=for-the-badge&logo=checkmarx&logoColor=white" alt="Foreign Keys Enforced" />
  <img src="https://img.shields.io/badge/Data_Safety-Zero_Data_Leak-brightgreen?style=for-the-badge&logo=shield&logoColor=white" alt="Zero Data Leak" />
  <img src="https://img.shields.io/badge/Architecture-CQRS_Treasury-00B0FF?style=for-the-badge&logo=blueprint&logoColor=white" alt="CQRS Architecture" />
</p>

<p align="center">
  <b>Empower your AI assistant with a high-speed relational lifecycle engine for strategic planning, tactical daily strikes, subtask trees, counterparty relationships, and cash flow governance.</b>
</p>

---

</div>

<br/>

## 📑 Table of Contents
- [✨ Core Capabilities](#-core-capabilities)
- [🏛️ System Architecture](#️-system-architecture)
- [🛠️ Tool Catalog (20 Operations)](#️-tool-catalog-20-operations)
- [📊 Database Schema & LifeCycle](#-database-schema--lifecycle)
- [🚀 Quickstart & Setup](#-quickstart--setup)
- [⚙️ Client Configurations](#️-client-configurations)
  - [Antigravity CLI](#antigravity-cli)
  - [Claude Desktop](#claude-desktop)
- [📐 Tactical Guardrails & Invariants](#-tactical-guardrails--invariants)
- [📄 License](#-license)

---

## ✨ Core Capabilities

- 🏛️ **4-Minister Governance Model**: Directive assignment across specialized domains:
  - **`Adhipati`**: Macro-Strategy, Legal, Recruitment, High-Order Decisions, Financial Governance.
  - **`Bhakta`**: Devotion to Duty, Physical Execution, Daily Disciplines, Engineering Craftsmanship.
  - **`Antaryami`**: Inner Observer, Self-Reflection, Psychological Constitution, Alignment.
  - **`Jigyasu`**: Intellectual Mastery, 366 Laws, Continuous Learning.
- ⚡ **High-Speed Relational Engine**: Direct SQLite access in WAL mode with sub-millisecond query latency.
- 💰 **Relational Treasury & Counterparties**: Track payables, receivables, debt dues, invoices, and partial payment history with live computed net balances.
- 🌳 **Hierarchical Subtask Trees**: Multi-level subtasks (`Initiated` ➔ `Doing` ➔ `Completed` / `Failed`).
- 🎯 **Daily Tactical Strikes**: Track daily battle directives with strict completion status (`NEUTRALIZED`).
- 🩺 **Automated Health Auditor**: `campaigns_audit_health` detects orphaned strikes, overdue deadlines, and stale directives in a single pass.
- 🛡️ **Zero Secret / Data Leaks**: Database location is fully configurable; schemas and initializers keep personal state isolated.

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AI AGENT RUNTIME ENGINE                         │
│               (Antigravity CLI / Claude Desktop / Cursor)              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ JSON-RPC (stdio)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   CAMPAIGNS MCP SERVER (server.py)                     │
├────────────────────────────────────────────────────────────────────────┤
│ 🛡️ Strict Whitelist & Type Sanitizer (Foreign Key Enforcement)        │
├───────────────────────────────────┬────────────────────────────────────┤
│ 📋 Task Lifecycle Engine          │ 🎯 Daily Strike Coordinator        │
│ 🌳 Subtask Hierarchy Manager      │ 🏷️ Taxonomy & Tag Indexer          │
│ 💰 Treasury & Obligations Manager │ 👥 Counterparty Directory Dossier  │
│ 🩺 Health & Integrity Auditor     │ ⚡ Unrestricted SQL Engine         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQLite Driver (WAL Mode)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   CAMPAIGNS RELATIONAL DATABASE                        │
│             `%APPDATA%\Campaigns\Database\campaigns.sqlite`             │
│   [ Tasks · Subtasks · Strikes · Tags · Counterparties · Treasury ]    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tool Catalog (20 Operations)

| Category | MCP Tool Name | Description |
| :--- | :--- | :--- |
| **🩺 Health & HUD** | `campaigns_get_dashboard` | Live overview of active campaigns, pending strikes, and operational health. |
| | `campaigns_audit_health` | Full database integrity scan across campaigns, strikes, subtasks, and treasury. |
| **📋 Tasks** | `campaigns_list_tasks` | List and filter campaigns by state (`Arsenal`, `Execution`, `Breach`, `Archive`), stage, or priority. |
| | `campaigns_get_task_details`| Deep query returning task attributes, subtask tree, connected strikes, and tags. |
| | `campaigns_create_task` | Create a new campaign with priority, state stage, origin date, and deadline. |
| | `campaigns_update_task` | Update task fields (state transitions, deadlines, stages) with relational integrity. |
| | `campaigns_delete_task` | Cascade deletion of a campaign and its associated subtasks and strikes. |
| **🎯 Strikes** | `campaigns_list_strikes` | List daily strikes filtered by execution date (`DD-MM-YYYY`), status, or Minister. |
| | `campaigns_create_strike` | Create a daily tactical strike assigned to a Minister with recurrence ID support. |
| | `campaigns_update_strike` | Update strike status (`STANDBY`, `ENGAGED`, `NEUTRALIZED`, `ABORTED`), date, or notes. |
| | `campaigns_delete_strike` | Remove a strike from the tactical schedule. |
| **🌳 Subtasks & Tags**| `campaigns_manage_subtask` | Create, update status (`Initiated`/`Doing`/`Completed`), or delete subtask nodes. |
| | `campaigns_manage_tag` | Attach or detach uppercase taxonomy tags (`GOVT`, `RECRUITMENT`, `MOTOR_WINDING`). |
| **💰 Treasury & Finance**| `campaigns_get_treasury_dashboard`| 1-shot financial summary: payables due, receivables due, net position, overdues. |
| | `campaigns_list_treasury` | Filter financial obligations across `flow_type`, `state`, `category`, and `counterparty_id`. |
| | `campaigns_manage_treasury` | Create obligations, update terms, record partial payments, or delete records. |
| **👥 Counterparties**| `campaigns_list_counterparties` | Directory of persons and entities with live computed net balances and total dues. |
| | `campaigns_get_counterparty_dossier` | Deep 360° relationship dossier and complete chronological transaction ledger. |
| | `campaigns_manage_counterparty` | Create, update, or remove counterparty entities. |
| **⚡ SQL Engine** | `campaigns_execute_sql` | Execute unrestricted custom SQL queries and transactions with automatic rollback safety. |

---

## 📊 Database Schema & LifeCycle

### State Lifecycle Machine
```
┌─────────────┐       ┌───────────────┐       ┌────────────┐       ┌─────────────┐
│   Arsenal   │ ───►  │   Execution   │ ───►  │   Breach   │ ───►  │   Archive   │
│ (Raw Intel) │       │   (Active)    │       │ (Overdue)  │       │  (Victory)  │
└─────────────┘       └───────────────┘       └────────────┘       └─────────────┘
```

---

## 🚀 Quickstart & Setup

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/karansinghverma979/antigravity-campaigns-mcp.git ~/.gemini/campaigns-mcp
cd ~/.gemini/campaigns-mcp
```

### 2. Verify Server
```bash
python -c "import server; print('MCP Server verified successfully!')"
```

---

## ⚙️ Client Configurations

### Antigravity CLI
Add to your `mcp_config.json` or Antigravity MCP settings:

```json
{
  "mcpServers": {
    "campaigns": {
      "command": "python",
      "args": [
        "C:\\Users\\<USER>\\.gemini\\campaigns-mcp\\server.py"
      ]
    }
  }
}
```

### Claude Desktop
Add to `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "campaigns": {
      "command": "python",
      "args": [
        "/path/to/campaigns-mcp/server.py"
      ]
    }
  }
}
```

---

## 📐 Tactical Guardrails & Invariants

1. **Strike Completion Standard**: Completed strikes are strictly marked as **`NEUTRALIZED`** (never `COMPLETED`).
2. **Date Format Standard**: Strict calendar format **`DD-MM-YYYY`**.
3. **Execution State Mandate**: Any campaign in `state = 'Execution'` strictly requires a valid `deadline`.
4. **Minister Allocation**: All strikes must be assigned to an active Minister (`Adhipati`, `Bhakta`, `Antaryami`, `Jigyasu`).
5. **Relational Integrity**: Treasury obligations strictly enforce foreign keys referencing `Counterparties(id)`.

---

## 🧠 Official Companion Skill & Autonomous Governance

This MCP server is natively governed and orchestrated by the **[`campaigns`](https://github.com/karansinghverma979/antigravity-custom-skills/blob/main/campaigns/SKILL.md)** skill from the **[`antigravity-custom-skills`](https://github.com/karansinghverma979/antigravity-custom-skills)** suite.

---

<div align="center">

### ⭐ Star this repository if you run AI-driven tactical operations!

<b>Maintained by <a href="https://github.com/karansinghverma979">Karan Singh Verma</a> · Open-Source MIT License</b>

</div>

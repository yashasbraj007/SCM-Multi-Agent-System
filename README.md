# Supply Chain Multi-Agent System

A locally hosted, LLM-driven multi-agent system for supply chain disruption
management in raw agricultural products (wheat, barley, rice, corn, soybeans).

Case Studies 2 (K-2379-3629) — Group 2

## What This Does

The system detects and responds to supply chain disruptions (delayed
shipments, quality flags) using two specialized agents:

- **Agent 1 — Logistics & Freshness Assessment**:

  reads a disruption event,
  calculates a shelf-life/delay buffer, and classifies severity as
  LOW / MEDIUM / HIGH using transparent, rule-based logic.

- **Agent 2 — Inventory & Recovery Planning**: 

  when severity is MEDIUM or
  HIGH, searches both existing warehouse inventory and producer network for
  the best recovery option, using a tolerance-aware scoring curve (small
  delays barely penalized, large delays penalized steeply).

Both agents operate on top of two real relational databases simulating the
company's business systems.

## Project Structure

supply_chain_agents/
  agents/
    agent1_logistics/
      severity_classifier.py     (Agent 1 core logic)
    agent2_recovery/
      recovery_matcher_v2.py     (Agent 2 core logic)
  orchestrator/
    orchestrator.py               (Connects both agents + both databases)
  data/
    setup_scm_db.py                (Builds scm.db - run FIRST)
    setup_crm_db.py                (Builds crm.db - run SECOND, reads scm.db)
    raw/                           (Real external datasets - USDA NASS, etc.)
  backend/                         (FastAPI backend - in progress)
  frontend/                        (UI - in progress)
  notebooks/                       (Fine-tuning / experimentation)
  requirements.txt
  .env                             (API keys - not committed, create locally)
## Databases

**`scm.db`** — Supply Chain Management side:
- `products`, `producers` (100), `warehouses` (50), `batches` (250),
  `inventory`, `routes`, `shipments`

**`crm.db`** — Customer/order side, linked to real `scm.db` shipment IDs:
- `customers` (20), `orders`, `order_items`, `customer_communications`,
  `disruption_events`, `shipment_tracking_events`, `temperature_events`,
  `recovery_plans`, `recovery_options`

Both `.db` files are excluded from Git (`.gitignore`) since they're
regenerated locally by the setup scripts using a fixed random seed —
everyone gets identical data.

## Setup Instructions

### 1. Clone and create a virtual environment

```powershell
git clone <repo-url>
cd supply_chain_agents
python -m venv venv
venv\Scripts\activate
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Create your `.env` file

```powershell
"NASS_API_KEY=your_key_here" | Out-File -FilePath .env -Encoding utf8
```
Get a free key at [quickstats.nass.usda.gov/api](https://quickstats.nass.usda.gov/api).

### 4. Build the databases (run in this exact order)

```powershell
python data\setup_scm_db.py
python data\setup_crm_db.py
```
`setup_crm_db.py` reads real shipment IDs from `scm.db`, so `scm.db` must
exist first or it will raise a `FileNotFoundError`.

### 5. Run the full pipeline

```powershell
python orchestrator\orchestrator.py
```

This pulls real open disruption events from `crm.db`, resolves them against
real shipments/batches in `scm.db`, runs Agent 1's severity classification,
and — for MEDIUM/HIGH severity — runs Agent 2's recovery search and writes
the result back into `crm.db`.

## Datasets Used

| Source | Used By | Status |
|---|---|---|
| USDA NASS Quick Stats API | Agent 1 | Connected |
| USDA AgTransport | Agent 1 | Planned |
| FSIS FoodKeeper | Agent 1 | Planned |
| openFDA Food Enforcement API | Agent 2 | Planned |
| Simulated CRM/SCM databases | Both agents | Built |

## Current Status

-  Environment (GPU/CUDA verified, RTX 3050 laptop, 4GB VRAM)
-  Agent 1 and Agent 2 core logic, tested
-  Full CRM + SCM database schema, linked and tested
-  Orchestrator connecting both databases end-to-end
-  LLM layer (in-context learning / QLoRA)
-  FastAPI backend
-  Chat UI

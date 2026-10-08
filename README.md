# Construction Budget System

A local-first proof of concept for modeling and calculating construction budgets from tabular data.

The project is currently a learning and portfolio MVP. Its purpose is to understand the domain model behind construction budgeting, test a transparent calculation pipeline in Python, and gradually move toward a commercially useful tool without prematurely adding database, UI, or infrastructure complexity.

## Current Status

**Spiral 1 completed — PoC v0.1**

Time invested:

- Session 1 — 2h45
- Session 2 — 1h45
- Session 3 — 2h00
- Session 4 — 1h30
- **Total Spiral 1 — 8h00**
- **Original project budget — 24h00**
- **Remaining budget — 16h00**

The current PoC is deterministic and tabular. It does not automatically choose between equivalent prices or data sources.

## What Spiral 1 Delivered

### 1. Domain model

The first spiral established the main budgeting chain:

```text
Project
  -> Service Requirements
  -> Services / Compositions
  -> Inputs
  -> Unit Costs
  -> Budget Items
  -> Cost of Work
  -> BDI
  -> Selling Price
```

Key conceptual decisions:

- `Project` and `Budget` are separate.
- A project defines what must be executed; a budget values it economically.
- A service is represented operationally by a measurable composition of inputs.
- Compositions are flat in the canonical model.
- Input prices are contextual observations, not permanent input attributes.
- Supplier and reference source are separate concepts.
- Missing price is not equivalent to zero.
- Project-level costs remain separate from productive service compositions.
- BDI is applied after the cost of work is formed.
- Price selection is a separate process from the budget engine.

### 2. Canonical model v0.2

The conceptual model was consolidated in:

```text
Construction Budget MVP — Canonical Model v0.2.md
```

The canonical model is intentionally source-independent. SINAPI, SICRO, quotations, or future private databases should eventually be translated into the same internal structure instead of defining the budgeting engine directly.

### 3. Tabular PoC

The initial object-oriented prototype was replaced by a simpler data-oriented implementation using CSV files and Pandas.

Current data files:

```text
data/
├── budget_config.csv
├── compositions.csv
├── inputs.csv
├── project_costs.csv
├── requirements.csv
└── selected_prices.csv
```

Responsibilities:

| File | Responsibility |
| --- | --- |
| `inputs.csv` | Canonical input catalog and metadata |
| `selected_prices.csv` | One previously selected price per input for the active budget context |
| `compositions.csv` | Input coefficients for each service |
| `requirements.csv` | Quantities of services required by the project |
| `project_costs.csv` | Costs attributable to the work as a whole |
| `budget_config.csv` | Global budget parameters such as BDI |

`inputs.csv` is currently a catalog/reference table. The calculation engine does not yet need to join it directly.

### 4. Calculation pipeline

The current engine implements the following sequence:

```text
compositions
    LEFT JOIN selected_prices
        ON input_id
            |
            v
coefficient * price
            |
            v
input cost contribution
            |
            v
GROUP BY service_id
            |
            v
service unit cost
            |
            v
requirements
    LEFT JOIN service unit costs
        ON service_id
            |
            v
quantity * unit cost
            |
            v
budget items
            |
            v
services total
            |
            + project-level costs
            |
            v
cost of work
            |
            * (1 + BDI)
            |
            v
selling price
```

The current engine uses no database, no ORM, and no custom class hierarchy.

### 5. Auditable output

The CLI output is divided into three stages:

```text
ENTRADA
PROCESSAMENTO
ORÇAMENTO
```

The audit layer currently exposes:

- service requirements;
- project-level costs;
- composition coefficients;
- selected prices;
- input cost contributions;
- service unit costs;
- budget items;
- final summary.

The current didactic dataset produces:

```text
Services total:       R$ 16.446,75
Project-level costs:  R$  1.624,63
Cost of work:         R$ 18.071,38
BDI:                       22,12%
Selling price:        R$ 22.068,77
```

These values come from synthetic/didactic data and are not intended to represent a real executable construction estimate.

## Architecture

The project is evolving toward three separate subsystems:

```text
1. DATA MANAGEMENT
   External sources
      -> normalization
      -> cleaning
      -> canonical data

2. QUOTATION / PRICE SELECTION
   Price observations
      -> user-defined selection criteria
      -> selected price book

3. BUDGET ENGINE
   Selected prices
   + compositions
   + project requirements
   + project-level costs
   + BDI
      -> auditable budget
```

Only the third subsystem currently has a working PoC.

The budget engine must remain deterministic: it calculates from previously selected prices instead of silently choosing economic alternatives on behalf of the user.

## Known Structural Decisions

### Keys and relations

Current logical keys:

```text
inputs
  PK: input_id

selected_prices
  PK: input_id

compositions
  desired unique pair: (service_id, input_id)

budget_config
  PK: parameter
```

`requirements` may eventually require its own `requirement_id`, because the same service may legitimately occur more than once in a project.

`project_costs` currently has no explicit ID. A future version may add `project_cost_id`.

### Catalog tables

`inputs.csv` is a catalog rather than an operational calculation table.

A future `services.csv` may play the same role:

```text
inputs.csv   -> what inputs exist?
services.csv -> what services exist?
```

Neither catalog needs to be in the critical calculation path unless metadata, validation, or UI requires it.

## Deferred Work

The following items were deliberately deferred from Spiral 1:

- real SINAPI data import;
- SINAPI exploratory analysis;
- adapters for external sources;
- SICRO or second-source comparison;
- equivalence matching between inputs;
- automatic price selection;
- user-defined quotation criteria;
- price families;
- persistent database;
- SQL / DuckDB;
- formal database integrity checks;
- database update / validation utility;
- `services.csv`;
- `project_cost_id`;
- UI;
- XLSX / Sheets output;
- dashboards;
- physical-financial schedule;
- full BDI composition engine;
- full payroll / labor-cost engine;
- automatic source updates.

These are not missing requirements for PoC v0.1. They are possible increments for later spirals.

## Roadmap

The project has a total initial investment cap of **24 hours**.

### Spiral 1 — Conceptual model and deterministic PoC
**Status: completed — 8h**

Delivered:

- domain terminology and cost model;
- BDI conceptual model;
- canonical model v0.2;
- source-independent tabular structure;
- Pandas calculation engine;
- auditable CLI output;
- consolidated PoC v0.1.

### Spiral 2 — Real source integration
**Planned**

Objectives:

- inspect a real SINAPI dataset;
- map SINAPI fields to the canonical model;
- build the first source adapter;
- preserve source provenance;
- confirm that the current budget engine can operate without being redesigned.

No new infrastructure should be added unless real data creates a concrete need.

### Spiral 3 — Source modularity and persistence
**Planned**

Objectives may include:

- test a second source or custom dataset;
- confirm source modularity;
- decide whether Parquet, DuckDB, or another local persistence layer is justified;
- separate database update/validation from normal budget execution.

### Spiral 4 — Demonstration and commercial conversion
**Planned**

Objectives:

- improve output/export;
- prepare a portfolio case;
- describe the service that can actually be offered;
- compare the PoC with real freelance requirements;
- evaluate whether further development has commercial justification.

After the 24-hour investment cap, additional work requires a new justification: commercial opportunity, reusable component, external interest, or a clearly higher-value extension.

## Environment

Current development environment:

```text
Python 3.8.10
Pandas 1.5.2
Ubuntu
```

No newer Python version is currently required for PoC v0.1.

## Running the PoC

From the repository root:

```bash
python3 budget_poc.py
```

The script reads the CSV files under `data/` and prints the audit trail and final budget to the terminal.

## Scope and Limitations

This repository is currently a proof of concept, not a production construction-estimating application.

In particular:

- prices are synthetic or didactic;
- no official source is imported automatically;
- no guarantee is made that current compositions correspond to executable construction specifications;
- BDI is currently supplied as an effective rate;
- no automatic quotation or procurement decision is performed;
- no database persistence is implemented.

The current objective is architectural clarity and domain learning before productization.

## Current Status

### Spiral 1 — Canonical Budget Model and Synthetic PoC

Completed.

The first spiral established the canonical budget model and validated the core
budget algebra using synthetic CSV data.

Main results:

- Project and budget treated as distinct concepts.
- Services represented as flat compositions of terminal inputs.
- Contextual prices separated from input identity.
- Project-level costs separated from service compositions.
- Simplified effective BDI applied after the cost of work.
- Deterministic budget engine implemented with Pandas.
- Synthetic PoC validated end-to-end.

Spiral 1 development time: approximately 7h45.

### Spiral 2 — SINAPI Integration MVP

Completed.

The second spiral integrated a real SINAPI snapshot into the canonical model
without changing the core budget algebra.

Reference snapshot:

- Source: SINAPI / CAIXA
- Period: 2025-09
- Location: SC
- Pricing regime: sem desoneração

Main results:

- Dynamic extraction from the SINAPI analytical workbook.
- Recursive composition flattening with arbitrary auxiliary composition depth.
- Preservation of source provenance through audit paths.
- Canonical source-qualified IDs such as `SINAPI_104658`.
- Complete service catalog extracted from the snapshot: 9,783 services.
- Selective materialization of service compositions.
- Canonical price extraction from the SINAPI ISD sheet.
- Cross-source metadata validation between analytical compositions and prices.
- Persistent canonical snapshot under `extracted-data/`.
- CLI for building valid project requirements from materialized services.
- Budget engine integrated with the real canonical snapshot.
- Explicit validation for:
  - non-materialized requested services;
  - missing required input prices;
  - invalid CLI selections;
  - invalid or non-positive quantities.

The benchmark composition `SINAPI_104658` produced:

- Engine unit cost: BRL 148.331134
- Official SINAPI CSD cost: BRL 148.29
- Difference: BRL 0.041134 (~0.028%)

The small difference is consistent with calculations based on published input
prices rounded to two decimal places.


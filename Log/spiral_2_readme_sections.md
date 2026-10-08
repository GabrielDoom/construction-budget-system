## Architecture

The MVP is organized around three logical subsystems:

1. **Data Management**
   - Reads external source data.
   - Performs source-specific EDA, validation and transformation.
   - Produces canonical repository data.

2. **Quotation / Price Selection**
   - Manages contextual price observations and price selection.
   - Currently represented only by the canonical `selected_prices` contract.
   - Supplier quotation workflows are planned for a later spiral.

3. **Budget Engine**
   - Consumes canonical requirements, compositions and selected prices.
   - Does not depend on SINAPI-specific concepts.
   - Produces deterministic budget calculations.

Current data flow:

```text
SINAPI raw snapshot
        |
        v
source-specific adapter
        |
        v
canonical snapshot
├── services.csv
├── compositions.csv
└── selected_prices.csv
        |
        v
requirements CLI
        |
        v
canonical requirements
        |
        v
budget engine
        |
        v
budget
```

The budget engine does not read SINAPI workbooks directly and does not know
about SINAPI source codes or recursive composition structures.

## Canonical Repository

A SINAPI snapshot is currently stored as:

```text
extracted-data/
└── SINAPI/
    └── 2025-09/
        └── SC/
            ├── services.csv
            ├── compositions.csv
            └── selected_prices.csv
```

### `services.csv`

Canonical service catalog.

```text
service_id
source_service_id
description
unit
reference_source
```

The current SINAPI snapshot contains 9,783 cataloged services.

Catalog membership does **not** imply that a service composition has already
been materialized.

### `compositions.csv`

Materialized canonical service compositions.

```text
service_id
input_id
coefficient
```

SINAPI auxiliary compositions are recursively flattened before entering the
canonical repository.

A service is currently considered materialized when its `service_id` occurs in
this table.

### `selected_prices.csv`

Selected contextual prices consumed by the budget engine.

```text
input_id
price
supplier
reference_source
location
period
```

SINAPI is represented as a `reference_source`, not as a supplier.

## Identifier Policy

External source identifiers and canonical identifiers have different roles.

Example:

```text
SINAPI source code: 104658
Canonical service ID: SINAPI_104658
```

`source_service_id` is retained in the service catalog for source lookup,
provenance and audit purposes.

Downstream canonical data and the budget engine use `service_id`.

The same policy applies to canonical input identifiers, e.g. `SINAPI_4750`.

## Validation Rules

The system follows a fail-fast policy for incomplete budget data.

The budget engine must reject:

- requirements for services without materialized compositions;
- required inputs without selected prices;
- invalid or non-positive quantities;
- incompatible canonical identifiers.

Missing data must never be interpreted as zero.

In particular, Pandas aggregation must not be allowed to silently ignore
missing prices and produce partial service costs.

## Current CLI Workflow

The current requirements CLI exposes only services whose compositions are
already materialized.

The workflow is:

1. Load the complete service catalog.
2. Detect materialized services from `compositions.csv`.
3. Present the materialized subset to the user.
4. Accept a service selection and quantity.
5. Convert the selection into canonical requirements.
6. Pass those requirements to the budget engine.

Selecting the same service multiple times currently aggregates its quantities.

The CLI is intentionally minimal and is not yet the main application interface.

## Known Limitations

The current MVP intentionally leaves the following problems unresolved:

- Materialization is still initiated through service codes configured in the
  SINAPI adapter.
- Incremental cache update / upsert semantics are not yet implemented.
- The system does not yet provide a top-level application orchestrator.
- Snapshot source, period and location are still selected largely through code.
- The current materialized SINAPI subset is mainly composed of services used
  during the `SINAPI_104658` validation case and is not a commercially useful
  service catalog.
- Project-level costs and BDI configuration still use synthetic Spiral 1 data.
- Private supplier quotations are not yet integrated.
- Price equivalence and price-selection workflows are not yet implemented.

## Next Direction

### Spiral 3 — Operational and Commercial Layer

The next spiral should prioritize commercial usefulness rather than another
large public reference database.

Candidate scope:

1. Introduce a top-level CLI / application orchestrator.
2. Provide catalog management without editing adapter source code.
3. Define incremental materialization and snapshot-update behavior.
4. Introduce a minimal private supplier quotation format.
5. Map supplier price observations to canonical inputs.
6. Separate price observations from selected prices.
7. Demonstrate a budget combining reference compositions with real supplier
   prices.

A new public reference database should only be integrated after this workflow
is validated.

## Spiral 2 Review

The SINAPI integration demonstrated that the canonical budget model can absorb
a real hierarchical public cost database without changing the budget engine.

Important findings:

- Source composition recursion belongs in the adapter, not in the engine.
- A complete searchable catalog can be inexpensive even when materializing all
  compositions would be expensive.
- Catalog presence and composition materialization are separate states.
- Audit evidence is needed because flattening intentionally loses the original
  composition tree structure.
- Source adapters should produce canonical data; they should not become search
  engines or user-facing applications.
- The budget engine should process only services requested by the current
  requirements, not the entire materialized cache.
- Integrity checks are required both when producing and when consuming
  canonical data.

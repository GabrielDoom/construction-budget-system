"""Construction Budget MVP — PoC v0.1

Session 3 artifact.
Scope:
- canonical entities with Python dataclasses
- flat service compositions
- contextual price observations
- input equivalence and explicit fallback
- project-level costs
- effective BDI
- traceable budget calculation

No persistence, database, external SINAPI files, UI, or Pandas.
All prices in this PoC are synthetic/didactic.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

D = Decimal


def q2(value: Decimal) -> Decimal:
    return value.quantize(D("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Input:
    id: str
    description: str
    canonical_type: str
    unit: str
    source: str
    cost_regime: Optional[str] = None


@dataclass(frozen=True)
class PriceObservation:
    input_id: str
    value: Decimal
    supplier: Optional[str]
    reference_source: str
    location: str
    period: str
    evidence_type: str
    status: str = "valid"
    notes: Optional[str] = None


@dataclass(frozen=True)
class InputEquivalence:
    input_a: str
    input_b: str
    relation: str


@dataclass(frozen=True)
class CompositionLine:
    input_id: str
    coefficient: Decimal


@dataclass(frozen=True)
class Service:
    id: str
    description: str
    unit: str
    composition: tuple[CompositionLine, ...]


@dataclass(frozen=True)
class ServiceRequirement:
    service_id: str
    quantity: Decimal


@dataclass(frozen=True)
class ProjectLevelCost:
    description: str
    kind: str
    value: Decimal


@dataclass(frozen=True)
class PricePolicy:
    location: str
    period: str
    preferred_sources: tuple[str, ...] = ("SUPPLIER_QUOTE", "SINAPI")
    allowed_equivalence: tuple[str, ...] = ("exact", "compatible")


@dataclass(frozen=True)
class SelectedPrice:
    requested_input: str
    selected_input: str
    value: Decimal
    relation: str
    supplier: Optional[str]
    reference_source: str
    location: str
    period: str
    evidence_type: str
    fallback_used: bool


@dataclass(frozen=True)
class CostLine:
    input_id: str
    description: str
    coefficient: Decimal
    selected_price: SelectedPrice
    unit_contribution: Decimal


@dataclass(frozen=True)
class ServiceCost:
    service_id: str
    description: str
    unit_cost: Decimal
    lines: tuple[CostLine, ...]


@dataclass(frozen=True)
class BudgetItemResult:
    service_id: str
    description: str
    quantity: Decimal
    unit: str
    unit_cost: Decimal
    total_cost: Decimal


@dataclass(frozen=True)
class ProjectLevelCostResult:
    description: str
    amount: Decimal


@dataclass(frozen=True)
class BudgetResult:
    service_items: tuple[BudgetItemResult, ...]
    project_level_costs: tuple[ProjectLevelCostResult, ...]
    services_total: Decimal
    cost_of_work: Decimal
    bdi_rate: Decimal
    selling_price: Decimal


def build_dataset():
    inputs = {
        "SINAPI_BLOCK": Input("SINAPI_BLOCK", "Bloco cerâmico", "material", "un", "SINAPI", "purchase"),
        "QUOTE_BLOCK": Input("QUOTE_BLOCK", "Bloco cerâmico equivalente", "material", "un", "SUPPLIER_QUOTE", "purchase"),
        "SINAPI_BEDDING_MORTAR": Input("SINAPI_BEDDING_MORTAR", "Argamassa de assentamento", "material", "kg", "SINAPI", "purchase"),
        "SINAPI_RENDER_MORTAR": Input("SINAPI_RENDER_MORTAR", "Argamassa de revestimento", "material", "kg", "SINAPI", "purchase"),
        "SINAPI_SEALER": Input("SINAPI_SEALER", "Selador acrílico", "material", "L", "SINAPI", "purchase"),
        "SINAPI_PAINT": Input("SINAPI_PAINT", "Tinta acrílica", "material", "L", "SINAPI", "purchase"),
        "QUOTE_PAINT": Input("QUOTE_PAINT", "Tinta acrílica compatível", "material", "L", "SUPPLIER_QUOTE", "purchase"),
        "SINAPI_BRICKLAYER": Input("SINAPI_BRICKLAYER", "Pedreiro", "labor", "h", "SINAPI", "employment"),
        "SINAPI_HELPER": Input("SINAPI_HELPER", "Ajudante", "labor", "h", "SINAPI", "employment"),
        "SINAPI_PAINTER": Input("SINAPI_PAINTER", "Pintor", "labor", "h", "SINAPI", "employment"),
        "SINAPI_MIXER_RENT": Input("SINAPI_MIXER_RENT", "Betoneira 400 L", "equipment", "h", "SINAPI", "rental"),
    }

    prices = [
        PriceObservation("SINAPI_BLOCK", D("2.20"), "SINAPI_MATERIAL_A", "SINAPI", "SC", "2026-09", "reference"),
        PriceObservation("QUOTE_BLOCK", D("2.35"), "FORNECEDOR_LOCAL_A", "SUPPLIER_QUOTE", "SC", "2026-09", "quotation"),
        PriceObservation("SINAPI_BEDDING_MORTAR", D("0.80"), "SINAPI_MATERIAL_A", "SINAPI", "SC", "2026-09", "reference"),
        PriceObservation("SINAPI_RENDER_MORTAR", D("0.75"), "SINAPI_MATERIAL_A", "SINAPI", "SC", "2026-09", "reference"),
        PriceObservation("SINAPI_SEALER", D("12.00"), "SINAPI_MATERIAL_A", "SINAPI", "SC", "2026-09", "reference"),

        # SINAPI_PAINT deliberately has no price observation.
        PriceObservation("QUOTE_PAINT", D("20.00"), "FORNECEDOR_LOCAL_B", "SUPPLIER_QUOTE", "SC", "2026-09", "quotation"),

        # Effective labor hourly costs already include 114.47% social charges
        # over synthetic base rates of R$16/h, R$11/h and R$15/h.
        PriceObservation("SINAPI_BRICKLAYER", D("34.32"), "SINAPI_LABOR_A", "SINAPI", "SC", "2026-09", "reference",
                         notes="Base R$16/h + 114,47% encargos"),
        PriceObservation("SINAPI_HELPER", D("23.59"), "SINAPI_LABOR_A", "SINAPI", "SC", "2026-09", "reference",
                         notes="Base R$11/h + 114,47% encargos"),
        PriceObservation("SINAPI_PAINTER", D("32.17"), "SINAPI_LABOR_A", "SINAPI", "SC", "2026-09", "reference",
                         notes="Base R$15/h + 114,47% encargos"),
        PriceObservation("SINAPI_MIXER_RENT", D("8.00"), "SINAPI_EQUIPMENT_A", "SINAPI", "SC", "2026-09", "reference"),
    ]

    equivalences = [
        InputEquivalence("SINAPI_BLOCK", "QUOTE_BLOCK", "exact"),
        InputEquivalence("SINAPI_PAINT", "QUOTE_PAINT", "compatible"),
    ]

    services = {
        "MASONRY": Service("MASONRY", "Alvenaria", "m2", (
            CompositionLine("SINAPI_BLOCK", D("16.7")),
            CompositionLine("SINAPI_BEDDING_MORTAR", D("8")),
            CompositionLine("SINAPI_BRICKLAYER", D("0.70")),
            CompositionLine("SINAPI_HELPER", D("0.35")),
            CompositionLine("SINAPI_MIXER_RENT", D("0.02")),
        )),
        "RENDER": Service("RENDER", "Revestimento", "m2", (
            CompositionLine("SINAPI_RENDER_MORTAR", D("18")),
            CompositionLine("SINAPI_BRICKLAYER", D("0.35")),
            CompositionLine("SINAPI_HELPER", D("0.20")),
            CompositionLine("SINAPI_MIXER_RENT", D("0.02")),
        )),
        "PAINTING": Service("PAINTING", "Pintura", "m2", (
            CompositionLine("SINAPI_SEALER", D("0.12")),
            CompositionLine("SINAPI_PAINT", D("0.25")),
            CompositionLine("SINAPI_PAINTER", D("0.20")),
            CompositionLine("SINAPI_HELPER", D("0.05")),
        )),
    }

    requirements = [
        ServiceRequirement("MASONRY", D("100")),
        ServiceRequirement("RENDER", D("200")),
        ServiceRequirement("PAINTING", D("200")),
    ]

    project_level_costs = [
        ProjectLevelCost("Mobilização/desmobilização", "fixed", D("600.00")),
        ProjectLevelCost("Administração local", "percent_of_services", D("0.0623")),
    ]

    return inputs, prices, equivalences, services, requirements, project_level_costs


def equivalence_for(target_id, candidate_id, equivalences):
    if target_id == candidate_id:
        return "identity"

    for eq in equivalences:
        if {eq.input_a, eq.input_b} == {target_id, candidate_id}:
            return eq.relation

    return None


def select_price(target_id, policy, inputs, prices, equivalences):
    candidates = []

    for obs in prices:
        relation = equivalence_for(target_id, obs.input_id, equivalences)

        if relation is None:
            continue
        if relation not in ("identity",) + policy.allowed_equivalence:
            continue
        if obs.status != "valid":
            continue

        target = inputs[target_id]
        candidate = inputs[obs.input_id]

        if target.unit != candidate.unit:
            continue
        if target.cost_regime != candidate.cost_regime:
            continue

        relation_rank = {"identity": 0, "exact": 1, "compatible": 2}[relation]
        location_rank = 0 if obs.location == policy.location else 1
        period_rank = 0 if obs.period == policy.period else 1

        try:
            source_rank = policy.preferred_sources.index(obs.reference_source)
        except ValueError:
            source_rank = len(policy.preferred_sources)

        rank = (relation_rank, location_rank, period_rank, source_rank)
        candidates.append((rank, obs, relation))

    if not candidates:
        raise LookupError(f"Sem preço utilizável para {target_id}")

    candidates.sort(key=lambda x: x[0])
    _, obs, relation = candidates[0]

    return SelectedPrice(
        requested_input=target_id,
        selected_input=obs.input_id,
        value=obs.value,
        relation=relation,
        supplier=obs.supplier,
        reference_source=obs.reference_source,
        location=obs.location,
        period=obs.period,
        evidence_type=obs.evidence_type,
        fallback_used=(obs.input_id != target_id),
    )


def calculate_service_cost(service, policy, inputs, prices, equivalences):
    lines = []
    total = D("0")

    for item in service.composition:
        selected = select_price(item.input_id, policy, inputs, prices, equivalences)
        contribution = item.coefficient * selected.value
        total += contribution

        lines.append(
            CostLine(
                input_id=item.input_id,
                description=inputs[item.input_id].description,
                coefficient=item.coefficient,
                selected_price=selected,
                unit_contribution=contribution,
            )
        )

    return ServiceCost(service.id, service.description, total, tuple(lines))


def calculate_budget(
    requirements,
    project_level_costs,
    policy,
    bdi_rate,
    inputs,
    prices,
    equivalences,
    services,
):
    item_results = []

    for req in requirements:
        service = services[req.service_id]
        service_cost = calculate_service_cost(
            service, policy, inputs, prices, equivalences
        )

        item_results.append(
            BudgetItemResult(
                service_id=service.id,
                description=service.description,
                quantity=req.quantity,
                unit=service.unit,
                unit_cost=service_cost.unit_cost,
                total_cost=req.quantity * service_cost.unit_cost,
            )
        )

    services_total = sum((x.total_cost for x in item_results), D("0"))

    plc_results = []
    for plc in project_level_costs:
        if plc.kind == "fixed":
            amount = plc.value
        elif plc.kind == "percent_of_services":
            amount = services_total * plc.value
        else:
            raise ValueError(f"Regra de custo desconhecida: {plc.kind}")

        plc_results.append(ProjectLevelCostResult(plc.description, amount))

    project_total = sum((x.amount for x in plc_results), D("0"))
    cost_of_work = services_total + project_total
    selling_price = cost_of_work * (D("1") + bdi_rate)

    return BudgetResult(
        tuple(item_results),
        tuple(plc_results),
        services_total,
        cost_of_work,
        bdi_rate,
        selling_price,
    )


def validate_model(inputs, prices, equivalences, services):
    errors = []

    for service in services.values():
        for line in service.composition:
            if line.input_id not in inputs:
                errors.append(f"{service.id}: input inexistente {line.input_id}")
            if line.coefficient <= 0:
                errors.append(f"{service.id}: coeficiente não positivo para {line.input_id}")

    for obs in prices:
        if obs.input_id not in inputs:
            errors.append(f"Preço aponta para input inexistente: {obs.input_id}")
        if obs.value < 0:
            errors.append(f"Preço negativo: {obs.input_id}")

    for eq in equivalences:
        if eq.input_a not in inputs or eq.input_b not in inputs:
            errors.append(f"Equivalência inválida: {eq}")
            continue

        a, b = inputs[eq.input_a], inputs[eq.input_b]

        if a.unit != b.unit:
            errors.append(f"Equivalência {eq.input_a} ↔ {eq.input_b}: unidades diferentes")
        if a.cost_regime != b.cost_regime:
            errors.append(f"Equivalência {eq.input_a} ↔ {eq.input_b}: regimes diferentes")

    return errors


def main():
    inputs, prices, equivalences, services, requirements, project_level_costs = build_dataset()
    policy = PricePolicy(location="SC", period="2026-09")

    errors = validate_model(inputs, prices, equivalences, services)
    if errors:
        raise ValueError("\n".join(errors))

    budget = calculate_budget(
        requirements=requirements,
        project_level_costs=project_level_costs,
        policy=policy,
        bdi_rate=D("0.2212"),
        inputs=inputs,
        prices=prices,
        equivalences=equivalences,
        services=services,
    )

    print("ORÇAMENTO PoC v0.1\n")
    for item in budget.service_items:
        print(
            f"{item.description:15} "
            f"{item.quantity:>6} {item.unit:>3} × "
            f"R$ {q2(item.unit_cost):>7} = "
            f"R$ {q2(item.total_cost):>9}"
        )

    print(f"\nServiços:             R$ {q2(budget.services_total)}")
    for plc in budget.project_level_costs:
        print(f"{plc.description:24} R$ {q2(plc.amount)}")

    print(f"Custo da obra:        R$ {q2(budget.cost_of_work)}")
    print(f"BDI efetivo:          {budget.bdi_rate * 100}%")
    print(f"Preço proposto:       R$ {q2(budget.selling_price)}")

    print("\nFALLBACKS:")
    seen = set()
    for service in services.values():
        for line in service.composition:
            if line.input_id in seen:
                continue
            seen.add(line.input_id)

            selected = select_price(
                line.input_id, policy, inputs, prices, equivalences
            )
            if selected.fallback_used:
                print(
                    f"{inputs[line.input_id].description}: "
                    f"{selected.selected_input} | "
                    f"{selected.reference_source} | "
                    f"{selected.relation}"
                )


if __name__ == "__main__":
    main()

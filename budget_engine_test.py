import pandas as pd
from pathlib import Path
from source.requirements_cli import (
    build_requirements_cli
)

# Format functions
def format_currency(value):
    formatted = "{:,.2f}".format(value)
    formatted = formatted.replace(",", "X")
    formatted = formatted.replace(".", ",")
    formatted = formatted.replace("X", ".")
    return "R$ " + formatted

def format_percent(value):
    return f"{value * 100: .2f}%".replace(".",",")

# Recovery path
SNAPSHOT_DIR = Path(
    "extracted-data/SINAPI/2025-09/SC"
)

# Catalog/reference data
services = pd.read_csv(
    SNAPSHOT_DIR / "services.csv"
)

compositions = pd.read_csv(
    SNAPSHOT_DIR / "compositions.csv"
)

selected_prices = pd.read_csv(
    SNAPSHOT_DIR / "selected_prices.csv"
)

selected_prices = selected_prices[
    selected_prices["input_id"]
    != "SINAPI_4750"
].copy()

# CLI Interruption

requirements = build_requirements_cli(
    services,
    compositions
)

# Wrong Injection

# materialized_ids = set(
#     compositions["service_id"]
# )

# unmaterialized_service = (
#     services[
#         ~services["service_id"].isin(
#             materialized_ids
#         )
#     ]
#     .iloc[0]
# )

# requirements = pd.DataFrame([
#     {
#         "service_id":
#             unmaterialized_service["service_id"],
#         "quantity": 1
#     }
# ])

# print(
#     "TEST SERVICE:",
#     unmaterialized_service["service_id"],
#     unmaterialized_service["description"]
# )

# Operational database
project_costs = pd.read_csv("data/project_costs.csv")
budget_config = pd.read_csv("data/budget_config.csv")

requested_service_ids = set(
    requirements["service_id"]
)

budget_compositions = compositions[
    compositions["service_id"].isin(
        requested_service_ids
    )
].copy()

composition_prices = budget_compositions.merge(
    selected_prices,
    on="input_id",
    how="left"
)

composition_prices = budget_compositions.merge(
    selected_prices,
    on="input_id",
    how="left"
)

missing_prices = composition_prices["price"].isna()

if missing_prices.any():
    missing_inputs = (
        composition_prices.loc[
            missing_prices,
            ["service_id", "input_id"]
        ]
        .to_dict("records")
    )

    raise ValueError(
        "Missing prices for required inputs: {}."
        .format(missing_inputs)
    )

composition_prices["input_cost"] = (
    composition_prices["coefficient"]
    * composition_prices["price"]
)

service_costs = (
    composition_prices
    .groupby("service_id", sort=False)["input_cost"]
    .sum()
    .reset_index()
)

service_costs = service_costs.rename(
    columns={"input_cost": "unit_cost"}
)

budget_items = requirements.merge(
    service_costs,
    on="service_id",
    how="left"
)

missing_costs = budget_items["unit_cost"].isna()

if missing_costs.any():
    raise ValueError(
        "Requirements contain services without materialized costs: {}."
        .format(
            budget_items.loc[
                missing_costs,
                "service_id"
            ].tolist()
        )
    )

budget_items["item_cost"] = (
    budget_items["quantity"]
    * budget_items["unit_cost"]
)

services_total = budget_items["item_cost"].sum()

project_costs["calculated_cost"] = project_costs["value"]

percent_mask = (
    project_costs["kind"] == "percent_of_services"
)

project_costs.loc[
	percent_mask,
	"calculated_cost"
] = (
	project_costs.loc[
		percent_mask,
		"value"
	]
	* services_total
)

project_costs_total = project_costs["calculated_cost"].sum()

cost_of_work = services_total+project_costs_total

bdi_rate = budget_config.loc[ 
	budget_config["parameter"] == "bdi_rate", "value"
].iloc[0]

selling_price = cost_of_work * (1 + bdi_rate)

budget_display = budget_items.copy()

budget_display["unit_cost"] = budget_display["unit_cost"].map(format_currency)
budget_display["item_cost"] = budget_display["item_cost"].map(format_currency)


print("\n==============================")
print("ENTRADA")
print("==============================")

print("\nREQUIREMENTS")
print(requirements)

print("\nPROJECT LEVEL COSTS")
print(project_costs)

print("\n==============================")
print("PROCESSAMENTO")
print("==============================")

print("\nCOMPOSITION + PRICES + INPUT COSTS")
print(
    composition_prices[
        [
            "service_id",
            "input_id",
            "coefficient",
            "price",
            "input_cost"
        ]
    ]
)

print("\nSERVICE UNIT COSTS")
print(service_costs)

print("\n==============================")
print("ORÇAMENTO")
print("==============================")

print("\nITENS")
print(budget_display)

print("\nRESUMO")
print("Serviços:", format_currency(services_total))
print("Custos de nível da obra:", format_currency(project_costs_total))
print("Custo da obra:", format_currency(cost_of_work))
print("BDI:", format_percent(bdi_rate))
print("Preço de venda:", format_currency(selling_price))
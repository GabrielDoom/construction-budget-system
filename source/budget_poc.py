import pandas as pd

# Format functions
def format_currency(value):
    formatted = "{:,.2f}".format(value)
    formatted = formatted.replace(",", "X")
    formatted = formatted.replace(".", ",")
    formatted = formatted.replace("X", ".")
    return "R$ " + formatted

def format_percent(value):
    return f"{value * 100: .2f}%".replace(".",",")


# Catalog/reference data
inputs = pd.read_csv("data/inputs.csv")

# Operational database
selected_prices = pd.read_csv("data/selected_prices.csv")
compositions = pd.read_csv("data/compositions.csv")
requirements = pd.read_csv("data/requirements.csv")
project_costs = pd.read_csv("data/project_costs.csv")
budget_config = pd.read_csv("data/budget_config.csv")

composition_prices = compositions.merge(
    selected_prices,
    on="input_id",
    how="left"
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
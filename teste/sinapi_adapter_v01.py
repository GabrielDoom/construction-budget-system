import pandas as pd
import sinapi_compositions as composition_adapter
import sinapi_prices as price_adapter

import warnings

warnings.filterwarnings(
	"ignore",
	category=FutureWarning
)

SOURCE_FILE = (
	"reference/SINAPI-2025-09-formato-xlsx/"
	"SINAPI_Referência_2025_09.xlsx"
)

SHEET_NAME = "Analítico"
TARGET_SERVICE = 104658
REFERENCE_SOURCE = "SINAPI"
LOCATION = "SC"
PERIOD = "2025-09"


def normalize_text(value):
	if pd.isna(value):
		return ""

	return " ".join(str(value).replace("\n", " ").split()).upper()


raw = pd.read_excel(
	SOURCE_FILE,
	sheet_name=SHEET_NAME,
	header=None
)


header_row = None

for index, row in raw.iterrows():
	normalized = [normalize_text(value) for value in row]

	if (
		"CÓDIGO DA COMPOSIÇÃO" in normalized
		and "TIPO ITEM" in normalized
		and "DESCRIÇÃO" in normalized
		and "UNIDADE" in normalized
	):
		header_row = index
		break


if header_row is None:
	raise ValueError(
		"Could not locate the required header in sheet 'Analítico'."
	)


headers = [
	normalize_text(value)
	for value in raw.iloc[header_row]
]


composition_col = headers.index("CÓDIGO DA COMPOSIÇÃO")
item_type_col = headers.index("TIPO ITEM")
description_col = headers.index("DESCRIÇÃO")
unit_col = headers.index("UNIDADE")
item_code_col = headers.index("CÓDIGO DO ITEM")
coefficient_col = headers.index("COEFICIENTE")
situation_col = headers.index("SITUAÇÃO")


data = raw.iloc[header_row + 1:].copy()

def extract_dependencies(service_code):
	direct_dependencies = data[
		(data.iloc[:, composition_col] == service_code)
		& (data.iloc[:, item_type_col].notna())
	].copy()

	if direct_dependencies.empty:
		raise ValueError(
			"Composition {} has no dependencies."
			.format(service_code)
		)

	dependencies = pd.DataFrame({
		"item_type": direct_dependencies.iloc[:, item_type_col],
		"item_id": direct_dependencies.iloc[:, item_code_col],
		"description": direct_dependencies.iloc[:, description_col],
		"unit": direct_dependencies.iloc[:, unit_col],
		"coefficient": direct_dependencies.iloc[:, coefficient_col],
		"situation": direct_dependencies.iloc[:, situation_col]
	})

	dependencies["item_type"] = (
		dependencies["item_type"]
		.map(normalize_text)
	)

	allowed_item_types = {
		"INSUMO",
		"COMPOSICAO"
	}

	invalid_item_types = (
		set(dependencies["item_type"])
		- allowed_item_types
	)

	if invalid_item_types:
		raise ValueError(
			"Unsupported item types found in composition {}: {}."
			.format(
				service_code,
				sorted(invalid_item_types)
			)
		)

	if dependencies["item_id"].isna().any():
		raise ValueError(
			"Found dependency without item ID in composition {}."
			.format(service_code)
		)

	dependencies["coefficient"] = pd.to_numeric(
		dependencies["coefficient"],
		errors="coerce"
	)

	invalid_coefficients = (
		dependencies["coefficient"].isna()
		| (dependencies["coefficient"] <= 0)
	)

	if invalid_coefficients.any():
		raise ValueError(
			"Found invalid coefficient in composition {}."
			.format(service_code)
		)

	return dependencies


service_rows = data[
	(data.iloc[:, composition_col] == TARGET_SERVICE)
	& (data.iloc[:, item_type_col].isna())
]


if len(service_rows) != 1:
	raise ValueError(
		"Expected exactly one service row for composition {}, found {}."
		.format(TARGET_SERVICE, len(service_rows))
	)


service_row = service_rows.iloc[0]


service = {
	"service_id": "{}_{}".format(
		REFERENCE_SOURCE,
		TARGET_SERVICE
	),
	"description": service_row.iloc[description_col],
	"unit": service_row.iloc[unit_col],
	"reference_source": REFERENCE_SOURCE
}

dependencies = extract_dependencies(TARGET_SERVICE)

def flatten_composition(
	service_code,
	multiplier=1.0,
	path=None,
	factor_chain=None
):	
	if path is None:
		path = []

	if factor_chain is None:
		factor_chain = []

	if service_code in path:
		cycle = path + [service_code]

		raise ValueError(
			"Composition cycle detected: {}."
			.format(
				" -> ".join(
					str(code)
					for code in cycle
				)
			)
		)

	current_path = path + [service_code]

	dependencies = extract_dependencies(service_code)

	terminal_rows = []

	for _, dependency in dependencies.iterrows():
		item_type = dependency["item_type"]
		item_id = dependency["item_id"]

		local_coefficient = dependency["coefficient"]

		current_factor_chain = (
			factor_chain
			+ [local_coefficient]
		)

		accumulated_coefficient = (
			multiplier
			* local_coefficient
		)

		if item_type == "INSUMO":
			terminal_rows.append({
				"input_id": item_id,
				"description": dependency["description"],
				"unit": dependency["unit"],
				"path": " -> ".join(
					str(code)
					for code in current_path + [item_id]
				),
				"factor_chain": " * ".join(
					str(value)
					for value in current_factor_chain
				),
				"coefficient": accumulated_coefficient
			})

		elif item_type == "COMPOSICAO":
			child_rows = flatten_composition(
				item_id,
				multiplier=accumulated_coefficient,
				path=current_path,
				factor_chain=current_factor_chain
			)

			terminal_rows.extend(child_rows)

	return terminal_rows

flattened = pd.DataFrame(
	flatten_composition(TARGET_SERVICE)
)

metadata_check = (
	flattened
	.groupby("input_id")
	.agg({
		"description": "nunique",
		"unit": "nunique"
	})
)

inconsistent_metadata = metadata_check[
	(metadata_check["description"] > 1)
	| (metadata_check["unit"] > 1)
]

if not inconsistent_metadata.empty:
	raise ValueError(
		"Inconsistent metadata found for input IDs: {}."
		.format(
			list(inconsistent_metadata.index)
		)
	)


aggregated = (
	flattened
	.groupby(
		"input_id",
		as_index=False
	)
	.agg({
		"description": "first",
		"unit": "first",
		"coefficient": "sum"
	})
)

canonical_composition = pd.DataFrame({
	"service_id": (
		REFERENCE_SOURCE
		+ "_"
		+ str(TARGET_SERVICE)
	),
	"input_id": (
		REFERENCE_SOURCE
		+ "_"
		+ aggregated["input_id"]
			.astype("Int64")
			.astype(str)
	),
	"coefficient": aggregated["coefficient"]
})



# print()
# print("FLATTENING AUDIT")
# print(
# 	flattened.to_string(
# 		index=False,
# 		float_format=lambda value: "{:.7f}".format(value)
# 	)
# )

# print()
# print("AGGREGATED TERMINAL INPUTS")
# print(
# 	aggregated.to_string(
# 		index=False,
# 		float_format=lambda value: "{:.7f}".format(value)
# 	)
# )

# print()
# print("CANONICAL COMPOSITION")
# print(
# 	canonical_composition.to_string(
# 		index=False,
# 		float_format=lambda value: "{:.7f}".format(value)
# 	)
# )

PRICE_SHEET = "ISD"
LOCATION = "SC"
PERIOD = "2025-09"


price_raw = pd.read_excel(
	SOURCE_FILE,
	sheet_name=PRICE_SHEET,
	header=None
)


price_header_row = None

for index, row in price_raw.iterrows():
	normalized = [normalize_text(value) for value in row]

	if (
		"CÓDIGO DO INSUMO" in normalized
		and "DESCRIÇÃO DO INSUMO" in normalized
		and "UNIDADE" in normalized
		and "ORIGEM DE PREÇO" in normalized
		and LOCATION in normalized
	):
		price_header_row = index
		break


if price_header_row is None:
	raise ValueError(
		"Could not locate the required header in sheet '{}'."
		.format(PRICE_SHEET)
	)


price_headers = [
	normalize_text(value)
	for value in price_raw.iloc[price_header_row]
]


input_code_col = price_headers.index("CÓDIGO DO INSUMO")
input_description_col = price_headers.index("DESCRIÇÃO DO INSUMO")
input_unit_col = price_headers.index("UNIDADE")
price_origin_col = price_headers.index("ORIGEM DE PREÇO")
location_price_col = price_headers.index(LOCATION)


price_data = price_raw.iloc[
	price_header_row + 1:
].copy()

price_data.iloc[:, input_code_col] = pd.to_numeric(
	price_data.iloc[:, input_code_col],
	errors="coerce"
)

required_input_ids = set(
	aggregated["input_id"]
	.astype("Int64")
	.tolist()
)

selected_source_rows = price_data[
	price_data.iloc[:, input_code_col]
	.isin(required_input_ids)
].copy()

found_input_ids = set(
	selected_source_rows.iloc[:, input_code_col]
	.dropna()
	.astype("Int64")
	.tolist()
)


missing_input_ids = (
	required_input_ids
	- found_input_ids
)


if missing_input_ids:
	raise ValueError(
		"Missing price rows for input IDs: {}."
		.format(
			sorted(missing_input_ids)
		)
	)

duplicated_input_ids = (
	selected_source_rows.iloc[:, input_code_col]
	[
		selected_source_rows.iloc[:, input_code_col]
		.duplicated(keep=False)
	]
	.dropna()
	.astype("Int64")
	.unique()
)


if len(duplicated_input_ids) > 0:
	raise ValueError(
		"Multiple price rows found for input IDs: {}."
		.format(
			sorted(duplicated_input_ids)
		)
	)

selected_source_rows.iloc[:, location_price_col] = pd.to_numeric(
	selected_source_rows.iloc[:, location_price_col],
	errors="coerce"
)


invalid_prices = (
	selected_source_rows.iloc[:, location_price_col].isna()
	| (selected_source_rows.iloc[:, location_price_col] <= 0)
)


if invalid_prices.any():
	invalid_ids = (
		selected_source_rows.loc[
			invalid_prices,
			selected_source_rows.columns[input_code_col]
		]
		.astype("Int64")
		.tolist()
	)

	raise ValueError(
		"Invalid prices for input IDs: {}."
		.format(invalid_ids)
	)

price_audit = pd.DataFrame({
	"input_id":
		selected_source_rows.iloc[:, input_code_col]
		.astype("Int64"),

	"description":
		selected_source_rows.iloc[:, input_description_col],

	"unit":
		selected_source_rows.iloc[:, input_unit_col],

	"price_origin":
		selected_source_rows.iloc[:, price_origin_col],

	"price":
		selected_source_rows.iloc[:, location_price_col]
})

# print()
# print("SELECTED PRICE SOURCE AUDIT")
# print(
# 	price_audit.to_string(
# 		index=False,
# 		float_format=lambda value: "{:.2f}".format(value)
# 	)
# )

# for test_service in [
# 	104658,
# 	88316,
# 	95378
# ]:
# 	print()
# 	print(
# 		"DIRECT DEPENDENCIES:",
# 		test_service
# 	)
# 	print(
# 		extract_dependencies(test_service)
# 		.to_string(index=False)
# 	)

# direct_dependencies = data[
# 	(data.iloc[:, composition_col] == TARGET_SERVICE)
# 	& (data.iloc[:, item_type_col].notna())
# ].copy()


# dependencies = pd.DataFrame({
# 	"item_type": direct_dependencies.iloc[:, item_type_col],
# 	"item_id": direct_dependencies.iloc[:, item_code_col],
# 	"description": direct_dependencies.iloc[:, description_col],
# 	"unit": direct_dependencies.iloc[:, unit_col],
# 	"coefficient": direct_dependencies.iloc[:, coefficient_col],
# 	"situation": direct_dependencies.iloc[:, situation_col]
# })

# allowed_item_types = {
# 	"INSUMO",
# 	"COMPOSICAO"
# }


# dependencies["item_type"] = dependencies["item_type"].map(normalize_text)

# invalid_item_types = (
# 	set(dependencies["item_type"])
# 	- allowed_item_types
# )

# if invalid_item_types:
# 	raise ValueError(
# 		"Unsupported item types found: {}."
# 		.format(sorted(invalid_item_types))
# 	)


# if dependencies["item_id"].isna().any():
# 	raise ValueError(
# 		"Found dependency without item ID in composition {}."
# 		.format(TARGET_SERVICE)
# 	)


# dependencies["coefficient"] = pd.to_numeric(
# 	dependencies["coefficient"],
# 	errors="coerce"
# )


# invalid_coefficients = (
# 	dependencies["coefficient"].isna()
# 	| (dependencies["coefficient"] <= 0)
# )

# if invalid_coefficients.any():
# 	raise ValueError(
# 		"Found invalid coefficient in composition {}."
# 		.format(TARGET_SERVICE)
# 	)


# if dependencies.empty:
# 	raise ValueError(
# 		"Composition {} has no dependencies."
# 		.format(TARGET_SERVICE)
# 	)

# print("HEADER ROW:", header_row)
# print()
# print("EXTRACTED SERVICE")
# print(pd.DataFrame([service]).to_string(index=False))
# print()
# print("DIRECT DEPENDENCIES")
# print(dependencies.to_string(index=False))

print()
print("=" * 70)
print("REFACTORED COMPOSITION MODULE TEST")
print("=" * 70)


ref_data, ref_columns, ref_header_row = (
	composition_adapter.load_analytical_source(
		SOURCE_FILE
	)
)


ref_service = (
	composition_adapter.extract_service(
		ref_data,
		ref_columns,
		TARGET_SERVICE
	)
)


ref_flattened = pd.DataFrame(
	composition_adapter.flatten_composition(
		ref_data,
		ref_columns,
		TARGET_SERVICE
	)
)


ref_aggregated = (
	composition_adapter.aggregate_terminal_inputs(
		ref_flattened
	)
)


ref_services = (
	composition_adapter.build_services(
		ref_service,
		REFERENCE_SOURCE
	)
)


ref_compositions = (
	composition_adapter.build_compositions(
		ref_aggregated,
		TARGET_SERVICE,
		REFERENCE_SOURCE
	)
)


ref_terminal_ids = (
	composition_adapter.get_terminal_input_ids(
		ref_aggregated
	)
)


print()
print("HEADER ROW:", ref_header_row)

print()
print("SERVICES")
print(
	ref_services.to_string(
		index=False
	)
)

print()
print("FLATTENING AUDIT")
print(
	ref_flattened.to_string(
		index=False,
		float_format=lambda value:
			"{:.7f}".format(value)
	)
)

print()
print("AGGREGATED TERMINAL INPUTS")
print(
	ref_aggregated.to_string(
		index=False,
		float_format=lambda value:
			"{:.7f}".format(value)
	)
)

print()
print("CANONICAL COMPOSITION")
print(
	ref_compositions.to_string(
		index=False,
		float_format=lambda value:
			"{:.7f}".format(value)
	)
)

print()
print(
	"TERMINAL INPUT IDS:",
	sorted(ref_terminal_ids)
)

print()
print("=" * 70)
print("REFACTORED PRICE MODULE TEST")
print("=" * 70)


ref_price_data, ref_price_columns, ref_price_header_row = (
	price_adapter.load_price_source(
		SOURCE_FILE,
		LOCATION
	)
)


ref_price_audit = (
	price_adapter.extract_price_rows(
		ref_price_data,
		ref_price_columns,
		ref_terminal_ids,
		LOCATION
	)
)


ref_selected_prices = (
	price_adapter.build_selected_prices(
		ref_price_audit,
		REFERENCE_SOURCE,
		LOCATION,
		PERIOD
	)
)


print()
print(
	"PRICE HEADER ROW:",
	ref_price_header_row
)

print()
print("PRICE EXTRACTION AUDIT")
print(
	ref_price_audit.to_string(
		index=False,
		float_format=lambda value:
			"{:.2f}".format(value)
	)
)

print()
print("CANONICAL SELECTED PRICES")
print(
	ref_selected_prices.to_string(
		index=False,
		float_format=lambda value:
			"{:.2f}".format(value)
	)
)

cross_check = (
	ref_aggregated[
		[
			"input_id",
			"description",
			"unit"
		]
	]
	.merge(
		ref_price_audit[
			[
				"input_id",
				"description",
				"unit"
			]
		],
		on="input_id",
		how="outer",
		suffixes=(
			"_composition",
			"_price"
		)
	)
)

description_mismatch = (
	cross_check["description_composition"]
	!= cross_check["description_price"]
)

unit_mismatch = (
	cross_check["unit_composition"]
	!= cross_check["unit_price"]
)

metadata_mismatch = (
	description_mismatch
	| unit_mismatch
)

if metadata_mismatch.any():
	raise ValueError(
		"Metadata mismatch between Analítico and ISD for input IDs: {}."
		.format(
			cross_check.loc[
				metadata_mismatch,
				"input_id"
			]
			.astype("Int64")
			.tolist()
		)
	)

print()
print(
	"ANALYTICAL / PRICE METADATA CHECK:",
	"OK"
)
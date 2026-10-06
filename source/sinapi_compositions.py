import pandas as pd

from sinapi_utils import (
	normalize_text,
	find_header_row,
	resolve_columns
)

ANALYTICAL_SHEET = "Analítico"

ALLOWED_ITEM_TYPES = {
	"INSUMO",
	"COMPOSICAO"
}


# ============================================================
# EDA / EXTRACTION
# ============================================================

def load_analytical_source(
	source_file,
	sheet_name=ANALYTICAL_SHEET
):
	raw = pd.read_excel(
		source_file,
		sheet_name=sheet_name,
		header=None
	)

	required_headers = [
		"CÓDIGO DA COMPOSIÇÃO",
		"TIPO ITEM",
		"CÓDIGO DO ITEM",
		"DESCRIÇÃO",
		"UNIDADE",
		"COEFICIENTE",
		"SITUAÇÃO"
	]

	header_row = find_header_row(
		raw,
		required_headers
	)

	columns = resolve_columns(
		raw,
		header_row,
		required_headers
	)

	data = raw.iloc[
		header_row + 1:
	].copy()

	return data, columns, header_row


def extract_service(
	data,
	columns,
	service_code
):
	composition_col = columns[
		"CÓDIGO DA COMPOSIÇÃO"
	]

	item_type_col = columns[
		"TIPO ITEM"
	]

	description_col = columns[
		"DESCRIÇÃO"
	]

	unit_col = columns[
		"UNIDADE"
	]

	service_rows = data[
		(data.iloc[:, composition_col] == service_code)
		& (data.iloc[:, item_type_col].isna())
	]

	if len(service_rows) != 1:
		raise ValueError(
			"Expected exactly one service row for composition {}, found {}."
			.format(
				service_code,
				len(service_rows)
			)
		)

	service_row = service_rows.iloc[0]

	description = service_row.iloc[
		description_col
	]

	unit = service_row.iloc[
		unit_col
	]

	if pd.isna(description) or not str(description).strip():
		raise ValueError(
			"Composition {} has no description."
			.format(service_code)
		)

	if pd.isna(unit) or not str(unit).strip():
		raise ValueError(
			"Composition {} has no unit."
			.format(service_code)
		)

	return {
		"source_service_id": int(service_code),
		"description": description,
		"unit": unit
	}


def extract_dependencies(
	data,
	columns,
	service_code
):
	composition_col = columns[
		"CÓDIGO DA COMPOSIÇÃO"
	]

	item_type_col = columns[
		"TIPO ITEM"
	]

	item_code_col = columns[
		"CÓDIGO DO ITEM"
	]

	description_col = columns[
		"DESCRIÇÃO"
	]

	unit_col = columns[
		"UNIDADE"
	]

	coefficient_col = columns[
		"COEFICIENTE"
	]

	situation_col = columns[
		"SITUAÇÃO"
	]

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
		"item_type":
			direct_dependencies.iloc[:, item_type_col],

		"item_id":
			direct_dependencies.iloc[:, item_code_col],

		"description":
			direct_dependencies.iloc[:, description_col],

		"unit":
			direct_dependencies.iloc[:, unit_col],

		"coefficient":
			direct_dependencies.iloc[:, coefficient_col],

		"situation":
			direct_dependencies.iloc[:, situation_col]
	})

	dependencies["item_type"] = (
		dependencies["item_type"]
		.map(normalize_text)
	)

	invalid_item_types = (
		set(dependencies["item_type"])
		- ALLOWED_ITEM_TYPES
	)

	if invalid_item_types:
		raise ValueError(
			"Unsupported item types found in composition {}: {}."
			.format(
				service_code,
				sorted(invalid_item_types)
			)
		)

	dependencies["item_id"] = pd.to_numeric(
		dependencies["item_id"],
		errors="coerce"
	)

	if dependencies["item_id"].isna().any():
		raise ValueError(
			"Found dependency without valid item ID in composition {}."
			.format(service_code)
		)

	non_integer_ids = (
		dependencies["item_id"] % 1 != 0
	)

	if non_integer_ids.any():
		raise ValueError(
			"Found non-integer item ID in composition {}."
			.format(service_code)
		)

	dependencies["item_id"] = (
		dependencies["item_id"]
		.astype("Int64")
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


# ============================================================
# TRANSFORMATION
# ============================================================

def flatten_composition(
	data,
	columns,
	service_code,
	multiplier=1.0,
	path=None,
	factor_chain=None
):
	if path is None:
		path = []

	if factor_chain is None:
		factor_chain = []

	service_code = int(service_code)

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

	current_path = (
		path
		+ [service_code]
	)

	dependencies = extract_dependencies(
		data,
		columns,
		service_code
	)

	terminal_rows = []

	for _, dependency in dependencies.iterrows():
		item_type = dependency[
			"item_type"
		]

		item_id = int(
			dependency["item_id"]
		)

		local_coefficient = dependency[
			"coefficient"
		]

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
				"description":
					dependency["description"],
				"unit":
					dependency["unit"],
				"path":
					" -> ".join(
						str(code)
						for code
						in current_path + [item_id]
					),
				"factor_chain":
					" * ".join(
						str(value)
						for value
						in current_factor_chain
					),
				"coefficient":
					accumulated_coefficient
			})

		elif item_type == "COMPOSICAO":
			child_rows = flatten_composition(
				data,
				columns,
				item_id,
				multiplier=accumulated_coefficient,
				path=current_path,
				factor_chain=current_factor_chain
			)

			terminal_rows.extend(
				child_rows
			)

	return terminal_rows


def aggregate_terminal_inputs(flattened):
	if flattened.empty:
		raise ValueError(
			"Flattening produced no terminal inputs."
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
				list(
					inconsistent_metadata.index
				)
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

	return aggregated


def canonical_id(
	reference_source,
	source_id
):
	return "{}_{}".format(
		reference_source,
		int(source_id)
	)


def build_services(
	source_service,
	reference_source
):
	return pd.DataFrame([
		{
			"service_id": canonical_id(
				reference_source,
				source_service[
					"source_service_id"
				]
			),
			"description":
				source_service["description"],
			"unit":
				source_service["unit"],
			"reference_source":
				reference_source
		}
	])


def build_compositions(
	aggregated,
	service_code,
	reference_source
):
	compositions = aggregated[
		[
			"input_id",
			"coefficient"
		]
	].copy()

	compositions.insert(
		0,
		"service_id",
		canonical_id(
			reference_source,
			service_code
		)
	)

	compositions["input_id"] = (
		compositions["input_id"]
		.apply(
			lambda input_id:
				canonical_id(
					reference_source,
					input_id
				)
		)
	)

	return compositions


def get_terminal_input_ids(
	aggregated
):
	return set(
		aggregated["input_id"]
		.astype("Int64")
		.tolist()
	)
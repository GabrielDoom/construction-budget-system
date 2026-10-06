import pandas as pd

from sinapi_utils import (
	normalize_text,
	find_header_row,
	resolve_columns
)


PRICE_SHEET = "ISD"


# ============================================================
# EDA / EXTRACTION
# ============================================================

def load_price_source(
	source_file,
	location,
	sheet_name=PRICE_SHEET
):
	location = normalize_text(location)

	raw = pd.read_excel(
		source_file,
		sheet_name=sheet_name,
		header=None
	)

	required_headers = [
		"CÓDIGO DO INSUMO",
		"DESCRIÇÃO DO INSUMO",
		"UNIDADE",
		"ORIGEM DE PREÇO",
		location
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


def extract_price_rows(
	data,
	columns,
	required_input_ids,
	location
):
	location = normalize_text(location)

	required_input_ids = {
		int(input_id)
		for input_id in required_input_ids
	}

	if not required_input_ids:
		raise ValueError(
			"No input IDs supplied for price extraction."
		)

	input_code_name = data.columns[
		columns["CÓDIGO DO INSUMO"]
	]

	description_name = data.columns[
		columns["DESCRIÇÃO DO INSUMO"]
	]

	unit_name = data.columns[
		columns["UNIDADE"]
	]

	price_origin_name = data.columns[
		columns["ORIGEM DE PREÇO"]
	]

	price_name = data.columns[
		columns[location]
	]

	extracted = pd.DataFrame({
		"input_id":
			data[input_code_name],

		"description":
			data[description_name],

		"unit":
			data[unit_name],

		"price_origin":
			data[price_origin_name],

		"price":
			data[price_name]
	})

	extracted["input_id"] = pd.to_numeric(
		extracted["input_id"],
		errors="coerce"
	)

	# Rows that are not actual input records are irrelevant here.
	extracted = extracted[
		extracted["input_id"].notna()
	].copy()

	non_integer_ids = (
		extracted["input_id"] % 1 != 0
	)

	if non_integer_ids.any():
		raise ValueError(
			"Found non-integer input IDs in price source."
		)

	extracted["input_id"] = (
		extracted["input_id"]
		.astype("Int64")
	)

	price_rows = extracted[
		extracted["input_id"]
		.isin(required_input_ids)
	].copy()

	found_input_ids = set(
		price_rows["input_id"]
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
		price_rows.loc[
			price_rows["input_id"]
			.duplicated(keep=False),
			"input_id"
		]
		.astype("Int64")
		.unique()
	)

	if len(duplicated_input_ids) > 0:
		raise ValueError(
			"Multiple price rows found for input IDs: {}."
			.format(
				sorted(
					int(input_id)
					for input_id
					in duplicated_input_ids
				)
			)
		)

	price_rows["price"] = pd.to_numeric(
		price_rows["price"],
		errors="coerce"
	)

	invalid_prices = (
		price_rows["price"].isna()
		| (price_rows["price"] <= 0)
	)

	if invalid_prices.any():
		invalid_input_ids = (
			price_rows.loc[
				invalid_prices,
				"input_id"
			]
			.astype("Int64")
			.tolist()
		)

		raise ValueError(
			"Invalid prices for input IDs: {}."
			.format(invalid_input_ids)
		)

	price_rows["price_origin"] = (
		price_rows["price_origin"]
		.map(normalize_text)
	)

	price_rows = (
		price_rows
		.sort_values("input_id")
		.reset_index(drop=True)
	)

	return price_rows


# ============================================================
# TRANSFORMATION
# ============================================================

def build_selected_prices(
	price_rows,
	reference_source,
	location,
	period
):
	reference_source = normalize_text(
		reference_source
	)

	location = normalize_text(
		location
	)

	if not reference_source:
		raise ValueError(
			"Reference source cannot be empty."
		)

	if not location:
		raise ValueError(
			"Location cannot be empty."
		)

	if not str(period).strip():
		raise ValueError(
			"Period cannot be empty."
		)

	selected_prices = pd.DataFrame({
		"input_id":
			price_rows["input_id"]
			.apply(
				lambda input_id:
					"{}_{}".format(
						reference_source,
						int(input_id)
					)
			),

		"price":
			price_rows["price"],

		"supplier":
			"",

		"reference_source":
			reference_source,

		"location":
			location,

		"period":
			str(period)
	})

	return selected_prices
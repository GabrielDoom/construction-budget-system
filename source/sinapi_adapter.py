import pandas as pd

import sinapi_compositions as composition_adapter
import sinapi_prices as price_adapter


SOURCE_FILE = (
	"reference/SINAPI-2025-09-formato-xlsx/"
	"SINAPI_Referência_2025_09.xlsx"
)

TARGET_SERVICE = 104658
REFERENCE_SOURCE = "SINAPI"
LOCATION = "SC"
PERIOD = "2025-09"


def main():
	# --------------------------------------------------------
	# COMPOSITIONS
	# --------------------------------------------------------

	data, columns, header_row = (
		composition_adapter.load_analytical_source(
			SOURCE_FILE
		)
	)

	source_service = (
		composition_adapter.extract_service(
			data,
			columns,
			TARGET_SERVICE
		)
	)

	flattened = pd.DataFrame(
		composition_adapter.flatten_composition(
			data,
			columns,
			TARGET_SERVICE
		)
	)

	aggregated = (
		composition_adapter.aggregate_terminal_inputs(
			flattened
		)
	)

	services = (
		composition_adapter.build_services(
			source_service,
			REFERENCE_SOURCE
		)
	)

	compositions = (
		composition_adapter.build_compositions(
			aggregated,
			TARGET_SERVICE,
			REFERENCE_SOURCE
		)
	)

	required_input_ids = (
		composition_adapter.get_terminal_input_ids(
			aggregated
		)
	)


	# --------------------------------------------------------
	# PRICES
	# --------------------------------------------------------

	price_data, price_columns, price_header_row = (
		price_adapter.load_price_source(
			SOURCE_FILE,
			LOCATION
		)
	)

	price_audit = (
		price_adapter.extract_price_rows(
			price_data,
			price_columns,
			required_input_ids,
			LOCATION
		)
	)

	selected_prices = (
		price_adapter.build_selected_prices(
			price_audit,
			REFERENCE_SOURCE,
			LOCATION,
			PERIOD
		)
	)


	# --------------------------------------------------------
	# CROSS-SOURCE AUDIT
	# --------------------------------------------------------

	cross_check = (
		aggregated[
			[
				"input_id",
				"description",
				"unit"
			]
		]
		.merge(
			price_audit[
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

	metadata_mismatch = (
		(
			cross_check["description_composition"]
			!= cross_check["description_price"]
		)
		|
		(
			cross_check["unit_composition"]
			!= cross_check["unit_price"]
		)
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


	# --------------------------------------------------------
	# SESSION AUDIT OUTPUT
	# --------------------------------------------------------

	print()
	print("SERVICES")
	print(
		services.to_string(
			index=False
		)
	)

	print()
	print("CANONICAL COMPOSITION")
	print(
		compositions.to_string(
			index=False,
			float_format=lambda value:
				"{:.7f}".format(value)
		)
	)

	print()
	print("SELECTED PRICES")
	print(
		selected_prices.to_string(
			index=False,
			float_format=lambda value:
				"{:.2f}".format(value)
		)
	)

	print()
	print(
		"ANALYTICAL / PRICE METADATA CHECK: OK"
	)


if __name__ == "__main__":
	main()
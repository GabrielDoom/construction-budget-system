import pandas as pd

import sinapi_compositions as composition_adapter
import sinapi_prices as price_adapter
import sinapi_audit

SOURCE_FILE = (
	"reference/SINAPI-2025-09-formato-xlsx/"
	"SINAPI_Referência_2025_09.xlsx"
)

SERVICE_CODES = [
	104658
]

#TARGET_SERVICE = 104658
REFERENCE_SOURCE = "SINAPI"
LOCATION = "SC"
PERIOD = "2025-09"
AUDIT = False

def main():
	# --------------------------------------------------------
	# COMPOSITIONS
	# --------------------------------------------------------

	data, columns, header_row = (
		composition_adapter.load_analytical_source(
			SOURCE_FILE
		)
	)

	composition_audits = {}

	service_frames = []
	composition_frames = []
	terminal_metadata_frames = []


	if not SERVICE_CODES:
		raise ValueError(
			"No service codes supplied."
		)


	normalized_service_codes = [
		int(service_code)
		for service_code in SERVICE_CODES
	]


	if len(normalized_service_codes) != len(
		set(normalized_service_codes)
	):
		raise ValueError(
			"Duplicate service codes supplied."
		)

	for service_code in normalized_service_codes:
		source_service = (
			composition_adapter.extract_service(
				data,
				columns,
				service_code
			)
		)

		flattened = pd.DataFrame(
			composition_adapter.flatten_composition(
				data,
				columns,
				service_code
			)
		)

		aggregated = (
			composition_adapter.aggregate_terminal_inputs(
				flattened
			)
		)

		service_frames.append(
			composition_adapter.build_services(
				source_service,
				REFERENCE_SOURCE
			)
		)

		composition_frames.append(
			composition_adapter.build_compositions(
				aggregated,
				service_code,
				REFERENCE_SOURCE
			)
		)

		terminal_metadata_frames.append(
			aggregated[
				[
					"input_id",
					"description",
					"unit"
				]
			].copy()
		)

		composition_audits[service_code] = {
			"source_service": source_service,
			"flattened": flattened,
			"aggregated": aggregated
		}

	services = pd.concat(
		service_frames,
		ignore_index=True
	)


	compositions = pd.concat(
		composition_frames,
		ignore_index=True
	)


	terminal_metadata = pd.concat(
		terminal_metadata_frames,
		ignore_index=True
	)

	terminal_metadata_check = (
		terminal_metadata
		.groupby("input_id")
		.agg({
			"description": "nunique",
			"unit": "nunique"
		})
	)


	inconsistent_terminal_metadata = (
		terminal_metadata_check[
			(terminal_metadata_check["description"] > 1)
			| (terminal_metadata_check["unit"] > 1)
		]
	)


	if not inconsistent_terminal_metadata.empty:
		raise ValueError(
			"Inconsistent terminal input metadata for IDs: {}."
			.format(
				list(
					inconsistent_terminal_metadata.index
				)
			)
		)	


	terminal_catalog = (
		terminal_metadata
		.groupby(
			"input_id",
			as_index=False
		)
		.agg({
			"description": "first",
			"unit": "first"
		})
	)

	required_input_ids = set(
		terminal_catalog["input_id"]
		.astype("Int64")
		.tolist()
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
		terminal_catalog[
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

	if AUDIT:
		for service_code in normalized_service_codes:
			audit = composition_audits[
				service_code
			]

			sinapi_audit.print_composition_audit(
				audit["source_service"],
				audit["flattened"],
				audit["aggregated"]
			)

		sinapi_audit.print_price_audit(
			price_audit,
			LOCATION,
			PERIOD
		)

		sinapi_audit.print_cross_source_audit(
			metadata_mismatch.any()
		)

	# --------------------------------------------------------
	# CANONICAL OUTPUT
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

if __name__ == "__main__":
	main()
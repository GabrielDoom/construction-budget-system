def print_composition_audit(
	source_service,
	flattened,
	aggregated
):
	print()
	print("=" * 70)
	print("COMPOSITION AUDIT")
	print("=" * 70)

	print()
	print("SOURCE SERVICE")
	print(
		"{} | {} | {}".format(
			source_service["source_service_id"],
			source_service["description"],
			source_service["unit"]
		)
	)

	print()
	print("FLATTENING PATHS")
	print(
		flattened.to_string(
			index=False,
			float_format=lambda value:
				"{:.7f}".format(value)
		)
	)

	print()
	print("AGGREGATED TERMINAL INPUTS")
	print(
		aggregated.to_string(
			index=False,
			float_format=lambda value:
				"{:.7f}".format(value)
		)
	)


def print_price_audit(
	price_rows,
	location,
	period
):
	print()
	print("=" * 70)
	print("PRICE AUDIT")
	print("=" * 70)

	print()
	print(
		"CONTEXT: {} | {}".format(
			location,
			period
		)
	)

	print()
	print("SOURCE PRICE ROWS")
	print(
		price_rows.to_string(
			index=False,
			float_format=lambda value:
				"{:.2f}".format(value)
		)
	)


def print_cross_source_audit(
	metadata_mismatch
):
	print()
	print("=" * 70)
	print("CROSS-SOURCE AUDIT")
	print("=" * 70)

	if metadata_mismatch:
		print(
			"Analytical / price metadata check: FAILED"
		)
	else:
		print(
			"Analytical / price metadata check: OK"
		)
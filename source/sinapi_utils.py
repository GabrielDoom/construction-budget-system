import pandas as pd


def normalize_text(value):
	if pd.isna(value):
		return ""

	return " ".join(
		str(value)
		.replace("\n", " ")
		.split()
	).upper()


def find_header_row(raw, required_headers):
	for index, row in raw.iterrows():
		normalized = [
			normalize_text(value)
			for value in row
		]

		if all(
			header in normalized
			for header in required_headers
		):
			return index

	raise ValueError(
		"Could not locate required headers: {}."
		.format(required_headers)
	)


def resolve_columns(raw, header_row, required_headers):
	headers = [
		normalize_text(value)
		for value in raw.iloc[header_row]
	]

	columns = {}

	for header in required_headers:
		positions = [
			index
			for index, value in enumerate(headers)
			if value == header
		]

		if len(positions) != 1:
			raise ValueError(
				"Expected exactly one column '{}', found {}."
				.format(
					header,
					len(positions)
				)
			)

		columns[header] = positions[0]

	return columns
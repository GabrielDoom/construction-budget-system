import pandas as pd


def build_requirements_cli(
	services,
	compositions
):
	materialized_ids = set(
		compositions["service_id"]
		.dropna()
		.unique()
	)

	available_services = (
		services[
			services["service_id"].isin(
				materialized_ids
			)
		]
		[
			[
				"service_id",
				"source_service_id",
				"description",
				"unit"
			]
		]
		.sort_values("source_service_id")
		.reset_index(drop=True)
	)

	missing_catalog_entries = (
		materialized_ids
		- set(available_services["service_id"])
	)

	if missing_catalog_entries:
		raise ValueError(
			"Materialized services absent from catalog: {}."
			.format(
				sorted(missing_catalog_entries)
			)
		)

	if available_services.empty:
		raise ValueError(
			"No materialized services available."
		)

	print()
	print("=" * 30)
	print("SERVIÇOS DISPONÍVEIS")
	print("=" * 30)
	print()

	for index, row in available_services.iterrows():
		print(
			"{}. {} | {} | {}".format(
				index + 1,
				row["source_service_id"],
				row["description"],
				row["unit"]
			)
		)

	requirements = []

	while True:
		print()

		selection = input(
			"Selecione um serviço "
			"(Enter para concluir): "
		).strip()

		if selection == "":
			if requirements:
				break

			print(
				"Selecione pelo menos um serviço."
			)
			continue

		try:
			selection = int(selection)
		except ValueError:
			print("Seleção inválida.")
			continue

		if not (
			1 <= selection
			<= len(available_services)
		):
			print("Seleção inválida.")
			continue

		selected_service = (
			available_services.iloc[
				selection - 1
			]
		)

		quantity_text = input(
			"Quantidade [{}]: ".format(
				selected_service["unit"]
			)
		).strip()

		try:
			quantity = float(
				quantity_text.replace(",", ".")
			)
		except ValueError:
			print("Quantidade inválida.")
			continue

		if quantity <= 0:
			print(
				"A quantidade deve ser positiva."
			)
			continue

		requirements.append({
			"service_id":
				selected_service["service_id"],
			"quantity":
				quantity
		})

	requirements = pd.DataFrame(
		requirements
	)

	requirements = (
		requirements
		.groupby(
			"service_id",
			as_index=False
		)["quantity"]
		.sum()
	)

	return requirements
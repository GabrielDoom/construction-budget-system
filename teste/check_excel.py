import pandas as pd

ref_file = "reference/SINAPI-2025-09-formato-xlsx/SINAPI_Referência_2025_09.xlsx"
coef_file = "reference/SINAPI-2025-09-formato-xlsx/SINAPI_familias_e_coeficientes_2025_09.xlsx"

targets = [
	(ref_file, "ISD"),
	(ref_file, "CSD"),
	(ref_file, "Analítico"),
	(ref_file, "Analítico com Custo"),
	(coef_file, "Coeficientes"),
]

for file, sheet in targets:
	print("\n" + "=" * 70)
	print("SHEET:", sheet)
	print("=" * 70)

	df = pd.read_excel(
		file,
		sheet_name=sheet,
		header=None,
		nrows=12
	)

	print(df.to_string(index=False, header=False))
import pandas as pd

# Specify your CSV file name and the desired XLSX file name
csv_file = 'output.csv'
xlsx_file = 'output.xlsx'

# Read the CSV into a DataFrame
df = pd.read_csv(csv_file)

# Write the DataFrame to an Excel file
df.to_excel(xlsx_file, index=False)

print(f"Successfully converted {csv_file} to {xlsx_file}")

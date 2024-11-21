import pandas as pd

# Replace with your published sheet URL
sheet_url = "https://docs.google.com/spreadsheets/d/1PzYgCDP4Xb5Dv-2rx-G6PfGiw7bu-m-pfrca8q9V9oA/export?format=csv"
data = pd.read_csv(sheet_url)

print("Data from Google Sheet:")
print(data)
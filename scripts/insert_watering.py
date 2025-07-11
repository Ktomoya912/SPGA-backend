import csv
import sqlite3
from datetime import datetime
from pathlib import Path

database_path = Path(__file__).parent.parent / "app.db"
csv_file_path = Path(__file__).parent.parent / "watering.csv"
if not database_path.exists():
    raise FileNotFoundError(f"Database file not found at {database_path}")

data = []
with open(csv_file_path, "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        data.append(row)

conn = sqlite3.connect(database_path)
cursor = conn.cursor()
# Insert data into the plants table
for i, row in enumerate(data):
    cursor.execute(
        """
        INSERT INTO waterings (id, plant_id, month, frequency, amount, humidity_when_dry, humidity_when_watered, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            i + 1,
            row["plant_ID"],
            row["month"],
            row["frequency"],
            row["quantity"],
            row["humidity_when_dry"],
            row["humidity_when_watered"],
            datetime.now(),
            datetime.now(),
        ),
    )

# Commit the changes and close the connection
conn.commit()
cursor.close()
conn.close()
print(f"Data inserted successfully into {database_path}")

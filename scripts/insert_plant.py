import csv
import sqlite3
from datetime import datetime
from pathlib import Path

database_path = Path(__file__).parent.parent / "app.db"
if not database_path.exists():
    raise FileNotFoundError(f"Database file not found at {database_path}")

csv_file_path = Path(__file__).parent.parent / "plant.csv"
data = []
with open(csv_file_path, "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        data.append(row)

conn = sqlite3.connect(database_path)
cursor = conn.cursor()
# Insert data into the plants table
for row in data:
    cursor.execute(
        """
        INSERT INTO plants (id, name_jp, name_en, description, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            row["id"],
            row["name_jp"],
            row["name_en"],
            row["description"],
            datetime.now(),
            datetime.now(),
        ),
    )

# Commit the changes and close the connection
conn.commit()
cursor.close()
conn.close()
print(f"Data inserted successfully into {database_path}")

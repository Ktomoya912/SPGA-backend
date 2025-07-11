import csv
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

load_dotenv()

DB_PATH = Path(__file__).parent.parent / "app.db"
DB_URL = f"sqlite:///{DB_PATH}"
plant_csv = Path(__file__).parent.parent / "plant.csv"
watering_csv = Path(__file__).parent.parent / "watering.csv"

with open(plant_csv, "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    plant_data = [row for row in reader]
with open(watering_csv, "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    watering_data = [row for row in reader]

engine = create_engine(DB_URL, echo=False)


def create_db_and_tables():
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    if DB_PATH.exists():
        DB_PATH.unlink()
    create_db_and_tables()
    with Session(engine) as session:
        from app import models

        for row in plant_data:
            plant = models.Plant(
                id=row["id"],
                name_jp=row["name_jp"],
                name_en=row["name_en"],
                description=row["description"],
                originalContentUrl=row["originalContentUrl"],
                previewImageUrl=row["originalContentUrl"],
            )
            session.add(plant)
        session.commit()

        for row in watering_data:
            watering = models.Watering(
                plant_id=int(row["plant_ID"]),
                month=row["month"],
                frequency=row["frequency"],
                amount=row["quantity"],
                humidity_when_dry=int(row["humidity_when_dry"]),
                humidity_when_watered=int(row["humidity_when_watered"]),
            )
            session.add(watering)
        session.commit()

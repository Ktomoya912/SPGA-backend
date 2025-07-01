from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app import db

if TYPE_CHECKING:
    from app.models.plant import Plant


class WateringBase(db.BaseModel):
    id: int = Field(description="水やりID", primary_key=True)
    plant_id: int = Field(description="植物ID", foreign_key="plants.id")
    date: str = Field(description="水やり日付")
    amount: float = Field(description="水の量 (ml)")


class Watering(WateringBase, table=True):
    __tablename__ = "waterings"

    plant: "Plant" = Relationship(
        sa_relationship_kwargs={"lazy": "joined"},
        back_populates="waterings",
    )

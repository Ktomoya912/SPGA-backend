from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app import db

if TYPE_CHECKING:
    from app.models.plant import Plant


class WateringBase(db.BaseModel):
    id: int = Field(description="水やりID", primary_key=True)
    plant_id: int = Field(description="植物ID", foreign_key="plants.id")
    month: str = Field(description="対象月")
    frequency: str = Field(description="水やり頻度")
    amount: str = Field(description="水やり量")
    humidity_when_dry: int = Field(
        description="乾燥時の湿度",
        default=-1,)
    humidity_when_watered: int = Field(
        description="水やり時の湿度",
        default=2000,
    )


class Watering(WateringBase, table=True):
    __tablename__ = "waterings"

    plant: "Plant" = Relationship(
        back_populates="waterings",
    )

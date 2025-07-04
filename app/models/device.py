from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app import db

if TYPE_CHECKING:
    from app.models.registed import Registed


class DeviceBase(db.BaseModel):
    id: int = Field(description="デバイスID", primary_key=True)
    name: str = Field(
        default=None,
        nullable=False,
        description="デバイス名",
    )
    plant_id: int = Field(
        description="植物ID",
        foreign_key="plants.id",
        nullable=False,
    )


class Device(DeviceBase, table=True):
    __tablename__ = "devices"

    plant: list["Registed"] = Relationship(
        back_populates="device",
    )

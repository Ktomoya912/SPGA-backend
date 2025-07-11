from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app import db

if TYPE_CHECKING:
    from app.models.registed import Registed
    from app.models.user import User


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
    user_id: str = Field(
        description="ユーザーID",
        foreign_key="users.id",
        nullable=False,
    )


class Device(DeviceBase, table=True):
    __tablename__ = "devices"

    user: "User" = Relationship(back_populates="devices")
    plant: list["Registed"] = Relationship(
        back_populates="device",
    )

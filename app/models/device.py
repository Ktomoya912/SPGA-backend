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


class Device(DeviceBase, table=True):
    __tablename__ = "devices"
    plant: list["Registed"] = Relationship(
        back_populates="device",
    )

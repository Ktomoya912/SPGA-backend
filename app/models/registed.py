from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app import db

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.plant import Plant
    from app.models.user import User


class RegistedBase(db.BaseModel):
    id: int = Field(
        primary_key=True,
        description="登録ID, 一意の識別子として使用される。",
    )
    user_id: str = Field(
        description="ユーザーID, ユーザーを識別するために使用される。",
        nullable=True,
        foreign_key="users.id",
    )
    plant_id: int = Field(
        description="植物ID, 機械学習の結果と一致している必要がある。",
        foreign_key="plants.id",
    )
    device_id: int = Field(
        description="デバイスID",
        foreign_key="devices.id",
    )


class Registed(RegistedBase, table=True):
    __tablename__ = "registed_plants"

    device: "Device" = Relationship(
        back_populates="plant",
    )
    plant: "Plant" = Relationship(
        back_populates="registed_plants",
    )
    user: "User" = Relationship(
        back_populates="registed_plants",
    )

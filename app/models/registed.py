from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app import db

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.plant import Plant


class RegistedBase(db.BaseModel):
    id: int = Field(
        primary_key=True,
        description="登録ID, 一意の識別子として使用される。",
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
        sa_relationship_kwargs={"lazy": "joined"},
        back_populates="registed_devices",
    )
    plant: "Plant" = Relationship(
        sa_relationship_kwargs={"lazy": "joined"},
        back_populates="registed_plants",
    )

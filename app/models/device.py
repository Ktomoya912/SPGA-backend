from sqlmodel import Field, SQLModel


class DeviceBase(SQLModel):
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

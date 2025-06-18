from sqlmodel import Field, SQLModel


class WateringBase(SQLModel):
    id: int = Field(description="水やりID", primary_key=True)
    plant_id: int = Field(description="植物ID", foreign_key="plants.id")
    date: str = Field(description="水やり日付")
    amount: float = Field(description="水の量 (ml)")

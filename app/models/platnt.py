from sqlmodel import Field, SQLModel


class PlantBase(SQLModel):
    id: int = Field(
        description="植物ID, 機械学習の結果と一致している必要がある。", primary_key=True
    )
    name_jp = Field(
        default=None,
        description="日本語の植物名",
        unique=True,
    )
    name_en = Field(
        description="英語の植物名",
        unique=True,
    )
    description = Field(
        default=None,
        description="植物の説明",
        nullable=True,
    )


class Plant(PlantBase, table=True):
    __tablename__ = "plants"

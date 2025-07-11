from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app import db

if TYPE_CHECKING:
    from app.models.registed import Registed
    from app.models.watering import Watering
    from app.models.notification_history import NotificationHistory 


class PlantBase(db.BaseModel):
    id: int = Field(
        description="植物ID, 機械学習の結果と一致している必要がある。", primary_key=True
    )
    name_jp: str = Field(
        default=None,
        description="日本語の植物名",
        unique=True,
    )
    name_en: str = Field(
        description="英語の植物名",
        unique=True,
    )
    description: str = Field(
        default=None,
        description="植物の説明",
        nullable=True,
    )
    previewImageUrl: str = Field(
        default=None,
        description="植物のプレビュー画像URL",
        nullable=True,
    )
    originalContentUrl: str = Field(
        default=None,
        description="植物のオリジナルコンテンツURL",
        nullable=True,
    )


class Plant(PlantBase, table=True):
    __tablename__ = "plants"
    registed_plants: list["Registed"] = Relationship(back_populates="plant")
    waterings: list["Watering"] = Relationship(back_populates="plant")
    notification_histories: list["NotificationHistory"] = Relationship(  # この行を追加
        back_populates="plant"
    )

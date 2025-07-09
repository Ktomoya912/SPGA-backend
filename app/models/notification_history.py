from typing import TYPE_CHECKING, Optional
from datetime import datetime

from sqlmodel import Field, Relationship

from app import db

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.plant import Plant
    from app.models.user import User


class NotificationHistoryBase(db.BaseModel):
    id: Optional[int] = Field(
        primary_key=True,
        description="通知履歴ID, 一意の識別子として使用される。",
        default=None,
    )
    user_id: str = Field(
        description="ユーザーID, ユーザーを識別するために使用される。",
        foreign_key="users.id",
    )
    plant_id: int = Field(
        description="植物ID (植物種類のIDでないことは注意)",
        foreign_key="plants.id",
    )
    notification_type: str = Field(
        description="通知タイプ（watering, reminder等）",
        default="watering"
    )
    message: str = Field(
        description="通知メッセージ内容"
    )
    sent_at: datetime = Field(
        description="送信日時",
        default_factory=datetime.now
    )
    last_flg: bool = Field(
        description="最新フラグ, Trueの場合は最新の通知",
        default=True,
    )


class NotificationHistory(NotificationHistoryBase, table=True):
    __tablename__ = "notification_histories"

    plant: "Plant" = Relationship(
        back_populates="notification_histories",
    )
    user: "User" = Relationship(
        back_populates="notification_histories",
    )
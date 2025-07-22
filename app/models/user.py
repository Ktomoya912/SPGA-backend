from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from app import db

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.notification_history import NotificationHistory
    from app.models.registed import Registed


class UserBase(db.BaseModel):
    id: str = Field(
        description="LINEメッセージから取得したユーザーID", primary_key=True
    )
    current_predict: Optional[str] = Field(
        default=None,
        description="現在の予測結果",
        nullable=True,
    )
    delete_mode: bool = Field(
        default=False,
        description="削除モードかどうか",
    )
    awaiting_device_id: int = Field(
        description="デバイスID入力待ちフラグ", 
        default=0
    )


class User(UserBase, table=True):
    __tablename__ = "users"

    registed_plants: list["Registed"] = Relationship(
        back_populates="user",
    )
    notification_histories: list["NotificationHistory"] = Relationship(
        back_populates="user"
    )

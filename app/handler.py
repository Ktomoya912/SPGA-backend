import logging
import re
import time
from datetime import datetime

from linebot.v3.messaging import MessagingApi, PushMessageRequest, TextMessage
from sqlmodel import Session, desc, select

from app import db, models

logger = logging.getLogger(__name__)


def handler(line_bot_api: MessagingApi):
    logger.info("水やりチェックシステムを開始します...")

    # 1秒もしくは30分ごとに湿度を取る。
    # 登録テーブルからすべてのデータを取る。
    with Session(db.engine) as session:
        try:
            while True:
                logger.info("水やりチェックを開始します...")
                current_time = datetime.now()
                users_list = get_users(session)
                current_month = current_time.month
                current_hour = current_time.hour
                if current_hour < 8 or current_hour > 21:
                    logger.info(
                        "現在の時間は水やりチェックの時間外です。スキップします。"
                    )
                    time.sleep(600)

                for user in users_list:
                    # ユーザーの登録済み植物を取得
                    logger.info(f"ユーザー {user.id} の水やりチェックを開始します...")
                    for registed in user.registed_plants:
                        latest_notification = get_latest_notification(
                            session, user.id, registed.plant_id
                        )
                        if (
                            latest_notification
                            and latest_notification.sent_at
                            > current_time.replace(hour=0, minute=0, second=0)
                        ):
                            logger.info(
                                f"{user.id} の植物 {registed.plant_id} は最近通知済みのためスキップ"
                            )
                            continue
                        plant_watering_data = get_watering_data(
                            session, current_month, registed.plant_id
                        )
                        logger.debug(
                            f"🔍 デバッグ: 検索対象のregisted.plant_id: {registed.plant_id}"
                        )
                        humidity = get_humidity(registed.device_id)  # 湿度データを取得
                        if check_watering_schedule(
                            plant_watering_data,
                            current_time,
                            humidity,
                            last_watering_date=(
                                latest_notification.sent_at
                                if latest_notification
                                else None
                            ),
                        ):
                            notification = record_notification_history(
                                session,
                                user.id,
                                registed.plant,
                                plant_watering_data,
                            )
                            # line bot api 挿入用の場所
                            line_bot_api.push_message_with_http_info(
                                push_message_request=PushMessageRequest(
                                    to=user.id,
                                    messages=[
                                        TextMessage(text=notification.message),
                                    ],
                                )
                            )

                # 1分間待機
                logger.info("60秒間待機します...")
                time.sleep(60)

        except KeyboardInterrupt:
            logger.info("\n水やりチェックシステムを停止しました")
        except Exception as e:
            logger.info(f"エラーが発生しました: {e}")
            import traceback

            traceback.print_exc()


def get_users(session: Session):
    """全ユーザーを取得"""
    users = session.exec(select(models.User)).all()

    return users


def get_watering_data(session: Session, month: int, plant_id: int):
    """指定した植物、指定した月の水やり頻度データを取得"""
    watering_data = session.exec(
        select(models.Watering).where(
            models.Watering.plant_id == plant_id,
            models.Watering.month == f"{month}",
        )
    ).first()
    logger.info(f"取得した水やりデータ: {watering_data}")
    return watering_data


def get_latest_notification(session: Session, user_id: str, plant_id: int):
    """特定のユーザーと植物の最新の通知履歴を取得"""
    notification = session.exec(
        select(models.NotificationHistory)
        .where(
            models.NotificationHistory.user_id == user_id,
            models.NotificationHistory.plant_id == plant_id,
        )
        .order_by(desc(models.NotificationHistory.sent_at))
    ).first()

    return notification


def get_humidity(device_id: int):
    """湿度データを取得"""
    # ここでは湿度データの取得方法を仮定しています。
    # 実際の実装では、センサーやAPIから湿度データを取得する必要があります。
    return 50  # 仮の湿度値


def check_watering_schedule(
    watering_data: models.Watering,
    current_time: datetime,
    humidity: float = None,
    last_watering_date: datetime = None,
):
    """水やりが必要かどうかを判定"""
    logger.info(watering_data)
    frequency = watering_data.frequency.lower()
    logger.info(f"Frequency: {frequency}")

    has_number = re.search(r"\d+", frequency)

    if has_number:
        # 数字がある場合：前回水をあげた日付との比較
        if last_watering_date is None:
            logger.warning("    ⚠️ 前回の水やり日付が不明です")
            return True  # 初回は水やりを推奨

        # 数字を抽出
        days_match = re.search(r"(\d+)", frequency)
        if days_match:
            target_days = int(days_match.group(1))

            # 前回の水やりからの経過日数を計算
            days_since_last_watering = (
                current_time.date() - last_watering_date.date()
            ).days

            logger.info(
                f"    📅 前回の水やりから{days_since_last_watering}日経過（目安: {target_days}日に1回）"
            )

            if days_since_last_watering >= target_days:
                return True
            else:
                logger.info(
                    f"    ⏳ あと{target_days - days_since_last_watering}日後に水やり予定"
                )
                return False

    else:
        # 数字がない場合：湿度比較
        humidity_when_dry = watering_data.humidity_when_dry
        if humidity is None:
            logger.warning("⚠️ 湿度データが取得できません")
            return False

        logger.info(f"    💧 現在の湿度: {humidity}% (乾燥基準: {humidity_when_dry}%)")

        if humidity <= humidity_when_dry:
            logger.info("    ✅ 土が乾燥しています")
            return True
        else:
            logger.info("    🚫 まだ湿っています")
            return False

    return False


def record_notification_history(
    session: Session,
    user_id: str,
    plant: models.Plant,
    watering_data: models.Watering,
):
    """通知履歴を記録する"""
    try:

        # 新しい通知履歴を作成
        new_notification = models.NotificationHistory(
            user_id=user_id,
            plant_id=plant.id,
            notification_type="watering",
            message=f"{plant.name_jp}の水やりが必要です。\n水やり頻度: {watering_data.frequency}\n水やり量: {watering_data.amount}",
        )
        session.add(new_notification)
        session.commit()

        logger.info(f"✅ 通知履歴を記録しました: {user_id} -> {plant.name_jp}")
        return new_notification
    except Exception as notification_error:
        logger.error(f"⚠️ 通知履歴の記録に失敗しました: {notification_error}")
        # 通知履歴の記録に失敗してもメイン処理は継続
        return False


if __name__ == "__main__":
    handler()

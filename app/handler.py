import logging
import re
import threading
import time
from datetime import datetime

import spidev
from linebot.v3.messaging import MessagingApi, PushMessageRequest, TextMessage
from sqlmodel import Session, desc, select

from app import db, models

logger = logging.getLogger(__name__)


def handler(line_bot_api: MessagingApi, stop_event: threading.Event):
    logger.info("水やりチェックシステムを開始します...")

    # 1秒もしくは30分ごとに湿度を取る。
    # 登録テーブルからすべてのデータを取る。

    try:
        while not stop_event.is_set():
            with Session(db.engine) as session:
                logger.info("水やりチェックを開始します...")
                current_time = datetime.now()
                users_list = get_users(session)
                current_month = current_time.month
                current_hour = current_time.hour
                # if current_hour < 8 or current_hour > 21:
                if False:
                    logger.info(
                        "現在の時間は水やりチェックの時間外です。スキップします。"
                    )
                    time.sleep(600)

                for user in users_list:
                    session.refresh(user)
                    # ユーザーの登録済み植物を取得
                    logger.info(f"ユーザー {user.id} の水やりチェックを開始します...")
                    logger.info(f"登録済み植物: {user.registed_plants}")
                    for registed in user.registed_plants:
                        latest_notification = get_latest_notification(
                            session, user.id, registed.plant_id
                        )
                        plant_watering_data = get_watering_data(
                            session, current_month, registed.plant_id
                        )
                        humidity = get_humidity(registed.device_id)  # 湿度データを取得
                        # 水やり効果の判定（前回通知から湿度変化をチェック）
                        effectiveness = check_watering_effectiveness(
                            session,
                            user.id,
                            registed.plant_id,
                            humidity,
                            plant_watering_data,
                        )
                        if effectiveness:
                            logger.info(f"水やり効果判定: {effectiveness['status']}")
                            # 効果判定結果を記録
                            effectiveness_notification = models.NotificationHistory(
                                user_id=user.id,
                                plant_id=registed.plant_id,
                                notification_type="watering_feedback",
                                message=f"{registed.plant.name_jp}: {effectiveness['message']}",
                                humidity=humidity,
                            )
                            line_bot_api.push_message_with_http_info(
                                push_message_request=PushMessageRequest(
                                    to=user.id,
                                    messages=[
                                        TextMessage(
                                            text=effectiveness_notification.message
                                        ),
                                    ],
                                )
                            )
                            session.add(effectiveness_notification)
                            session.commit()

                        if (
                            latest_notification
                            and latest_notification.sent_at
                            > current_time.replace(hour=0, minute=0, second=0)
                        ):
                            logger.info(
                                f"{user.id} の植物 {registed.plant_id} は最近通知済みのためスキップ"
                            )
                            continue

                        logger.debug(
                            f"🔍 デバッグ: 検索対象のregisted.plant_id: {registed.plant_id}"
                        )

                        # 最新の水やり履歴を取得（通知履歴を使用）
                        latest_watering = get_latest_notification(
                            session, user.id, registed.plant_id
                        )

                        if check_watering_schedule(
                            plant_watering_data,
                            current_time,
                            humidity,
                            last_watering_date=(
                                latest_watering.sent_at if latest_watering else None
                            ),
                        ):
                            notification = record_notification_history(
                                session,
                                user.id,
                                registed.plant,
                                plant_watering_data,
                                humidity,
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
                for _ in range(60):
                    if stop_event.is_set():
                        logger.info("水やりチェックシステムを停止します。")
                        return
                    time.sleep(1)
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


def get_humidity(channel: int):
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 1350000  # 1.35MHz
    if not 0 <= channel <= 7:
        raise ValueError("チャンネルは0〜7を指定してください")

    # SPI通信で送る3バイト（MCP3008は10bit ADC）
    cmd = [1, (8 + channel) << 4, 0]
    response = spi.xfer2(cmd)

    # 応答（10bit）を結合してアナログ値に変換
    value = ((response[1] & 3) << 8) + response[2]
    return value


def check_watering_effectiveness(
    session: Session,
    user_id: str,
    plant_id: int,
    current_humidity: int,
    watering_data: models.Watering,
):
    """前回通知時の湿度と現在の湿度を比較して水やり効果を判定"""
    # 最新の水やり通知履歴を取得
    latest_notification = session.exec(
        select(models.NotificationHistory)
        .where(
            models.NotificationHistory.user_id == user_id,
            models.NotificationHistory.plant_id == plant_id,
        )
        .order_by(desc(models.NotificationHistory.sent_at))
    ).first()

    if latest_notification.notification_type != "watering":
        logger.info(
            f"最新の通知は水やりではありません: {latest_notification.notification_type}"
        )
        return None

    if abs(current_humidity - latest_notification.humidity) <= 100:
        # 湿度の変化が100以内なら効果なし
        logger.info("湿度の変化が100以内のため、効果なしと判定")
        return None

    if not latest_notification:
        return None  # 判定できない

    # 前回の湿度データを取得する代替手段を実装
    # 現在はシンプルに湿度のしきい値をもとに効果を判定
    target_humidity = watering_data.humidity_when_watered

    logger.info(f"現在湿度: {current_humidity}, 目標湿度: {target_humidity}")

    # 目標湿度との差を計算
    target_diff = abs(current_humidity - target_humidity)

    if target_diff <= 100:
        # ちょうど良い範囲内
        status = "ちょうど良い"
        message = "水やりの量はちょうど良いです。"
    elif current_humidity > target_humidity + 100:
        # 湿度が低い（乾燥している） = 水量が少ない
        status = "水量不足"
        message = (
            "今回は水量が少ないみたいです。次回はもう少し多めに水やりしてください。"
        )
    else:
        # 湿度が高い（湿っている） = 水量が多い
        status = "水量過多"
        message = "水量が多いみたいです。次回は少し控えめに水やりしてください。"

    logger.info(f"水やり判定: {status} - {message}")

    return {
        "status": status,
        "message": message,
        "current_humidity": current_humidity,
        "target_humidity": target_humidity,
    }


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

        if humidity >= humidity_when_dry:
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
    humidity: float = None,
):
    """通知履歴を記録する"""
    try:
        current_time = datetime.now()

        # 新しい通知履歴を作成
        new_notification = models.NotificationHistory(
            user_id=user_id,
            plant_id=plant.id,
            notification_type="watering",
            message=f"{plant.name_jp}の水やりが必要です。\n水やり頻度: {watering_data.frequency}\n水やり量: {watering_data.amount}",
            sent_at=current_time,
            humidity=humidity,
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

import re
import time
from datetime import datetime, timedelta

from linebot.v3.messaging import MessagingApi, PushMessageRequest, TextMessage
from sqlmodel import Session, select

from app import db, models


# def handler(line_bot_api: MessagingApi):
def handler():
    print("水やりチェックシステムを開始します...")

    # 1秒もしくは30分ごとに湿度を取る。
    # 登録テーブルからすべてのデータを取る。
    # register_plant()
    # show_available_models()
    # show_database_tables()
    with Session(db.engine) as session:
        # 初回実行時にデータを取得
        # user_plants = get_user_registed_plants(session, "U197b8687c1c426392c2d64b9bf2fd89f")
        watering_data = get_watering_data(session)
        users_list = get_users(session)
        last_data_update = datetime.now() - timedelta(
            hours=2
        )  # 最後のデータ更新時間を記録

        try:
            while True:
                print(
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 水やりチェックを開始します..."
                )
                current_time = datetime.now()
                current_month = current_time.month
                current_hour = current_time.hour
                # current_minute = current_time.minute
                if current_hour < 8 or current_hour > 21:
                    print(
                        f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 現在の時間は水やりチェックの時間外です。スキップします。"
                    )
                    time.sleep(600)

                time_diff = current_time - last_data_update
                if time_diff.total_seconds() >= 3600:  # 3600秒 = 1時間
                    print(
                        f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 1時間経過 - データを再取得中..."
                    )
                    watering_data = get_watering_data(session)
                    users_list = get_users(session)
                    last_data_update = current_time

                    # 月の文字列から数字を抽出して比較
                print("データ取得終了")
                watering_data_list = []
                # print(watering_data)
                print("水やりデータ:の月で絞り込みを開始します...")
                for wd in watering_data:
                    try:
                        # '1月' -> 1, '12月' -> 12 のように変換
                        month_str = wd.month.replace("月", "")
                        month_num = int(month_str)
                        if month_num == current_month:
                            watering_data_list.append(wd)
                    except (ValueError, AttributeError):
                        # 変換に失敗した場合はスキップ
                        print(f"⚠️ 月データの変換に失敗: {wd.month}")
                        continue
                # print(watering_data_list)
                print("水やりデータ:の月で絞り込みを終了します...")

                print("各ユーザの処理を開始します...")
                # print(users_list)
                for user in users_list:
                    # ユーザーの登録済み植物を取得
                    print(
                        f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] ユーザー {user.id} の水やりチェックを開始します..."
                    )
                    registed_plants = get_user_registed_plants(session, user.id)
                    notification_history = get_notification_history(session, user.id)
                    # print(f"通知履歴: {notification_history}")
                    for registed in registed_plants:
                        # 植物の判定
                        # if (直近の通知が今日ならばスキップ)
                        if (
                            notification_history
                            and notification_history.sent_at
                            > current_time.replace(hour=0, minute=0, second=0)
                        ):
                            print(
                                f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] {user.id} の植物 {registed.plant_id} は最近通知済みのためスキップ"
                            )
                            continue
                        plant_watering_data = next(
                            (
                                wd
                                for wd in watering_data_list
                                if wd.plant_id == registed.plant_id
                            ),
                            None,
                        )
                        watering_plant_ids = [wd.plant_id for wd in watering_data_list]
                        print(
                            f"🔍 デバッグ: watering_data_listのplant_id一覧: {watering_plant_ids}"
                        )
                        print(
                            f"🔍 デバッグ: 検索対象のregisted.plant_id: {registed.plant_id}"
                        )
                        humidity = get_humidity(registed.device_id)  # 湿度データを取得
                        last_watering_date = None
                        if notification_history:
                            last_watering_date = notification_history.sent_at
                        if check_watering_schedule(
                            plant_watering_data,
                            current_time,
                            humidity,
                            last_watering_date,
                        ):
                            # line bot api 挿入用の場所
                            # line_bot_api.push_message_with_http_info(
                            #     push_message_request=PushMessageRequest(
                            #         to=user.id,
                            #         messages=[
                            #             TextMessage(
                            #                 text=f"{registed.plant.name_jp} ({registed.plant.id}) の水やりが必要です。"
                            #             ),
                            #         ],
                            #     )
                            # )
                            # 通知履歴を記録
                            print("通知を記録")
                            record_notification_history(
                                session, 
                                user.id, 
                                registed.plant_id, 
                                registed.plant.name_jp, 
                                current_time
                            )

                # 1分間待機
                print(
                    f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 60秒間待機します..."
                )
                time.sleep(60)

        except KeyboardInterrupt:
            print("\n水やりチェックシステムを停止しました")
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            import traceback

            traceback.print_exc()
    pass


def get_user_registed_plants(session: Session, user_id: str):
    """特定のユーザーの登録済み植物を取得"""
    registed_plants = session.exec(
        select(models.Registed).where(models.Registed.user_id == user_id)
    ).all()

    return registed_plants


def get_users(session: Session):
    """全ユーザーを取得"""
    users = session.exec(select(models.User)).all()

    return users


def get_watering_data(session: Session):
    """水やり頻度データを取得"""
    watering_data = session.exec(select(models.Watering)).all()

    return watering_data


def get_notification_history(session: Session, user_id: str):
    """特定のユーザーの通知履歴を取得"""
    notification_history = session.exec(
        select(models.NotificationHistory).where(
            (models.NotificationHistory.user_id == user_id),
            (models.NotificationHistory.last_flg == True),
        )
    ).all()

    if notification_history:
        return notification_history[-1]  # 最新の通知履歴
    else:
        return None


def get_humidity(device_id: int):
    """湿度データを取得"""
    # ここでは湿度データの取得方法を仮定しています。
    # 実際の実装では、センサーやAPIから湿度データを取得する必要があります。
    return 50  # 仮の湿度値


def check_watering_schedule(
    watering_data, current_time, humidity=None, last_watering_date=None
):
    """水やりが必要かどうかを判定"""
    print(watering_data)
    frequency = watering_data.frequency.lower()
    print(f"Frequency: {frequency}")

    has_number = re.search(r"\d+", frequency)

    if has_number:
        # 数字がある場合：前回水をあげた日付との比較
        if last_watering_date is None:
            print("    ⚠️ 前回の水やり日付が不明です")
            return True  # 初回は水やりを推奨

        # 数字を抽出
        days_match = re.search(r"(\d+)", frequency)
        if days_match:
            target_days = int(days_match.group(1))

            # 前回の水やりからの経過日数を計算
            days_since_last_watering = (
                current_time.date() - last_watering_date.date()
            ).days

            print(
                f"    📅 前回の水やりから{days_since_last_watering}日経過（目安: {target_days}日に1回）"
            )

            if days_since_last_watering >= target_days:
                return True
            else:
                print(
                    f"    ⏳ あと{target_days - days_since_last_watering}日後に水やり予定"
                )
                return False

    else:
        # 数字がない場合：湿度比較
        humidity_when_dry = watering_data.humidity_when_dry
        if humidity is None:
            print("⚠️ 湿度データが取得できません")
            return False

        print(f"    💧 現在の湿度: {humidity}% (乾燥基準: {humidity_when_dry}%)")

        if humidity <= humidity_when_dry:
            print("    ✅ 土が乾燥しています")
            return True
        else:
            print("    🚫 まだ湿っています")
            return False

    return False

def record_notification_history(session: Session, user_id: str, plant_id: int, plant_name: str, current_time: datetime):
    """通知履歴を記録する"""
    try:
        # 既存の通知履歴のlast_flgをFalseに更新
        existing_notifications = session.exec(
            select(models.NotificationHistory).where(
                models.NotificationHistory.user_id == user_id,
                models.NotificationHistory.plant_id == plant_id,
                models.NotificationHistory.last_flg == True
            )
        ).all()
        
        for existing in existing_notifications:
            existing.last_flg = False
        
        # 新しい通知履歴を作成
        new_notification = models.NotificationHistory(
            user_id=user_id,
            plant_id=plant_id,
            notification_type="watering",
            message=f"{plant_name}の水やりが必要です",
            sent_at=current_time,
            last_flg=True
        )
        session.add(new_notification)
        session.commit()
        
        print(f"✅ 通知履歴を記録しました: {user_id} -> {plant_name} ({current_time.strftime('%Y-%m-%d %H:%M:%S')})")
        return True
        
    except Exception as notification_error:
        print(f"⚠️ 通知履歴の記録に失敗しました: {notification_error}")
        # 通知履歴の記録に失敗してもメイン処理は継続
        return False

if __name__ == "__main__":
    handler()

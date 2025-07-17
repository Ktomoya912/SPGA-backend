import sys
from pathlib import Path
from datetime import datetime, timedelta

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import Session, select  # selectを追加
from app import db, models

def create_test_users():
    """テストユーザーを作成"""
    print("テストユーザーを作成中...")
    
    with Session(db.engine) as session:
        
        # テストユーザーデータ
        test_users = [
            {
                "id": "U197b8687c1c426392c2d64b9bf2fd89f",
                "current_predict": None,
                "delete_mode": False
            },
            {
                "id": "U298c9798d2e537493d3e75c8cg3ge90g",
                "current_predict": "ポトス",
                "delete_mode": False
            },
            {
                "id": "U399d9809e3f648504e4f86d9dh4hf01h",
                "current_predict": "モンステラ",
                "delete_mode": False
            },
            {
                "id": "U400e0910f4g759605f5g97e0ei5ig02i",
                "current_predict": None,
                "delete_mode": False
            },
            {
                "id": "U501f1021g5h860716g6h08f1fj6jh03j",
                "current_predict": "パキラ",
                "delete_mode": False
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for user_data in test_users:
            # 既存ユーザーをチェック
            existing_user = session.get(models.User, user_data["id"])
            
            if existing_user:
                # 既存ユーザーを更新
                existing_user.current_predict = user_data["current_predict"]
                existing_user.delete_mode = user_data["delete_mode"]
                updated_count += 1
                print(f"  更新: {user_data['id']} (予測: {user_data['current_predict']})")
            else:
                # 新しいユーザーを作成
                user = models.User(**user_data)
                session.add(user)
                created_count += 1
                print(f"  作成: {user_data['id']} (予測: {user_data['current_predict']})")
        
        session.commit()
        
        print(f"\n✅ ユーザー処理完了:")
        print(f"   新規作成: {created_count}件")
        print(f"   更新: {updated_count}件")
        
        # 作成されたユーザーを確認
        all_users = session.exec(select(models.User)).all()
        print(f"\n📊 データベース内のユーザー数: {len(all_users)}件")
        
        return all_users

def create_devices_for_users():
    """各ユーザーにデバイスを作成（特定の植物に紐づける）"""
    print("\nデバイスを作成中...")
    
    with Session(db.engine) as session:
        users = session.exec(select(models.User)).all()
        plants = session.exec(select(models.Plant)).all()
        
        if not plants:
            print("⚠️ 植物データが存在しません。先にマイグレーションを実行してください。")
            return
        
        device_locations = [
            "リビング", "ベランダ", "書斎", "キッチン", "寝室", 
            "廊下", "玄関", "バスルーム", "屋上", "庭"
        ]
        
        created_count = 0
        
        for i, user in enumerate(users):
            location = device_locations[i % len(device_locations)]
            # ユーザーに植物を割り当て（循環的に）
            assigned_plant = plants[i % len(plants)]
            
            # 既存デバイスをチェック
            existing_device = session.exec(
                select(models.Device).where(models.Device.user_id == user.id)
            ).first()
            
            if not existing_device:
                device = models.Device(
                    name=f"{location}湿度センサー",
                    user_id=user.id,
                    plant_id=assigned_plant.id  # plant_idを必須として追加
                )
                session.add(device)
                created_count += 1
                print(f"  作成: {user.id} -> {device.name} (植物: {assigned_plant.name_jp})")
        
        session.commit()
        print(f"✅ デバイス作成完了: {created_count}件")


def create_plant_registrations():
    """ユーザーと植物の登録関係を作成"""
    print("\n植物登録を作成中...")
    
    with Session(db.engine) as session:
        users = session.exec(select(models.User)).all()
        plants = session.exec(select(models.Plant)).all()
        
        if not plants:
            print("⚠️ 植物データが存在しません。先にマイグレーションを実行してください。")
            return
        
        created_count = 0
        
        for i, user in enumerate(users):
            # 各ユーザーに1-2個の植物を登録
            start_idx = i % len(plants)
            end_idx = min(start_idx + 2, len(plants))
            user_plants = plants[start_idx:end_idx]
            
            # 最低1つは登録
            if len(user_plants) == 0:
                user_plants = [plants[0]]
            
            # ユーザーのデバイスを取得
            user_device = session.exec(
                select(models.Device).where(models.Device.user_id == user.id)
            ).first()
            
            if not user_device:
                print(f"⚠️ ユーザー {user.id} のデバイスが見つかりません")
                continue
            
            for plant in user_plants:
                # 既存の登録をチェック
                existing_reg = session.exec(
                    select(models.Registed).where(
                        models.Registed.user_id == user.id,
                        models.Registed.plant_id == plant.id
                    )
                ).first()
                
                if not existing_reg:
                    registration = models.Registed(
                        user_id=user.id,
                        plant_id=plant.id,
                        device_id=user_device.id
                    )
                    session.add(registration)
                    created_count += 1
                    print(f"  登録: {user.id} -> {plant.name_jp} (デバイス: {user_device.id})")
        
        session.commit()
        print(f"✅ 植物登録完了: {created_count}件")

def create_notification_history():
    """通知履歴を作成"""
    print("\n通知履歴を作成中...")
    
    with Session(db.engine) as session:
        registrations = session.exec(select(models.Registed)).all()
        
        created_count = 0
        
        for reg in registrations:
            plant = session.get(models.Plant, reg.plant_id)
            
            # 過去の通知履歴を作成（複数の履歴）
            notification_dates = [
                datetime.now() - timedelta(days=7),
                datetime.now() - timedelta(days=4),
                datetime.now() - timedelta(days=1),
            ]
            
            for i, sent_date in enumerate(notification_dates):
                notification = models.NotificationHistory(
                    user_id=reg.user_id,
                    plant_id=reg.plant_id,
                    notification_type="watering",
                    message=f"{plant.name_jp}に水やりが必要です",
                    sent_at=sent_date,
                )
                session.add(notification)
                created_count += 1
                
                if i == len(notification_dates) - 1:  # 最新のもの
                    print(f"  通知履歴: {reg.user_id} -> {plant.name_jp} (最新: {sent_date.strftime('%Y-%m-%d %H:%M')})")
        
        session.commit()
        print(f"✅ 通知履歴作成完了: {created_count}件")

def show_all_test_data():
    """作成されたテストデータを表示"""
    print("\n=== 作成されたテストデータ ===")
    
    with Session(db.engine) as session:
        # ユーザー情報
        users = session.exec(select(models.User)).all()
        print(f"\n👥 ユーザー数: {len(users)}")
        for user in users:
            print(f"  {user.id}: {user.name}")
            
            # 植物登録情報
            registrations = session.exec(
                select(models.Registed).where(models.Registed.user_id == user.id)
            ).all()
            
            for reg in registrations:
                plant = session.get(models.Plant, reg.plant_id)
                print(f"    📱 デバイス{reg.device_id} -> 🌱 {plant.name_jp} (ID: {plant.id})")
                
                # 最新の通知履歴
                latest_notification = session.exec(
                    select(models.NotificationHistory).where(
                        models.NotificationHistory.user_id == user.id,
                        models.NotificationHistory.plant_id == plant.id
                    ).order_by(models.NotificationHistory.sent_at.desc())
                ).first()
                
                if latest_notification:
                    print(f"      📬 最新通知: {latest_notification.sent_at.strftime('%Y-%m-%d %H:%M')} - {latest_notification.message}")
                
                # 水やりデータ
                watering_data = session.exec(
                    select(models.Watering).where(
                        models.Watering.plant_id == plant.id,
                        models.Watering.month == str(datetime.now().month)
                    )
                ).first()
                
                if watering_data:
                    print(f"      💧 水やり頻度: {watering_data.frequency} (湿度基準: {watering_data.humidity_when_dry}%)")

def show_summary():
    """データの統計情報を表示"""
    print("\n=== データ統計 ===")
    
    with Session(db.engine) as session:
        users_count = len(session.exec(select(models.User)).all())
        plants_count = len(session.exec(select(models.Plant)).all())
        devices_count = len(session.exec(select(models.Device)).all())
        registrations_count = len(session.exec(select(models.Registed)).all())
        notifications_count = len(session.exec(select(models.NotificationHistory)).all())
        waterings_count = len(session.exec(select(models.Watering)).all())
        
        print(f"📊 データベース統計:")
        print(f"   👤 ユーザー: {users_count}件")
        print(f"   🌱 植物: {plants_count}件")
        print(f"   📱 デバイス: {devices_count}件")
        print(f"   📝 登録: {registrations_count}件")
        print(f"   📬 通知履歴: {notifications_count}件")
        print(f"   💧 水やりデータ: {waterings_count}件")

if __name__ == "__main__":
    try:
        print("🚀 テストデータ作成を開始...")
        
        # 1. ユーザー作成
        users = create_test_users()
        
        # 2. デバイス作成（plant_id必須）
        create_devices_for_users()
        
        # 3. 植物登録作成
        create_plant_registrations()
        
        # 4. 通知履歴作成
        create_notification_history()
        
        # 5. 作成データ表示
        show_all_test_data()
        
        # 6. 統計情報表示
        show_summary()
        
        print("\n🎉 テストデータ作成完了!")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
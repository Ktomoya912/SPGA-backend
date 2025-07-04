from sqlmodel import Session, select

from app import models


def get_create_user(db: Session, user_id: str):
    user = db.exec(select(models.User).where(models.User.id == user_id)).first()
    if user is None:
        new_user = models.User(id=user_id)
        db.add(new_user)
        db.commit()
        return new_user
    else:
        return user


def plant_regist(db: Session, plant_id: int, user_id: int, device_id: int = 0):
    registed = db.exec(
        select(models.Registed).where(
            models.Registed.plant_id == plant_id,
            models.Registed.device_id == device_id,
            models.Registed.user_id == user_id,
        )
    ).first()
    if registed is None:
        new_registed = models.Registed(
            plant_id=plant_id, device_id=device_id, user_id=user_id
        )
        db.add(new_registed)
        db.commit()
        return True
    else:
        return False

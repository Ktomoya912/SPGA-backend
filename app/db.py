from datetime import datetime

from dotenv import load_dotenv
from sqlmodel import Field, Session, SQLModel, create_engine

load_dotenv()

DB_URL = "sqlite:///./app.db"

engine = create_engine(DB_URL, echo=False)


class BaseModel(SQLModel):
    __abstract__ = True

    created_at: datetime = Field(
        default_factory=datetime.now,
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column_kwargs={"onupdate": datetime.now},
    )


def get_db():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Ссылка на мою БД в Neon
SQLALCHEMY_DATABASE_URL = "postgresql://neondb_owner:npg_GTDqA4ztIcl3@ep-odd-field-b4we7phh-pooler.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Создаем движок
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для наших моделей
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
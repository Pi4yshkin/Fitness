from database import Base  # Импортируем Base из нашего database.py
from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # 👇 Связи с другими таблицами (у одного пользователя много дней и подходов)
    days = relationship("TrainingDay", back_populates="owner", cascade="all, delete-orphan")
    workouts = relationship("Workout", back_populates="owner", cascade="all, delete-orphan")


class TrainingDay(Base):
    __tablename__ = "training_days"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # Привязка к пользователю
    day_id = Column(String)  # Внутренний id 
    name = Column(String)  # Название тренировочного дня

    # Упражнения храним как строку (JSON), так как это список строк. 
    # Это проще, чем создавать отдельную таблицу для упражнений дня.
    exercises_json = Column(Text, default="[]")

    owner = relationship("User", back_populates="days")


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # Призяка к пользователю
    workout_id = Column(String)  # UUID из Flet (что бы не дублировать записи)
    day_id = Column(String)
    exercise = Column(String)
    weight = Column(String)
    reps = Column(String)
    comment = Column(String, nullable=True)
    date = Column(String)
    timestamp = Column(String)

    owner = relationship("User", back_populates="workouts")

    
from datetime import datetime, timedelta
from typing import Optional

import models
from database import engine, get_db

# Depends механизм внедрения зависимостей (например, что бы получить текущего пользователя)
from fastapi import Depends, FastAPI, HTTPException, status

# OAuth2PasswordBearer - класс, который извлекает токен из заголовка Authorization
# OAuth2PasswordRequestForm - стандартная форма для логина (usernamr + password)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# JWTError - ошибка при декодировании токена
# jwt - библиотека для создания и проверки JWT-токенов
from jose import JWTError, jwt

# CryptContext - менеджер для хеширования паролей (bcrypt)
from passlib.context import CryptContext

# BaseModel из Pydantic используется для валидации входящих данных (схем)
from pydantic import BaseModel
from sqlalchemy.orm import Session

# SECRET_KEY это "соль", которой подписываются токены
# НАДО БУДЕТ ПЕРЕНЕСТИ В .env
SECRET_KEY = "super-secret-key-change-me-later"

# ALGORITHM - алгоритм шифровавания подписи (HS256 - стандарт JWT)
ALGORITHM = "HS256"

# Сколько будет жить токен в минутах
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

# CryptContext говорит: используй bcrypt для хеширования, а старые схемы помечай как устаревшие
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer — это "охранник"
# Когда пользователь делает запрос к защищенному эндпоинту, 
# этот класс проверяет заголовок Authorization и достает оттуда токен.
# tokenUrl="token" — указывает, куда идти за токеном (это наш эндпоинт /token).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Создаем экземпляр приложения FastAPI
app = FastAPI()

# 👇 ВАЖНО: Эта команда создает таблицы в базе данных, если их еще нет.
# Она берет описание из models.py и применяет к базе из database.py.
models.Base.metadata.create_all(bind=engine)


# Pydantic-модель для регистрации. 
# Она проверяет, что пришел JSON с полями username и password (оба строки).
class UserCreate(BaseModel):
    username: str
    password: str

# Pydantic-модель для ответа при логине.
# Сервер вернет JSON: {"access_token": "...", "token_type": "bearer"}
class Token(BaseModel):
    access_token: str
    token_type: str


def verify_password(plain_password, hashed_password):
    """
    Проверяет, совпадает ли введенный пароль с хешем из базы.
    bcrypt сам "разворачивает" хеш и сравнивает. Мы никогда не храним пароль в открытом виде!
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """
    Превращает пароль в нечитаемый хеш (например, "password123" -> "$2b$12$...").
    Этот хеш и будет храниться в базе.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Создает JWT-токен.
    data — это полезная нагрузка (payload), например {"sub": "username"}.
    sub (subject) — стандартное поле JWT, означающее "для кого этот токен".
    expires_delta — время жизни токена (если None, то по умолчанию 15 минут).
    """
    to_encode = data.copy()  # делаем копию, что бы не менять оригинал 

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    # Добавляем поле "exp" (expiration) — это стандартное поле JWT.
    to_encode.update({"exp": expire})

    # Кодируем данные в токен с помощью секретного ключа и алгоритма.
    # Получается длинная строка вида "eyJhbGciOiJIUzI1NiIs...".
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация. Теперь мы ищем пользователя в базе данных.
    """
    # Ищем пользователя в таблице users
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        # Если занят — возвращаем ошибку 400 Bad Request.
        raise HTTPException(status_code=400, detail="Такой пользователь уже зарегистрирован")
    
    # Хешируем пароль (никогда не сохраняем его в открытом виде!).
    hashed_password = get_password_hash(user.password)

    # Сохраняем пользователя в базу данных
    new_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()  # Фиксируем изменения в базе
    db.refresh(new_user)  # Обновляем объект (что бы получит id)

    # Возвращаем сообщение об успехе.
    return {"message": "Пользователь зарегистрирован"}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Логин. Ищем пользователя в базе и проверяем пароль.
    """
    # Ищем пользователя в базе.
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    # Если пользователя нет или пароль неверный — возвращаем 401 Unauthorized.
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Неверное имя или пароль",
                            # Заголовок WWW-Authenticate говорит клиенту, какой тип авторизации использовать.
                            headers={"WWW-Authenticate": "Bearer"},
                            )
    # Создаем токен. В поле "sub" (subject) кладем имя пользователя.
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    # Возвращаем токен клиенту.
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me")
async def read_users_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Защищенный эндпоинт. Проверяем токен и достаем пользователя из базы.
    """
    # Готовим ошибку на случай проблем с токеном.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Декодируем токен (проверяем подпись и срок действия).
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Достаем из токена имя пользователя (поле "sub").
        username: str = payload.get("sub")

        # Если имени нет — токен невалидный.
        if username is None:
            raise credentials_exception
    except JWTError:
         # Если токен просрочен или подпись неверна — возвращаем ошибку.
         raise credentials_exception

    # Проверяем, что такой пользователь действительно существует.
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception

    # Возвращаем данные пользователя.
    return {"username": user.username}
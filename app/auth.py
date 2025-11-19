"""
Модуль аутентификации и авторизации для Habit Tracker API
Реализует JWT-аутентификацию согласно требованиям безопасности
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import AUTH_JWT_ALGORITHM, AUTH_JWT_EXPIRATION_MINUTES
from app.database import get_db
from app.models import User

# Настройка хеширования паролей (используем Argon2 - более современный и безопасный)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2 схема для получения токена из заголовка Authorization
# auto_error=False делает токен опциональным
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

# Получение секретного ключа из переменной окружения или из конфига
_DEFAULT_KEY = "REPLACE_WITH_SECURE_RANDOM_KEY"
SECRET_KEY = os.getenv("AUTH_JWT_SECRET_KEY", _DEFAULT_KEY)
if SECRET_KEY == _DEFAULT_KEY:  # noqa: S105
    import secrets

    SECRET_KEY = secrets.token_urlsafe(32)
    print("⚠️  WARNING: Using generated secret key. Set AUTH_JWT_SECRET_KEY in production!")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Хеширование пароля"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание JWT токена

    Args:
        data: Данные для включения в токен
        expires_delta: Время жизни токена

    Returns:
        JWT токен
    """
    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=AUTH_JWT_EXPIRATION_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=AUTH_JWT_ALGORITHM)

    return encoded_jwt


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Получить пользователя по username"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Получить пользователя по ID"""
    return db.query(User).filter(User.id == user_id).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Аутентификация пользователя

    Args:
        db: Сессия базы данных
        username: Имя пользователя
        password: Пароль

    Returns:
        User object если аутентификация успешна, иначе None
    """
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(db: Session, username: str, password: str) -> User:
    """
    Создание нового пользователя

    Args:
        db: Сессия базы данных
        username: Имя пользователя
        password: Пароль

    Returns:
        Созданный User object
    """
    hashed_password = get_password_hash(password)
    db_user = User(username=username, hashed_password=hashed_password, is_active=True)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


async def get_current_user(
    db: Session = Depends(get_db),  # noqa: B008
    token: Optional[str] = Depends(oauth2_scheme),  # noqa: B008
) -> Optional[User]:
    """
    Dependency для получения текущего пользователя из JWT токена

    Args:
        db: Сессия базы данных
        token: JWT токен из заголовка Authorization (опциональный)

    Returns:
        User object текущего пользователя или None если аутентификация отключена

    Raises:
        HTTPException: Если токен невалиден или пользователь не найден
    """
    # Если аутентификация отключена или токен не предоставлен, возвращаем None
    from app.config import AUTH_ENABLED

    if not AUTH_ENABLED or token is None:
        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[AUTH_JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception from e

    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return user


async def get_current_active_user(
    current_user: Optional[User] = Depends(get_current_user),  # noqa: B008
) -> Optional[User]:
    """
    Dependency для получения активного пользователя

    Args:
        current_user: Текущий пользователь (может быть None если AUTH_ENABLED=False)

    Returns:
        User object если пользователь активен, или None если аутентификация отключена

    Raises:
        HTTPException: Если пользователь неактивен
    """
    # Если аутентификация отключена, возвращаем пустого пользователя
    from app.config import AUTH_ENABLED

    if not AUTH_ENABLED:
        return None

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user

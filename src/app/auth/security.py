from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.deps import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def validate_password_strength(password: str) -> None:
    """
    Validate password security requirements.

    Requirements:
    - 8 to 128 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - No whitespace
    """
    if not isinstance(password, str):
        raise ValueError("Password must be a string")

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    if len(password) > 128:
        raise ValueError("Password must not exceed 128 characters")

    if any(char.isspace() for char in password):
        raise ValueError("Password must not contain whitespace")

    if not any(char.isupper() for char in password):
        raise ValueError("Password must contain at least one uppercase letter")

    if not any(char.islower() for char in password):
        raise ValueError("Password must contain at least one lowercase letter")

    if not any(char.isdigit() for char in password):
        raise ValueError("Password must contain at least one digit")

    if not any(not char.isalnum() for char in password):
        raise ValueError("Password must contain at least one special character")
    
def hash_password(password: str) -> str:
    validate_password_strength(password)
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    payload = data.copy()
    now = datetime.now(timezone.utc)

    payload["typ"] = "access"
    payload["iat"] = now
    payload["exp"] = now + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        if payload.get("typ") != "access":
            raise credentials_exception

        email = payload.get("sub")

        if not email or not isinstance(email, str):
            raise credentials_exception

    except JWTError as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(User.email == email).first()

    if user is None:
        raise credentials_exception

    return user
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.crud.user import create_user, get_users
from app.database.deps import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == str(user.email).lower()).first():
        raise HTTPException(status_code=409, detail="Email is already registered")
    if db.query(User).filter(User.username == user.username.strip()).first():
        raise HTTPException(status_code=409, detail="Username is already registered")
    try:
        return create_user(db, user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username or email is already registered") from exc


@router.get("/", response_model=list[UserResponse])
def read_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return get_users(db)

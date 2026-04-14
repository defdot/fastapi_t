"""用户路由 - CRUD + 获取当前用户信息"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.models.user import User
from app.schemas.schemas import UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user


@router.get("/", response_model=list[UserOut])
def list_users(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """获取用户列表（分页）"""
    return db.query(User).offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserOut)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """获取单个用户"""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.put("/me", response_model=UserOut)
def update_current_user(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前用户信息"""
    if user_in.email is not None:
        current_user.email = user_in.email
    if user_in.password is not None:
        current_user.hashed_password = hash_password(user_in.password)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除当前用户"""
    db.delete(current_user)
    db.commit()

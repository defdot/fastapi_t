"""Item 路由 - 完整 CRUD，需要认证"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.item import Item
from app.models.user import User
from app.schemas.schemas import ItemCreate, ItemOut, ItemUpdate

router = APIRouter(prefix="/api/items", tags=["Item"])


@router.post("/", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(item_in: ItemCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """创建 Item"""
    item = Item(**item_in.model_dump(), owner_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/", response_model=list[ItemOut])
def list_items(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """获取 Item 列表（分页）"""
    return db.query(Item).offset(skip).limit(limit).all()


@router.get("/me", response_model=list[ItemOut])
def list_my_items(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的 Item 列表"""
    return db.query(Item).filter(Item.owner_id == current_user.id).offset(skip).limit(limit).all()


@router.get("/{item_id}", response_model=ItemOut)
def read_item(item_id: int, db: Session = Depends(get_db)):
    """获取单个 Item"""
    item = db.query(Item).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item 不存在")
    return item


@router.put("/{item_id}", response_model=ItemOut)
def update_item(
    item_id: int,
    item_in: ItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新 Item（仅所有者可操作）"""
    item = db.query(Item).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item 不存在")
    if item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此 Item")

    update_data = item_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除 Item（仅所有者可操作）"""
    item = db.query(Item).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item 不存在")
    if item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此 Item")

    db.delete(item)
    db.commit()

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Category, Product
from app.schemas import (
    CategoryOut,
    ProductListOut,
    ProductOut,
    ProductSort,
)

router = APIRouter(prefix="/api", tags=["shop"])

DbSession = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# Категории и бренды
# ---------------------------------------------------------------------------


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: DbSession):
    """Все категории (для главной, фильтров и меню)."""
    return db.scalars(select(Category).order_by(Category.id)).all()


@router.get("/brands", response_model=list[str])
def list_brands(db: DbSession):
    """Список производителей для фильтра в каталоге."""
    stmt = select(Product.brand).where(Product.brand != "").distinct().order_by(Product.brand)
    return db.scalars(stmt).all()


# ---------------------------------------------------------------------------
# Каталог
# ---------------------------------------------------------------------------


def catalog_order_by(sort: ProductSort):
    """
    КРИТИЧЕСКОЕ ПРАВИЛО: товары в наличии (in_stock = True) всегда идут первыми,
    а «под заказ» (in_stock = False) уходят в конец списка. Выбранная пользователем
    сортировка применяется уже внутри этих двух групп.
    """
    secondary = {
        ProductSort.DEFAULT: Product.created_at.desc(),  # новинки выше
        ProductSort.PRICE_ASC: Product.price.asc(),
        ProductSort.PRICE_DESC: Product.price.desc(),
    }[sort]
    return (Product.in_stock.desc(), secondary, Product.id.desc())


@router.get("/products", response_model=ProductListOut)
def list_products(
    db: DbSession,
    category: Annotated[
        list[str] | None, Query(description="Slug категории. Можно передать несколько.")
    ] = None,
    brand: Annotated[list[str] | None, Query(description="Бренд. Можно несколько.")] = None,
    min_price: Annotated[int | None, Query(ge=0)] = None,
    max_price: Annotated[int | None, Query(ge=0)] = None,
    in_stock_only: bool = False,
    q: Annotated[str | None, Query(max_length=100, description="Поиск по названию, описанию, бренду")] = None,
    sort: ProductSort = ProductSort.DEFAULT,
    limit: Annotated[int, Query(ge=1, le=100)] = 12,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """
    Каталог товаров. Используется и на главной (`?limit=4` — «Новые поступления»),
    и в каталоге (фильтры, сортировка, «Показать ещё» через `offset`).
    """
    conditions = []

    if category:
        conditions.append(
            Product.category_id.in_(select(Category.id).where(Category.slug.in_(category)))
        )
    if brand:
        conditions.append(Product.brand.in_(brand))
    if min_price is not None:
        conditions.append(Product.price >= min_price)
    if max_price is not None:
        conditions.append(Product.price <= max_price)
    if in_stock_only:
        conditions.append(Product.in_stock.is_(True))
    if q and q.strip():
        term = q.strip().lower()
        conditions.append(
            or_(
                func.lower(Product.name).contains(term, autoescape=True),
                func.lower(Product.description).contains(term, autoescape=True),
                func.lower(Product.brand).contains(term, autoescape=True),
            )
        )

    total = db.scalar(select(func.count()).select_from(Product).where(*conditions)) or 0

    products = db.scalars(
        select(Product)
        .options(joinedload(Product.category))
        .where(*conditions)
        .order_by(*catalog_order_by(sort))
        .limit(limit)
        .offset(offset)
    ).all()

    return ProductListOut(
        items=[ProductOut.model_validate(p) for p in products],
        total=total,
    )


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: DbSession):
    product = db.scalar(
        select(Product).options(joinedload(Product.category)).where(Product.id == product_id)
    )
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")
    return product

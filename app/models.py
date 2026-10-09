from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    # Класс иконки FontAwesome, например "fa-guitar"
    icon: Mapped[str] = mapped_column(String(50), default="fa-music")
    # URL или путь вида "/static/uploads/xxx.jpg"
    image: Mapped[str | None] = mapped_column(String(500), default=None)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    # Цена в целых рублях (во фронтенде цены целые)
    price: Mapped[int] = mapped_column(Integer)
    image: Mapped[str | None] = mapped_column(String(500), default=None)
    # RESTRICT: нельзя удалить категорию, пока в ней есть товары
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    brand: Mapped[str] = mapped_column(String(100), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    specs: Mapped[str] = mapped_column(Text, default="")
    # True — в наличии, False — под заказ / нет в наличии
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    category: Mapped["Category"] = relationship(back_populates="products")

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OrderStatus(str, enum.Enum):
    NEW = "Новый"
    IN_PROGRESS = "В обработке"
    DONE = "Завершен"
    CANCELLED = "Отменен"


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


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(100))
    customer_phone: Mapped[str] = mapped_column(String(30))
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            native_enum=False,
            length=20,
            # В БД хранятся русские значения ("Новый"), а не имена членов enum
            values_callable=lambda e: [m.value for m in e],
        ),
        default=OrderStatus.NEW,
        index=True,
    )
    total_price: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.id",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    # SET NULL: если товар удалят из каталога, история заказа сохранится
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), default=None
    )
    # Снимок названия на момент заказа (нужен, если товар потом удалят/переименуют)
    product_name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(Integer)
    # Цена за 1 шт. на момент заказа (позже цена товара может измениться)
    price: Mapped[int] = mapped_column(Integer)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product | None"] = relationship()

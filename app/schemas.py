import re
from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
    field_validator,
)

from app.models import OrderStatus

# ---------------------------------------------------------------------------
# Общие типы
# ---------------------------------------------------------------------------

# Строка без пробелов по краям
Str = Annotated[str, StringConstraints(strip_whitespace=True)]

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ICON_RE = re.compile(r"^fa-[a-z0-9-]+$")


def _check_image(value: str | None) -> str | None:
    """Картинка: пусто, внешний URL или путь к загруженному файлу."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not (value.startswith(("http://", "https://", "/static/"))):
        raise ValueError("Ссылка на изображение должна начинаться с http(s):// или /static/")
    return value


class ORMModel(BaseModel):
    """Базовая схема для ответов: читает данные прямо из SQLAlchemy-объектов."""

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Категории
# ---------------------------------------------------------------------------


class CategoryBase(BaseModel):
    name: Annotated[Str, Field(min_length=2, max_length=100)]
    # Если slug не передан, админка сгенерирует его из названия
    slug: Annotated[Str, Field(max_length=120)] | None = None
    icon: Annotated[Str, Field(max_length=50)] = "fa-music"
    image: str | None = None

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: str | None) -> str | None:
        if not v:
            return None
        v = v.lower()
        if not SLUG_RE.match(v):
            raise ValueError("Slug: только латиница, цифры и дефисы (например, saxophones)")
        return v

    @field_validator("icon")
    @classmethod
    def _icon(cls, v: str) -> str:
        if not ICON_RE.match(v):
            raise ValueError("Иконка FontAwesome должна выглядеть как fa-guitar")
        return v

    @field_validator("image")
    @classmethod
    def _image(cls, v: str | None) -> str | None:
        return _check_image(v)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class CategoryOut(ORMModel):
    id: int
    name: str
    slug: str
    icon: str
    image: str | None = None


# ---------------------------------------------------------------------------
# Товары
# ---------------------------------------------------------------------------


class ProductSort(str, Enum):
    """Сортировка каталога. Товары в наличии ВСЕГДА идут первыми, это вторичный ключ."""

    DEFAULT = "default"
    PRICE_ASC = "price-asc"
    PRICE_DESC = "price-desc"


class ProductBase(BaseModel):
    name: Annotated[Str, Field(min_length=2, max_length=200)]
    price: Annotated[int, Field(ge=0, le=100_000_000)]
    category_id: int
    brand: Annotated[Str, Field(max_length=100)] = ""
    description: Str = ""
    specs: Str = ""
    in_stock: bool = True
    # Ссылка на картинку. Загруженный файл админка сохранит и подставит путь сама
    image: str | None = None

    @field_validator("image")
    @classmethod
    def _image(cls, v: str | None) -> str | None:
        return _check_image(v)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    pass


class ProductOut(ORMModel):
    id: int
    name: str
    price: int
    image: str | None = None
    brand: str
    description: str
    specs: str
    in_stock: bool
    category: CategoryOut


class ProductListOut(BaseModel):
    """Страница каталога: товары + общее число (для кнопки «Показать ещё»)."""

    items: list[ProductOut]
    total: int


class StockUpdate(BaseModel):
    """Быстрое переключение наличия."""

    in_stock: bool


# ---------------------------------------------------------------------------
# Заказы
# ---------------------------------------------------------------------------


def normalize_phone(raw: str) -> str:
    """
    Приводит телефон к виду +7XXXXXXXXXX (для российских номеров)
    или +<цифры> (для международных).

    "8 (949) 710-62-63" -> "+79497106263"
    "949 710 62 63"     -> "+79497106263"
    "+380 50 123 45 67" -> "+380501234567"
    """
    raw = raw.strip()
    if not re.fullmatch(r"\+?[\d\s()\-.]+", raw):
        raise ValueError("Телефон может содержать только цифры, пробелы, скобки, дефис и +")

    digits = re.sub(r"\D", "", raw)

    if raw.startswith("+"):
        if not 10 <= len(digits) <= 15:
            raise ValueError("Некорректная длина номера телефона")
        return "+" + digits

    if len(digits) == 11 and digits[0] in "78":
        return "+7" + digits[1:]
    if len(digits) == 10:
        return "+7" + digits
    raise ValueError("Введите номер полностью, например +7 949 123-45-67")


class OrderItemIn(BaseModel):
    """Позиция корзины. Цену клиент НЕ передаёт: сервер берёт её из БД."""

    product_id: int
    quantity: Annotated[int, Field(ge=1, le=99)]


class OrderCreate(BaseModel):
    customer_name: Annotated[Str, Field(min_length=2, max_length=100)]
    customer_phone: str
    items: Annotated[list[OrderItemIn], Field(min_length=1, max_length=50)]

    @field_validator("customer_phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalize_phone(v)

    @field_validator("items")
    @classmethod
    def _merge_duplicates(cls, items: list[OrderItemIn]) -> list[OrderItemIn]:
        """Один и тот же товар дважды в списке -> одна позиция с суммой количества."""
        merged: dict[int, int] = {}
        for it in items:
            merged[it.product_id] = merged.get(it.product_id, 0) + it.quantity
        if any(q > 99 for q in merged.values()):
            raise ValueError("Не более 99 штук одного товара")
        return [OrderItemIn(product_id=pid, quantity=q) for pid, q in merged.items()]


class OrderCreated(ORMModel):
    """Ответ на POST /api/orders."""

    id: int
    total_price: int
    status: OrderStatus


class OrderItemOut(ORMModel):
    product_id: int | None
    product_name: str
    quantity: int
    price: int

    @computed_field
    @property
    def line_total(self) -> int:
        return self.price * self.quantity


class OrderOut(ORMModel):
    id: int
    customer_name: str
    customer_phone: str
    status: OrderStatus
    total_price: int
    created_at: datetime
    items: list[OrderItemOut]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus

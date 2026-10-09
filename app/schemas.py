import re
from enum import Enum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)


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

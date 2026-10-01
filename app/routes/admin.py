import re
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.deps import csrf_token, require_admin, verify_csrf
from app.models import Category, Order, OrderStatus, Product
from app.services.uploads import save_image

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates" / "admin"))

DbSession = Depends(get_db)


def slugify(value: str) -> str:
    table = str.maketrans({
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "j", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "",
        "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    })
    text = value.strip().lower().translate(table)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:120] or "category"


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("is_admin") is True:
        return redirect("/admin")
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None, "csrf_token": csrf_token(request)},
    )


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    password: str = Form(...),
    token: str | None = Form(None),
):
    verify_csrf(request, token)
    if secrets.compare_digest(password, settings.admin_password):
        request.session["is_admin"] = True
        return redirect("/admin")
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "Неверный пароль", "csrf_token": csrf_token(request)},
        status_code=401,
    )


@router.post("/logout")
def logout(request: Request, token: str | None = Form(None)):
    verify_csrf(request, token)
    request.session.clear()
    return redirect("/admin/login")


@router.get("", response_class=HTMLResponse)
def admin_home(request: Request, _=Depends(require_admin)):
    return redirect("/admin/products")


@router.get("/categories", response_class=HTMLResponse)
def categories_page(request: Request, db: Session = DbSession, _=Depends(require_admin)):
    categories = db.scalars(select(Category).order_by(Category.id)).all()
    return templates.TemplateResponse(
        request=request,
        name="categories.html",
        context={"categories": categories, "csrf_token": csrf_token(request)},
    )


@router.post("/categories/create")
def create_category(
    request: Request,
    name: str = Form(...),
    slug: str | None = Form(None),
    icon: str = Form("fa-music"),
    image: UploadFile | None = None,
    token: str | None = Form(None),
    db: Session = DbSession,
    _=Depends(require_admin),
):
    verify_csrf(request, token)
    final_slug = (slug or slugify(name)).strip().lower()
    category = Category(name=name.strip(), slug=final_slug, icon=icon.strip() or "fa-music")
    saved = save_image(image, subdir="categories")
    if saved:
        category.image = saved
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return redirect("/admin/categories?error=duplicate")
    return redirect("/admin/categories")


@router.post("/categories/{category_id}/update")
def update_category(
    category_id: int,
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    icon: str = Form("fa-music"),
    image: UploadFile | None = None,
    token: str | None = Form(None),
    db: Session = DbSession,
    _=Depends(require_admin),
):
    verify_csrf(request, token)
    category = db.get(Category, category_id)
    if category is None:
        return redirect("/admin/categories")
    category.name = name.strip()
    category.slug = slug.strip().lower()
    category.icon = icon.strip() or "fa-music"
    saved = save_image(image, subdir="categories")
    if saved:
        category.image = saved
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return redirect("/admin/categories?error=duplicate")
    return redirect("/admin/categories")


@router.post("/categories/{category_id}/delete")
def delete_category(
    category_id: int,
    request: Request,
    token: str | None = Form(None),
    db: Session = DbSession,
    _=Depends(require_admin),
):
    verify_csrf(request, token)
    category = db.get(Category, category_id)
    if category is None:
        return redirect("/admin/categories")
    if db.scalar(select(Product.id).where(Product.category_id == category_id).limit(1)):
        return redirect("/admin/categories?error=has_products")
    db.delete(category)
    db.commit()
    return redirect("/admin/categories")


@router.get("/products", response_class=HTMLResponse)
def products_page(request: Request, db: Session = DbSession, _=Depends(require_admin)):
    products = db.scalars(
        select(Product).options(joinedload(Product.category)).order_by(Product.created_at.desc(), Product.id.desc())
    ).all()
    categories = db.scalars(select(Category).order_by(Category.name)).all()
    return templates.TemplateResponse(
        request=request,
        name="products.html",
        context={"products": products, "categories": categories, "csrf_token": csrf_token(request)},
    )


@router.get("/products/new", response_class=HTMLResponse)
def product_new(request: Request, db: Session = DbSession, _=Depends(require_admin)):
    categories = db.scalars(select(Category).order_by(Category.name)).all()
    return templates.TemplateResponse(
        request=request,
        name="product_form.html",
        context={"product": None, "categories": categories, "csrf_token": csrf_token(request)},
    )


@router.get("/products/{product_id}/edit", response_class=HTMLResponse)
def product_edit(product_id: int, request: Request, db: Session = DbSession, _=Depends(require_admin)):
    product = db.scalar(select(Product).where(Product.id == product_id))
    if product is None:
        return redirect("/admin/products")
    categories = db.scalars(select(Category).order_by(Category.name)).all()
    return templates.TemplateResponse(
        request=request,
        name="product_form.html",
        context={"product": product, "categories": categories, "csrf_token": csrf_token(request)},
    )


def _save_product(
    *, db: Session, product: Product | None, name: str, price: int, category_id: int,
    brand: str, description: str, specs: str, in_stock: bool, image: UploadFile | None,
) -> bool:
    if product is None:
        product = Product(
            name=name.strip(), price=price, category_id=category_id, brand=brand.strip(),
            description=description.strip(), specs=specs.strip(), in_stock=in_stock,
        )
        db.add(product)
    else:
        product.name = name.strip()
        product.price = price
        product.category_id = category_id
        product.brand = brand.strip()
        product.description = description.strip()
        product.specs = specs.strip()
        product.in_stock = in_stock

    saved = save_image(image, subdir="products")
    if saved:
        product.image = saved
    db.commit()
    return True


@router.post("/products/create")
def product_create(
    request: Request,
    name: str = Form(...), price: int = Form(...), category_id: int = Form(...),
    brand: str = Form(""), description: str = Form(""), specs: str = Form(""),
    in_stock: str | None = Form(None), image: UploadFile | None = None,
    token: str | None = Form(None), db: Session = DbSession, _=Depends(require_admin),
):
    verify_csrf(request, token)
    _save_product(
        db=db, product=None, name=name, price=price, category_id=category_id, brand=brand,
        description=description, specs=specs, in_stock=in_stock == "on", image=image,
    )
    return redirect("/admin/products")


@router.post("/products/{product_id}/update")
def product_update(
    product_id: int,
    request: Request,
    name: str = Form(...), price: int = Form(...), category_id: int = Form(...),
    brand: str = Form(""), description: str = Form(""), specs: str = Form(""),
    in_stock: str | None = Form(None), image: UploadFile | None = None,
    token: str | None = Form(None), db: Session = DbSession, _=Depends(require_admin),
):
    verify_csrf(request, token)
    product = db.get(Product, product_id)
    if product is None:
        return redirect("/admin/products")
    _save_product(
        db=db, product=product, name=name, price=price, category_id=category_id, brand=brand,
        description=description, specs=specs, in_stock=in_stock == "on", image=image,
    )
    return redirect("/admin/products")


@router.post("/products/{product_id}/delete")
def product_delete(
    product_id: int,
    request: Request,
    token: str | None = Form(None),
    db: Session = DbSession,
    _=Depends(require_admin),
):
    verify_csrf(request, token)
    product = db.get(Product, product_id)
    if product is not None:
        db.delete(product)
        db.commit()
    return redirect("/admin/products")


@router.post("/products/{product_id}/stock")
def product_stock(
    product_id: int,
    request: Request,
    token: str | None = Form(None),
    db: Session = DbSession,
    _=Depends(require_admin),
):
    verify_csrf(request, token)
    product = db.get(Product, product_id)
    if product is not None:
        product.in_stock = not product.in_stock
        db.commit()
    return redirect("/admin/products")


@router.get("/orders", response_class=HTMLResponse)
def orders_page(request: Request, db: Session = DbSession, _=Depends(require_admin)):
    orders = db.scalars(
        select(Order).options(joinedload(Order.items)).order_by(Order.created_at.desc(), Order.id.desc())
    ).unique().all()
    return templates.TemplateResponse(
        request=request,
        name="orders.html",
        context={"orders": orders, "statuses": list(OrderStatus), "csrf_token": csrf_token(request)},
    )


@router.post("/orders/{order_id}/status")
def order_status_update(
    order_id: int,
    request: Request,
    status_value: str = Form(..., alias="status"),
    token: str | None = Form(None),
    db: Session = DbSession,
    _=Depends(require_admin),
):
    verify_csrf(request, token)
    order = db.get(Order, order_id)
    try:
        new_status = OrderStatus(status_value)
    except ValueError:
        return redirect("/admin/orders")
    if order is not None:
        order.status = new_status
        db.commit()
    return redirect("/admin/orders")

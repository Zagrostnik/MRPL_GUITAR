from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from app import models  # noqa: F401
from app.config import BASE_DIR, settings
from app.database import Base, SessionLocal, engine
from app.routes import admin, shop
from app.seed import normalize_category_names, seed_if_empty

STATIC_DIR = BASE_DIR / "app" / "static"
INDEX_FILE = STATIC_DIR / "index.html"
settings.upload_dir.mkdir(parents=True, exist_ok=True)


def remove_legacy_order_tables() -> None:
    """Remove the old order system and its stored customer details during migration."""
    with engine.begin() as connection:
        # Child table first to respect foreign keys on SQLite and PostgreSQL.
        connection.execute(text("DROP TABLE IF EXISTS order_items"))
        connection.execute(text("DROP TABLE IF EXISTS orders"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    remove_legacy_order_tables()
    Base.metadata.create_all(engine)
    if settings.seed_demo_data:
        with SessionLocal() as db:
            normalize_category_names(db)
            seed_if_empty(db)
    yield


app = FastAPI(title="Мелодия Гитар", version="1.0.0", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, session_cookie="melody_admin", same_site="lax")

app.include_router(shop.router)
app.include_router(admin.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    return JSONResponse({"message": "Фронтенд ещё не подключён. API: /docs"})

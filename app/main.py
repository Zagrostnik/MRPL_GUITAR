from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import models  # noqa: F401
from app.config import BASE_DIR, settings
from app.database import Base, SessionLocal, engine
from app.routes import admin, shop
from app.seed import seed_if_empty

STATIC_DIR = BASE_DIR / "app" / "static"
INDEX_FILE = STATIC_DIR / "index.html"
settings.upload_dir.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    if settings.seed_demo_data:
        with SessionLocal() as db:
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

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Product

U = "https://images.unsplash.com/photo-{}?auto=format&fit=crop&w={}&q=80"

CATEGORIES = [
    # slug, name, icon, photo id
    ("elektrogitary", "Электрогитары", "fa-guitar", "1564186763535-ebb21ef5277f"),
    ("akusticheskie-gitary", "Акустические гитары", "fa-music", "1510915361894-db8b60106cb1"),
    ("bas-gitary", "Бас-гитары", "fa-sliders", "1563379091339-03b21ab4a4f8"),
    ("usiliteli", "Комбоусилители", "fa-volume-high", "1543852786-1cf6624b9987"),
    ("pedali-effektov", "Педали эффектов", "fa-bolt", "1598488035139-bdbb2231ce04"),
    ("aksessuary", "Аксессуары", "fa-box-archive", "1525201548942-d8732f6617a0"),
]

PRODUCTS = [
    # name, category slug, brand, price, in_stock, photo id, description, specs
    ("Электрогитара Epiphone Les Paul Standard", "elektrogitary", "Epiphone", 64900, True,
     "1550985516-3ec0bbe609ed",
     "Классический электрогитарный инструмент, корпус из красного дерева с топом из волнистого клена, хамбакеры ProBucker, 22 лада.",
     "Корпус: красное дерево / клен. Гриф: вклеенный, махагони. Звукосниматели: H-H ProBucker."),
    ("Акустическая гитара Yamaha F310", "akusticheskie-gitary", "Yamaha", 21500, True,
     "1510915361894-db8b60106cb1",
     "Надежная акустическая гитара с верхней декой из ели. Отличный резонанс и сбалансированное звучание для обучения и репетиций.",
     "Верхняя дека: ель. Нижняя дека и обечайки: местное дерево. Мензура: 634 мм."),
    ("Бас-гитара Squier Affinity Jazz Bass", "bas-gitary", "Fender/Squier", 43200, True,
     "1563379091339-03b21ab4a4f8",
     "Легендарный джаз-бас с двумя синглами. Удобный тонкий гриф, яркий и плотный микс.",
     "Корпус: тополь. Гриф: клен, профиль 'C'. Звукосниматели: Ceramic Single-Coil Jazz Bass."),
    ("Гитарная педаль Boss DS-1 Distortion", "pedali-effektov", "Boss", 11200, True,
     "1598488035139-bdbb2231ce04",
     "Классический дисторшн для электрогитары. Плотный роковый перегруз, проверенный десятилетиями.",
     "Управление: Dist, Tone, Level. Питание: батарея 9В или адаптер."),
    ("Комбоусилитель Marshall MG15R", "usiliteli", "Marshall", 19800, True,
     "1543852786-1cf6624b9987",
     "Транзисторный комбоусилитель мощностью 15 Ватт с чистым каналом, овердрайвом и встроенным ревербератором.",
     "Мощность: 15 Вт. Динамик: 8 дюймов. Эффекты: Reverb."),
    ("Набор струн D'Addario EXL110 (10-46)", "aksessuary", "D'Addario", 1450, True,
     "1525201548942-d8732f6617a0",
     "Популярный комплект никелированных струн для электрогитары с универсальным натяжением.",
     "Калибр: 010-046. Материал: никелированная сталь."),
    ("Электрогитара Ibanez Gio GRX70QA", "elektrogitary", "Ibanez", 36500, False,
     "1511671782779-c97d3d27a1d4",
     "Скоростной гриф, конфигурация звукоснимателей H-S-H для универсального звучания от блюза до метала.",
     "Корпус: тополь с топом из стеганого клена. Лады: 22 Medium."),
    ("Процессор эффектов Zoom G1 Four", "pedali-effektov", "Zoom", 14900, True,
     "1563379091339-03b21ab4a4f8",
     "Компактный процессор с более чем 60 эффектами и моделями усилителей, лупером и ритм-машиной.",
     "Эффекты: до 5 одновременно. Память патчей: 50."),
]


def seed_if_empty(db: Session) -> None:
    """Заполняет пустую БД категориями и товарами из исходного макета."""
    if db.scalar(select(func.count()).select_from(Category)):
        return

    by_slug: dict[str, Category] = {}
    for slug, name, icon, photo in CATEGORIES:
        cat = Category(name=name, slug=slug, icon=icon, image=U.format(photo, 300))
        db.add(cat)
        by_slug[slug] = cat
    db.flush()

    for name, slug, brand, price, in_stock, photo, description, specs in PRODUCTS:
        db.add(
            Product(
                name=name,
                category_id=by_slug[slug].id,
                brand=brand,
                price=price,
                in_stock=in_stock,
                image=U.format(photo, 600),
                description=description,
                specs=specs,
            )
        )
    db.commit()

"""
weekly_scraper.py – Scraper + Thin API
=====================================
Pipeline completo para extraer información de productos financieros, descargar
PDFs de T&C y exponerla mediante una **API REST minimalista** con FastAPI.

Cambios principales respecto a la versión previa:
------------------------------------------------
* **FastAPI** agregado (sección "API Thin")
* **CORS** habilitado opcionalmente
* Función `get_session()` para inyección de dependencias en los endpoints
* Endpoint **/search** con búsqueda FTS5 (SQLite) + fallback LIKE
* Modularización: separamos configuración en `config.py` para facilitar nuevos
  mercados (MX, US, CO, etc.) – pero sigue inline para mantener el script en un
  solo archivo.

Requisitos extra (pip install ...): fastapi, uvicorn, python-multipart (si vas a
recibir uploads), pydantic-settings (opcional)

Uso rápido
----------
$ python weekly_scraper.py --run-now        # ejecuta scraping y termina
$ uvicorn weekly_scraper:app --reload       # arranca la API Thin en localhost:8000

Producción: contenedor Docker + `CMD ["uvicorn", "weekly_scraper:app", "--host=0.0.0.0", "--port=80"]`

Estrategia multipaís
--------------------
1. **Archivo institutions.json**
   ```json
   {
     "bbva-mx": {"name": "BBVA México",   "base_url": "https://www.bbva.mx",   "product_patterns": ["/personas/"]},
     "bbva-usa": {"name": "BBVA USA",      "base_url": "https://www.bbvausa.com", "product_patterns": ["/personal/"]},
     "bancolombia": {"name": "Bancolombia", "base_url": "https://www.grupobancolombia.com", "product_patterns": ["/personas/"]}
   }
   ```
   Cárgala al inicio con `json.load(open("institutions.json"))`.
2. **Regex adaptable**: `product_patterns` acepta lista de patterns por país.
3. **locales**: si quieres clasificar productos por idioma/regulación, añade
   `country`, `currency`, etc. en la tabla `institutions`.

"""
from __future__ import annotations
import os
import re
import json
import logging
import pathlib
import datetime as dt
from typing import List, Dict, Optional, Generator
from urllib.parse import urljoin, urlparse
from fastapi import FastAPI

import requests
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean,
    UniqueConstraint, Index, select
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from slugify import slugify

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI()

LOG_LEVEL = os.getenv("SCRAPER_LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = pathlib.Path(os.getenv("SCRAPER_DATA_DIR", "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_URL = os.getenv("SCRAPER_DB_URL", "sqlite:///finai.db")

# Carga dinámica de instituciones (puede venir de JSON externo)
if os.getenv("INSTITUTIONS_FILE") and pathlib.Path(os.getenv("INSTITUTIONS_FILE")).exists():
    INSTITUTIONS = json.loads(pathlib.Path(os.getenv("INSTITUTIONS_FILE")).read_text())
else:
    INSTITUTIONS: Dict[str, Dict[str, str | List[str]]] = {
        "bbva-mx": {
            "name": "BBVA México",
            "base_url": "https://www.bbva.mx",
            "product_patterns": [r"/personas/[^#?]*"],
        },
    }

# ──────────────────────────────────────────────────────────────────────────────
# DB Models
# ──────────────────────────────────────────────────────────────────────────────

Base = declarative_base()

class Institution(Base):
    __tablename__ = "institutions"
    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    country = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    products = relationship("Product", back_populates="institution", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    url = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    title = Column(String)
    last_seen = Column(DateTime, default=dt.datetime.utcnow)

    documents = relationship("Document", back_populates="product", cascade="all, delete-orphan")
    institution = relationship("Institution", back_populates="products")

    __table_args__ = (
        UniqueConstraint("institution_id", "url", name="uq_product_url"),
    )

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    url = Column(String, nullable=False)
    local_path = Column(String, nullable=False)
    text = Column(Text)
    version = Column(Integer, default=1)
    scraped_at = Column(DateTime, default=dt.datetime.utcnow)
    is_active = Column(Boolean, default=True)

    product = relationship("Product", back_populates="documents")

    __table_args__ = (
        UniqueConstraint("product_id", "url", name="uq_document_url"),
        Index("ix_document_text", "text")
    )

# ──────────────────────────────────────────────────────────────────────────────
# DB Helpers
# ──────────────────────────────────────────────────────────────────────────────

engine = create_engine(DB_URL, echo=False, future=True)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as db:
        yield db

# ──────────────────────────────────────────────────────────────────────────────
# Scraping utils
# ──────────────────────────────────────────────────────────────────────────────

def fetch(url: str, timeout: int = 20) -> Optional[str]:
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "FinaiBot/0.2"})
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return resp.text
    except Exception as e:
        logger.warning(f"No se pudo obtener {url}: {e}")
        return None

def is_pdf(url: str) -> bool:
    return url.lower().split("?")[0].endswith(".pdf")

def sanitize_filename(url: str) -> str:
    parsed = urlparse(url)
    name = pathlib.Path(parsed.path).name or slugify(url)
    return slugify(name, max_length=60)

def download_pdf(url: str, dest_dir: pathlib.Path) -> Optional[pathlib.Path]:
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        filename = sanitize_filename(url)
        dest = dest_dir / filename
        if dest.exists():
            return dest
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return dest
    except Exception as e:
        logger.warning(f"Error descargando PDF {url}: {e}")
        return None

def extract_product_links(html: str, base_url: str, patterns: List[str]) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full = urljoin(base_url, href)
        if any(re.search(pat, href) for pat in patterns):
            links.append(full)
    return list(dict.fromkeys(links))

# ──────────────────────────────────────────────────────────────────────────────
# Core crawling logic
# ──────────────────────────────────────────────────────────────────────────────

def crawl_institution(slug: str, cfg: Dict[str, str | List[str]]):
    base_url = cfg["base_url"]
    patterns = cfg["product_patterns"]

    html = fetch(base_url)
    if not html:
        return

    product_links = extract_product_links(html, base_url, patterns)
    logger.info(f"{slug}: {len(product_links)} productos encontrados")

    with SessionLocal() as db:
        inst = db.query(Institution).filter_by(slug=slug).first()
        if not inst:
            inst = Institution(slug=slug, name=cfg["name"], country=cfg.get("country"))
            db.add(inst)
            db.commit()

        for link in product_links:
            product_slug = slugify(link)
            product = (
                db.query(Product)
                .filter_by(institution_id=inst.id, url=link)
                .first()
            )
            if not product:
                product = Product(institution_id=inst.id, url=link, slug=product_slug)
                db.add(product)
                db.commit()
            product.last_seen = dt.datetime.utcnow()
            db.commit()

            page_html = fetch(link)
            if not page_html:
                continue
            soup = BeautifulSoup(page_html, "lxml")
            if not product.title:
                title_tag = soup.find(["h1", "title"])
                if title_tag:
                    product.title = title_tag.get_text(strip=True)
                    db.commit()

            pdf_links = [urljoin(link, a["href"]) for a in soup.find_all("a", href=True) if is_pdf(a["href"])]
            for pdf_url in pdf_links:
                doc = (
                    db.query(Document)
                    .filter_by(product_id=product.id, url=pdf_url)
                    .first()
                )
                if doc:
                    continue

                local_path = download_pdf(pdf_url, DATA_DIR / slug)
                if not local_path:
                    continue

                text_content = extract_text(str(local_path))
                doc = Document(product_id=product.id, url=pdf_url, local_path=str(local_path), text=text_content)
                db.add(doc)
                db.commit()
                logger.info(f"Almacenado doc {pdf_url}")

# ──────────────────────────────────────────────────────────────────────────────
# Orchestration (weekly)
# ──────────────────────────────────────────────────────────────────────────────

def run_full_scrape():
    logger.info("===== INICIO SCRAPING =====")
    for slug, cfg in INSTITUTIONS.items():
        try:
            crawl_institution(slug, cfg)
        except Exception as e:
            logger.error(f"Error {slug}: {e}")
    logger.info("===== FIN SCRAPING =====")


def schedule_weekly_scrape():
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run_full_scrape, CronTrigger(day_of_week="sun", hour=3))
    logger.info("Scheduler activo (domingo 03:00 UTC)")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass

# ──────────────────────────────────────────────────────────────────────────────
# Thin API (FastAPI)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from fastapi import FastAPI, Depends, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    FastAPI = None  # type: ignore

if FastAPI:
    app = FastAPI(title="Finai Thin API")

    # CORS (ajusta origins en prod)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class InstitutionOut(BaseModel):
        id: int
        slug: str
        name: str
        country: Optional[str] = None
        class Config:
            orm_mode = True

    class ProductOut(BaseModel):
        id: int
        slug: str
        url: str
        title: Optional[str]
        institution_id: int
        class Config:
            orm_mode = True

    class DocumentOut(BaseModel):
        id: int
        url: str
        version: int
        scraped_at: dt.datetime
        product_id: int
        class Config:
            orm_mode = True

    @app.get("/institutions", response_model=List[InstitutionOut])
    def list_institutions(db: Session = Depends(get_session)):
        return db.scalars(select(Institution)).all()

    @app.get("/institutions/{slug}/products", response_model=List[ProductOut])
    def list_products(slug: str, db: Session = Depends(get_session)):
        inst = db.scalar(select(Institution).where(Institution.slug == slug))
        if not inst:
            raise HTTPException(404, "Institution not found")
        return inst.products

    @app.get("/products/{product_id}/documents", response_model=List[DocumentOut])
    def list_docs(product_id: int, db: Session = Depends(get_session)):
        prod = db.scalar(select(Product).where(Product.id == product_id))
        if not prod:
            raise HTTPException(404, "Product not found")
        return prod.documents

    @app.get("/search", response_model=List[DocumentOut])
    def search(q: str, limit: int = 20, db: Session = Depends(get_session)):
        # SQLite FTS5 example; fallback to LIKE
        try:
            rows = db.execute(
                "SELECT d.* FROM documents d JOIN docs_fts f ON d.id = f.rowid WHERE f.text MATCH ? LIMIT ?",
                (q, limit),
            ).fetchall()
            return [Document(**dict(r)) for r in rows]  # type: ignore
        except Exception:
            pattern = f"%{q}%"
            docs = db.scalars(select(Document).where(Document.text.like(pattern)).limit(limit)).all()
            return docs

else:
    app = None  # FastAPI no instalado

# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Finai scraper + API")
    parser.add_argument("--run-now", action="store_true", help="Scrapea y sale")
    parser.add_argument("--schedule", action="store_true", help="Ejecuta scheduler semanal")
    args = parser.parse_args()

    if args.run_now:
        run_full_scrape()
    elif args.schedule:
        schedule_weekly_scrape()
    else:
        if app is None:
            print("Instala fastapi y uvicorn para usar la API")
        else:
            import uvicorn
            uvicorn.run("weekly_scraper:app", host="0.0.0.0", port=8000, reload=True)

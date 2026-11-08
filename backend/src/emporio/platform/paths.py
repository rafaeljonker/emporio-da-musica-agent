from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[4]
DATA_DIR: Path = REPO_ROOT / "data"

_CASE_CSV_KEYS = ("products", "promotions", "customers", "categories", "order_items", "orders")
CASE_CSV_FILES: dict[str, Path] = {
    key: DATA_DIR / f"desafio_tecnico_ai_eng - {key}.csv" for key in _CASE_CSV_KEYS
}

# NFC-normalized name (accented "í" is a single code point).
POLICIES_PDF: Path = DATA_DIR / "políticas_da_loja.pdf"

MIGRATIONS_DIR: Path = REPO_ROOT / "backend" / "migrations"

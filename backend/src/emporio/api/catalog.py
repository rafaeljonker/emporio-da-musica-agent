from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Request
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints, field_validator

from emporio.api.errors import ApiErrorCode, http_error
from emporio.api.guards import Session, SlidingWindow, client_ip, require_json, require_session
from emporio.catalog.application.admin import CatalogAdmin, ProductInput, ProductView
from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.config import Settings
from emporio.shared.result import Err, Ok, Result

# Zero-width marks and bidi embeddings, overrides and isolates: text that renders unlike it reads.
_INVISIBLE = "\u200b-\u200f\u202a-\u202e\u2066-\u2069"
# One line: no C0 control, DEL or invisible mark.
_LINE = f"^[^\x00-\x1f\x7f{_INVISIBLE}]*$"
# Free text: also keeps tab and line breaks.
_TEXT = f"^[^\x00-\x08\x0b\x0c\x0e-\x1f\x7f{_INVISIBLE}]*$"

SpecKey = Annotated[str, StringConstraints(min_length=1, max_length=40, pattern=_LINE)]
SpecValue = Annotated[str, StringConstraints(min_length=1, max_length=120, pattern=_LINE)]


class ProductIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: Annotated[str, StringConstraints(min_length=2, max_length=120, pattern=_LINE)]
    category_id: Annotated[StrictInt, Field(ge=1, le=2_147_483_647)]
    description: Annotated[str, StringConstraints(max_length=2000, pattern=_TEXT)] = ""
    # A decimal string, never a JSON number: floats lose cents. ASCII digits only.
    price: Annotated[str, StringConstraints(pattern=r"^[0-9]{1,6}(\.[0-9]{1,2})?$")]
    stock: Annotated[StrictInt, Field(ge=0, le=100_000)]
    status: Literal["active", "discontinued", "coming_soon"]
    specs: Annotated[dict[SpecKey, SpecValue], Field(max_length=20)] = {}

    @field_validator("price")
    @classmethod
    def _positive_cents(cls, value: str) -> str:
        if Decimal(value) <= 0:
            raise ValueError("price_not_positive")
        return value

    def to_input(self) -> ProductInput:
        return ProductInput(
            self.name,
            self.category_id,
            self.description,
            Decimal(self.price),
            self.stock,
            self.status,
            tuple(self.specs.items()),
        )


def _product_json(p: ProductView) -> dict[str, object]:
    return {
        "id": p.id,
        "name": p.name,
        "category_id": p.category_id,
        "category": p.category,
        "description": p.description,
        "specs": dict(p.specs),
        "price": str(p.price.quantize(Decimal("0.01"))),
        "stock": p.stock,
        "status": p.status,
    }


def _owner(request: Request, _: Annotated[Session, Depends(require_session)]) -> str:
    lid = request.session.get("lid")
    if not isinstance(lid, str) or not lid:
        raise http_error(ApiErrorCode.UNAUTHENTICATED)
    return lid


Owner = Annotated[str, Depends(_owner)]


def _unwrap[T](result: Result[T, CatalogErrorCode]) -> T:
    match result:
        case Ok(value):
            return value
        case Err(code):
            raise http_error(code)


def build_catalog_router(catalog: CatalogAdmin, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/catalog")
    m = settings.rate_limit_multiplier
    per_login = SlidingWindow(10 * m, 60)
    # Any visitor can log in again for a fresh lid, so the IP windows are the real ceiling.
    per_ip = SlidingWindow(10 * m, 60)
    creates_per_ip = SlidingWindow(30 * m, 3600)

    def write_slot(owner: Owner, request: Request) -> str:
        # Keyed by the login, not the sid: a customer switch rotates sid but not lid.
        if not (per_login.allow(owner) and per_ip.allow(client_ip(request, settings))):
            raise http_error(ApiErrorCode.TOO_MANY_WRITES)
        return owner

    def create_slot(owner: Annotated[str, Depends(write_slot)], request: Request) -> str:
        if not creates_per_ip.allow(client_ip(request, settings)):
            raise http_error(ApiErrorCode.TOO_MANY_WRITES)
        return owner

    @router.get("/categories")
    def categories(_: Owner) -> list[dict[str, object]]:
        return [{"id": i, "name": name} for i, name in _unwrap(catalog.categories())]

    @router.get("/products/mine")
    def mine(owner: Owner) -> list[dict[str, object]]:
        return [_product_json(p) for p in _unwrap(catalog.mine(owner))]

    @router.post("/products", status_code=201, dependencies=[Depends(require_json)])
    def create(body: ProductIn, owner: Annotated[str, Depends(create_slot)]) -> dict[str, object]:
        return _product_json(_unwrap(catalog.create(owner, body.to_input())))

    @router.put("/products/{product_id}", dependencies=[Depends(require_json)])
    def update(
        product_id: Annotated[int, Path(ge=1, le=2_147_483_647)],
        body: ProductIn,
        owner: Annotated[str, Depends(write_slot)],
    ) -> dict[str, object]:
        return _product_json(_unwrap(catalog.update(owner, product_id, body.to_input())))

    return router

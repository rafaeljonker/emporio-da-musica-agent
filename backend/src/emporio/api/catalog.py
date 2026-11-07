from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints, field_validator

from emporio.api.guards import Session, SlidingWindow, require_json, require_session
from emporio.config import Settings
from emporio.support.application.ports import (
    CatalogAdmin,
    CatalogWriteRejected,
    ProductInput,
    ProductView,
)

_STATUS = {"unknown_category": 422, "not_found": 404, "catalog_full": 409}

SpecKey = Annotated[str, StringConstraints(min_length=1, max_length=40)]
SpecValue = Annotated[str, StringConstraints(min_length=1, max_length=120)]


class ProductIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: Annotated[str, StringConstraints(min_length=2, max_length=120)]
    category_id: Annotated[StrictInt, Field(ge=1, le=2_147_483_647)]
    description: Annotated[str, StringConstraints(max_length=2000)] = ""
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
        raise HTTPException(status_code=401, detail="unauthenticated")
    return lid


Owner = Annotated[str, Depends(_owner)]


def build_catalog_router(catalog: CatalogAdmin, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/catalog")
    writes = SlidingWindow(10 * settings.rate_limit_multiplier, 60)

    def write_slot(owner: Owner) -> str:
        # Keyed by the login: a customer switch rotates sid but not lid.
        if not writes.allow(owner):
            raise HTTPException(status_code=429, detail="too_many_writes")
        return owner

    @router.get("/categories")
    def categories(_: Owner) -> list[dict[str, object]]:
        return [{"id": i, "name": name} for i, name in catalog.categories()]

    @router.get("/products/mine")
    def mine(owner: Owner) -> list[dict[str, object]]:
        return [_product_json(p) for p in catalog.mine(owner)]

    @router.post("/products", status_code=201, dependencies=[Depends(require_json)])
    def create(body: ProductIn, owner: Annotated[str, Depends(write_slot)]) -> dict[str, object]:
        try:
            return _product_json(catalog.create(owner, body.to_input()))
        except CatalogWriteRejected as err:
            raise HTTPException(status_code=_STATUS[err.code], detail=err.code) from err

    @router.put("/products/{product_id}", dependencies=[Depends(require_json)])
    def update(
        product_id: Annotated[int, Path(ge=1, le=2_147_483_647)],
        body: ProductIn,
        owner: Annotated[str, Depends(write_slot)],
    ) -> dict[str, object]:
        try:
            return _product_json(catalog.update(owner, product_id, body.to_input()))
        except CatalogWriteRejected as err:
            raise HTTPException(status_code=_STATUS[err.code], detail=err.code) from err

    return router

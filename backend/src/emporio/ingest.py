"""Composition root: apply migrations, then index policies and products."""

from emporio.catalog.infrastructure.csv_catalog_repository import CsvCatalogRepository
from emporio.catalog.infrastructure.pg_product_index import PgProductIndex
from emporio.db import connect
from emporio.embeddings import E5Embedder
from emporio.migrate import apply_migrations
from emporio.policies.application.ingest_policies import IngestPolicies
from emporio.policies.infrastructure.pdf_sections import PdfPolicySource
from emporio.policies.infrastructure.pg_policy_index import PgPolicyIndex


def main() -> None:
    embedder = E5Embedder()
    catalog = CsvCatalogRepository()
    with connect() as conn:
        apply_migrations(conn)
        policies = IngestPolicies(PdfPolicySource(), PgPolicyIndex(conn, embedder))()
        products = catalog.products()
        PgProductIndex(conn, embedder).replace_all(
            products, {c.id: c.name for c in catalog.categories()}
        )
    print(f"policies: {policies}, products: {len(products)}")


if __name__ == "__main__":
    main()

"""Composition root: apply migrations, then index policies and products."""

import sys

from emporio.catalog.infrastructure.csv_catalog_repository import CsvCatalogRepository
from emporio.catalog.infrastructure.pg_product_index import PgProductIndex
from emporio.db import DatabaseNotConfigured, connect, database_url
from emporio.embeddings import E5Embedder
from emporio.migrate import apply_migrations
from emporio.policies.application.ingest_policies import IngestPolicies
from emporio.policies.infrastructure.pdf_sections import PdfPolicySource
from emporio.policies.infrastructure.pg_policy_index import PgPolicyIndex


def main() -> None:
    try:
        url = database_url()
    except DatabaseNotConfigured as err:
        print(err, file=sys.stderr)
        raise SystemExit(2) from err
    embedder = E5Embedder()
    catalog = CsvCatalogRepository()
    with connect(url) as conn:
        apply_migrations(conn)
        policies = IngestPolicies(PdfPolicySource(), PgPolicyIndex(conn, embedder))()
        products = catalog.products()
        PgProductIndex(conn, embedder).replace_all(
            products, {c.id: c.name for c in catalog.categories()}
        )
    print(f"policies: {policies}, products: {len(products)}")


if __name__ == "__main__":
    main()

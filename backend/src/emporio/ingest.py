"""Composition root: apply migrations, then index policies and seed the catalog."""

import sys

from emporio.catalog.infrastructure.csv_catalog_repository import CsvCatalogRepository
from emporio.catalog.infrastructure.pg_catalog_writer import PgCatalogWriter
from emporio.db import DatabaseNotConfigured, connect, database_url, make_pool
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
    csv = CsvCatalogRepository()
    with connect(url) as conn:
        apply_migrations(conn)
    with make_pool(url) as pool:
        policies = IngestPolicies(PdfPolicySource(), PgPolicyIndex(pool, embedder))()
        embedded = PgCatalogWriter(pool, embedder).seed(
            csv.categories(), csv.products(), csv.promotions()
        )
    print(f"policies: {policies}, products: {len(csv.products())} (embedded {embedded})")


if __name__ == "__main__":
    main()

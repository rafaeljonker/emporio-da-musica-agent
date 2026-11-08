from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.catalog.domain.installments import InstallmentPlan, installment_plan, max_installments
from emporio.shared.money import Money
from emporio.shared.result import Ok, Result


class QuoteInstallments:
    def __call__(
        self, total: Money, count: int | None = None
    ) -> Result[InstallmentPlan, CatalogErrorCode]:
        if count is None:
            return Ok(max_installments(total))
        return installment_plan(total, count)

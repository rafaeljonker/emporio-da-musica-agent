from emporio.catalog.domain.installments import InstallmentPlan, installment_plan, max_installments
from emporio.shared.money import Money


class QuoteInstallments:
    def __call__(self, total: Money, count: int | None = None) -> InstallmentPlan:
        if count is None:
            return max_installments(total)
        return installment_plan(total, count)

"""What one turn cost in BRL, from its token counts (or GPU time) and the configured prices."""

from decimal import Decimal

from emporio.platform.config import Provider, Settings
from emporio.support.infrastructure.agent.turn_probe import TurnProbe, to_ms


def _usd(
    price: tuple[Decimal, Decimal, Decimal], input_tokens: int, cached: int, output: int
) -> Decimal:
    usd_in, usd_out, usd_cached = price
    fresh = input_tokens - cached
    return (fresh * usd_in + cached * usd_cached + output * usd_out) / Decimal(1_000_000)


def turn_cost_brl(
    settings: Settings, model: str, guard_model: str, probe: TurnProbe
) -> Decimal | None:
    """None when the model has no price (and is not the GPU-hour priced Gemma)."""
    price = settings.prices.get(model)
    if price is None:
        gpu = settings.gpu_usd_per_hour
        if gpu is None or settings.provider_name != Provider.GEMMA.value:
            return None
        # Upper bound: assumes the GPU served only this turn (concurrency 1).
        ms = Decimal(to_ms(probe.ms_guard) + to_ms(probe.ms_llm))
        return gpu * ms / 3_600_000 * settings.usd_brl
    guard_price = settings.prices.get(guard_model, price)
    agent_usd = _usd(
        price,
        probe.input_tokens - probe.guard_input_tokens,
        probe.cached_tokens - probe.guard_cached_tokens,
        probe.output_tokens - probe.guard_output_tokens,
    )
    guard_usd = _usd(
        guard_price,
        probe.guard_input_tokens,
        probe.guard_cached_tokens,
        probe.guard_output_tokens,
    )
    return (agent_usd + guard_usd) * settings.usd_brl

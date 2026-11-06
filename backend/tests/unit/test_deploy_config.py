"""Deploy constants, read with `ast` so the test needs neither `modal` nor a Modal account."""

import ast

from emporio.paths import REPO_ROOT

DEPLOY_DIR = REPO_ROOT / "deploy"


def _constant(module: str, name: str) -> object:
    tree = ast.parse((DEPLOY_DIR / module).read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    msg = f"{name} is not a literal top-level constant of deploy/{module}"
    raise AssertionError(msg)


def test_ready_ttl_is_under_gpu_scaledown():
    scaledown = _constant("modal_llm.py", "GPU_SCALEDOWN_SECONDS")
    ttl = _constant("modal_api.py", "WARM_READY_TTL_SECONDS")
    assert isinstance(scaledown, int)
    assert isinstance(ttl, int)
    assert 0 < scaledown - ttl <= 120


def test_gpu_prices_cover_every_gpu():
    prices = _constant("modal_api.py", "GPU_PRICES")
    gpus = _constant("modal_llm.py", "GPUS")
    assert isinstance(prices, dict)
    assert isinstance(gpus, tuple)
    assert set(prices) == set(gpus)


def test_llm_weights_cover_every_weights_key():
    names = _constant("modal_api.py", "LLM_WEIGHTS")
    weights = _constant("modal_llm.py", "WEIGHTS")
    assert isinstance(names, tuple)
    assert isinstance(weights, dict)
    assert set(names) == set(weights)

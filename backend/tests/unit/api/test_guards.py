import time

from emporio.api.guards import SlidingWindow


def test_expired_key_is_removed():
    window = SlidingWindow(1, 0.01)
    assert window.allow("a")
    time.sleep(0.03)
    assert window.allow("b")
    assert "a" not in window._hits  # pyright: ignore[reportPrivateUsage]  # whitebox: no leak

from emporio.support.domain.channel_identity import ChannelIdentity


def test_thread_id_differs_per_customer() -> None:
    a = ChannelIdentity("web", 1, "s").thread_id()
    b = ChannelIdentity("web", 2, "s").thread_id()
    assert a == "web:customer:1"
    assert a != b


def test_anonymous_thread_uses_session() -> None:
    assert ChannelIdentity("web", None, "abc").thread_id() == "web:anon:abc"

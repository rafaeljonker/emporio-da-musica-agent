from emporio.support.domain.channel_identity import ChannelIdentity


def test_thread_id_differs_per_customer() -> None:
    a = ChannelIdentity("web", 1, "s").thread_id()
    b = ChannelIdentity("web", 2, "s").thread_id()
    assert a == "web:customer:1:s"
    assert a != b


def test_same_customer_two_sessions_get_different_threads() -> None:
    a = ChannelIdentity("web", 1, "s1").thread_id()
    b = ChannelIdentity("web", 1, "s2").thread_id()
    assert a != b


def test_anonymous_thread_uses_session() -> None:
    assert ChannelIdentity("web", None, "abc").thread_id() == "web:anon:abc"

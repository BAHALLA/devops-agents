"""Tests for Slack thread → ADK session mapping."""


class TestSessionMap:
    def test_get_returns_none_for_unknown_thread(self, session_map):
        assert session_map.get("C_CHAN", "123.456") is None

    def test_set_and_get(self, session_map):
        session_map.set("C_CHAN", "123.456", "sess_abc")
        assert session_map.get("C_CHAN", "123.456") == "sess_abc"

    def test_different_channels_are_independent(self, session_map):
        session_map.set("C_ONE", "123.456", "sess_1")
        session_map.set("C_TWO", "123.456", "sess_2")
        assert session_map.get("C_ONE", "123.456") == "sess_1"
        assert session_map.get("C_TWO", "123.456") == "sess_2"

    def test_different_threads_are_independent(self, session_map):
        session_map.set("C_CHAN", "111.000", "sess_a")
        session_map.set("C_CHAN", "222.000", "sess_b")
        assert session_map.get("C_CHAN", "111.000") == "sess_a"
        assert session_map.get("C_CHAN", "222.000") == "sess_b"

    def test_remove(self, session_map):
        session_map.set("C_CHAN", "123.456", "sess_abc")
        session_map.remove("C_CHAN", "123.456")
        assert session_map.get("C_CHAN", "123.456") is None

    def test_remove_nonexistent_is_noop(self, session_map):
        session_map.remove("C_CHAN", "999.999")  # should not raise

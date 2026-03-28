from data_pipeline.db import Database


def _make_db() -> Database:
    return Database("postgresql://fake/db")


class FakeCursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return self.rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, row_factory=None):
        return self._cursor

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_fetch_unsummarized_content_default(monkeypatch) -> None:
    db = _make_db()
    rows = [{"id": "abc", "filename": "newsletters/abc.md", "title": "ABC"}]
    fake_cur = FakeCursor(rows=rows)
    fake_conn = FakeConnection(fake_cur)
    monkeypatch.setattr(db, "_connect", lambda: fake_conn)

    result = db.fetch_unsummarized_content()
    assert result == rows
    sql = fake_cur.executed[0][0]
    assert "summary IS NULL" in sql


def test_fetch_unsummarized_content_force(monkeypatch) -> None:
    db = _make_db()
    rows = [{"id": "abc", "filename": "newsletters/abc.md", "title": "ABC"}]
    fake_cur = FakeCursor(rows=rows)
    fake_conn = FakeConnection(fake_cur)
    monkeypatch.setattr(db, "_connect", lambda: fake_conn)

    result = db.fetch_unsummarized_content(force=True)
    assert result == rows
    sql = fake_cur.executed[0][0]
    assert "summary IS NULL" not in sql


def test_update_summary(monkeypatch) -> None:
    db = _make_db()
    fake_cur = FakeCursor()
    fake_conn = FakeConnection(fake_cur)
    monkeypatch.setattr(db, "_connect", lambda: fake_conn)

    db.update_summary("abc", "This is a summary.")
    assert len(fake_cur.executed) == 1
    sql, params = fake_cur.executed[0]
    assert "UPDATE content" in sql
    assert params["summary"] == "This is a summary."
    assert params["id"] == "abc"

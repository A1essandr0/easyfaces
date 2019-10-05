import sqlite3

import pytest
from imageapp.db import get_db


def test_get_close_db(app):
    with app.app_context():
        db = get_db()
        assert db is get_db()

    with pytest.raises(sqlite3.ProgrammingError) as e:
        db.execute('SELECT 1')

    assert str(e) is not None

def test_init_db_command(runner, monkeypatch):
    class Recorder(object):
        called = False

    def fake_init_db():
        Recorder.called = True

    monkeypatch.setattr('imageapp.db.init_db', fake_init_db)
    result = runner.invoke(args=['init-db'])
    assert 'activated' in result.output
    assert Recorder.called

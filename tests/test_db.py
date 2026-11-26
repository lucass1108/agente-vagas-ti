import os, tempfile
from pathlib import Path

import pytest

import db


@pytest.fixture(autouse=True)
def tmp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_FILE", tmp_path / "test.db")
    db.init_db()
    yield
    if (tmp_path / "test.db").exists():
        (tmp_path / "test.db").unlink()


def test_insercao_e_dedup():
    v = {"titulo": "Estágio Python", "empresa": "X", "fonte": "Gupy", "score": 80, "url": "https://example.com/1"}
    assert db.upsert_vaga(v) is True  # nova
    assert db.upsert_vaga(v) is False  # duplicada


def test_deteccao_novas():
    v = {"titulo": "Estágio Python", "empresa": "X", "fonte": "Gupy", "score": 80, "url": "https://example.com/2"}
    db.upsert_vaga(v)
    novas = db.listar_novas()
    assert len(novas) == 1
    db.marcar_enviadas(["https://example.com/2"])
    assert len(db.listar_novas()) == 0
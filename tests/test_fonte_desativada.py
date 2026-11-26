import os
import pytest

import vagas_agent as va


def test_fonte_desativada_avisa(monkeypatch):
    monkeypatch.setenv("ADZUNA_APP_ID", "")
    monkeypatch.setenv("ADZUNA_APP_KEY", "")
    # reset global
    va.ADZUNA_ID = ""
    va.ADZUNA_KEY = ""
    va.FONTES_DESATIVADAS.clear()
    res = va.buscar_adzuna("estágio ti")
    assert res == []
    assert "Adzuna" in va.FONTES_DESATIVADAS
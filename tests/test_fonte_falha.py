import pytest
from unittest.mock import patch

import vagas_agent as va


def test_fonte_falha_nao_quebra_coleta(monkeypatch):
    va.FONTES_COM_FALHA.clear()
    va.FONTES_DESATIVADAS.clear()

    def boom(*a, **k):
        raise Exception("timeout")

    monkeypatch.setattr(va, "buscar_bing", boom)
    # Adzuna sem chaves (desativada)
    va.ADZUNA_ID = ""
    va.ADZUNA_KEY = ""
    vagas, hist, stats = va.coletar()
    # Gupy pode ou não retornar, mas não deve crashar
    assert isinstance(vagas, list)
    # Bing deve estar na lista de falhas
    assert "Bing" in va.FONTES_COM_FALHA
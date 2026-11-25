import pytest
from datetime import datetime, timedelta

from vagas_agent import calcula_score


def make_vaga(titulo, cidade="São Paulo", descricao="", data=None, prazo="", remoto=False, tipo=""):
    return {
        "titulo": titulo,
        "empresa": "Empresa Teste",
        "cidade": cidade,
        "url": "https://example.com/vaga/1",
        "tipo": tipo,
        "remoto": remoto,
        "descricao": descricao,
        "data": data if data is not None else datetime.now().strftime("%Y-%m-%d"),
        "prazo": prazo,
        "fonte": "Teste",
    }


def test_estagio_ti_python_sp_score_alto():
    v = make_vaga("Estágio Python", cidade="São Paulo", descricao="python sql flask mysql git")
    v = calcula_score(v)
    assert v["score"] >= 60


def test_penalidade_senior():
    v = make_vaga("Desenvolvedor Sênior Python", cidade="São Paulo", descricao="python")
    v = calcula_score(v)
    assert "nível acima" in v["motivos"]


def test_penalidade_pleno():
    v = make_vaga("Desenvolvedor Pleno Python", cidade="São Paulo", descricao="python")
    v = calcula_score(v)
    assert "nível acima" in v["motivos"]


def test_penalidade_fora_regiao():
    v = make_vaga("Estágio Python", cidade="Curitiba", descricao="python")
    v = calcula_score(v)
    assert "fora da região" in v["motivos"]


def test_recente_ganha_bonus():
    hoje = datetime.now().strftime("%Y-%m-%d")
    v = make_vaga("Estágio Python", cidade="São Paulo", descricao="python", data=hoje)
    v = calcula_score(v)
    assert "recente" in v["motivos"]


def test_score_clamp():
    v = make_vaga("Estágio Python", cidade="São Paulo", descricao="python sql flask mysql git")
    v = calcula_score(v)
    assert 0 <= v["score"] <= 100

    v2 = make_vaga("Sênior Pleno Especialista Gerente", cidade="Curitiba", descricao="")
    v2 = calcula_score(v2)
    assert 0 <= v2["score"] <= 100
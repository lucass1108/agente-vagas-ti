import pytest
from datetime import datetime, timedelta

from vagas_agent import valida, vaga_aprovada


def make_vaga(titulo, cidade="São Paulo", descricao="python sql flask", url="https://example.com/vaga/1",
              data=None, prazo="", remoto=False, tipo=""):
    return {
        "titulo": titulo,
        "empresa": "Empresa Teste",
        "cidade": cidade,
        "url": url,
        "tipo": tipo,
        "remoto": remoto,
        "descricao": descricao,
        "data": data if data is not None else datetime.now().strftime("%Y-%m-%d"),
        "prazo": prazo,
        "fonte": "Teste",
    }


def test_titulo_curto_rejeitado():
    v = make_vaga("Dev")
    assert valida(v) is False


def test_titulo_numerico_rejeitado():
    v = make_vaga("123456")
    assert valida(v) is False


def test_url_sem_http_rejeitada():
    v = make_vaga("Estágio Python", url="example.com/vaga/1")
    assert valida(v) is False


def test_vaga_nao_ti_rejeitada():
    v = make_vaga("Estágio de Limpeza", descricao="limpeza faxina", cidade="São Paulo")
    assert vaga_aprovada(v) is False


def test_vaga_encerrada_rejeitada():
    ontem = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    v = make_vaga("Estágio Python", prazo=ontem)
    assert vaga_aprovada(v) is False


def test_vaga_valida_aceita():
    futuro = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
    v = make_vaga("Estágio Python TI", prazo=futuro, descricao="python sql flask mysql git")
    assert vaga_aprovada(v) is True
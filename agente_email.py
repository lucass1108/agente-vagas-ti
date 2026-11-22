#!/usr/bin/env python3
"""Mini-Agente de Email - Lê ultimas_vagas.json e envia email HTML."""
import sys, json, os
sys.path.insert(0, ".")
from vagas_agent import monta_html, envia_email, BASE
from pathlib import Path

def main():
    print("=" * 50)
    print("  Mini-Agente: EMAIL")
    print("=" * 50)
    vagas_file = BASE / "ultimas_vagas.json"
    if not vagas_file.exists():
        print("ERRO: ultimas_vagas.json não encontrado. Rode agente_busca.py primeiro.")
        sys.exit(1)
    vagas = json.loads(vagas_file.read_text(encoding="utf-8"))
    if not vagas:
        print("ERRO: Nenhuma vaga no arquivo.")
        sys.exit(1)
    print(f"Carregadas {len(vagas)} vagas de {vagas_file}")
    html = monta_html(vagas)
    assunto = f"Vagas TI - {__import__('datetime').datetime.now():%d/%m/%Y} - {len(vagas)} vagas"
    envia_email(html, assunto)
    print("Email enviado com sucesso!")

if __name__ == "__main__":
    main()

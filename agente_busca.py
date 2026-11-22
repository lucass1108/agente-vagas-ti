#!/usr/bin/env python3
"""Mini-Agente de Busca - Busca vagas de TI e salva em ultimas_vagas.json."""
import sys
sys.path.insert(0, ".")
from vagas_agent import coletar, monta_html, BASE
import json

def main():
    print("=" * 50)
    print("  Mini-Agente: BUSCA")
    print("=" * 50)
    vagas, hist, stats = coletar()
    if not vagas:
        print("ERRO: Nenhuma vaga encontrada.")
        sys.exit(1)
    # Salva ultimas_vagas.json
    out = BASE / "ultimas_vagas.json"
    out.write_text(json.dumps(vagas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(vagas)} vagas salvas em: {out}")
    print(f"Top: {sum(v['score'] >= 60 for v in vagas)} | Médias: {sum(40 <= v['score'] < 60 for v in vagas)}")
    print(f"Fontes: {stats}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Mini-Agente de Entrevista - Gera prep de entrevista para uma vaga."""
import sys
sys.path.insert(0, ".")
from vagas_agent import generate_interview_prep

def main():
    if len(sys.argv) < 2:
        print("Uso: python agente_entrevista.py \"Nome da vaga\"")
        sys.exit(1)
    vaga = " ".join(sys.argv[1:])
    print("=" * 50)
    print("  Mini-Agente: ENTREVISTA")
    print("=" * 50)
    generate_interview_prep(vaga)

if __name__ == "__main__":
    main()

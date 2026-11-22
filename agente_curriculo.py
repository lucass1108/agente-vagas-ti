#!/usr/bin/env python3
"""Mini-Agente de Curriculo - Gera curriculo personalizado para uma vaga."""
import sys
sys.path.insert(0, ".")
from vagas_agent import generate_tailored_resume

def main():
    if len(sys.argv) < 2:
        print("Uso: python agente_curriculo.py \"Nome da vaga\"")
        sys.exit(1)
    vaga = " ".join(sys.argv[1:])
    print("=" * 50)
    print("  Mini-Agente: CURRICULO")
    print("=" * 50)
    generate_tailored_resume(vaga)

if __name__ == "__main__":
    main()

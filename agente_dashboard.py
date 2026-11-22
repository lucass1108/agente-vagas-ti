#!/usr/bin/env python3
"""Mini-Agente de Dashboard - Gera dashboard Obsidian Base."""
import sys
sys.path.insert(0, ".")
from vagas_agent import generate_dashboard

def main():
    print("=" * 50)
    print("  Mini-Agente: DASHBOARD")
    print("=" * 50)
    generate_dashboard()

if __name__ == "__main__":
    main()

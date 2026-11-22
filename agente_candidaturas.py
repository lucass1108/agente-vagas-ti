#!/usr/bin/env python3
"""Mini-Agente de Candidaturas - Gerencia candidaturas de vagas."""
import sys, argparse
sys.path.insert(0, ".")
from vagas_agent import (load_applications, track_application, get_application_stats,
                          list_applications, get_followup_reminders, APPLICATION_STATUSES)

def main():
    ap = argparse.ArgumentParser(description="Mini-Agente: Candidaturas")
    ap.add_argument("--listar", action="store_true", help="Listar candidaturas")
    ap.add_argument("--stats", action="store_true", help="Estatísticas")
    ap.add_argument("--followup", action="store_true", help="Lembretes de follow-up")
    ap.add_argument("--registrar", type=str, help="Registrar candidatura (título da vaga)")
    ap.add_argument("--status", type=str, default="candidatado", choices=list(APPLICATION_STATUSES.keys()))
    ap.add_argument("--nota", type=str, default="", help="Notas")
    ap.add_argument("--empresa", type=str, default="", help="Empresa")
    ap.add_argument("--link", type=str, default="", help="Link da vaga")
    ap.add_argument("--score", type=int, default=0, help="Score")
    args = ap.parse_args()

    print("=" * 50)
    print("  Mini-Agente: CANDIDATURAS")
    print("=" * 50)

    if args.registrar:
        track_application(title=args.registrar, status=args.status, notes=args.nota,
                          link=args.link, score=args.score, empresa=args.empresa)
    elif args.followup:
        reminders = get_followup_reminders()
        if not reminders:
            print("Nenhum follow-up pendente!")
        else:
            print(f"{len(reminders)} follow-ups pendentes:")
            for app, days in reminders:
                print(f"  - {app['vaga']} ({days} dias sem resposta)")
    elif args.stats:
        s = get_application_stats()
        print(f"Total: {s['total']} | Resposta: {s['taxa_resposta']}% | Entrevista: {s['taxa_entrevista']}%")
        for k, info in APPLICATION_STATUSES.items():
            if s.get(k, 0) > 0:
                print(f"  {info['icon']} {info['label']}: {s[k]}")
    else:
        list_applications()

if __name__ == "__main__":
    main()

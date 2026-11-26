import subprocess, json, time
from pathlib import Path

BASE = Path(__file__).parent
RELATORIO = BASE / "status_agente.md"

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        return (r.stdout.strip() or r.stderr.strip())
    except Exception as e:
        return f"ERRO: {e}"

def main():
    linhas = ["# Status do Agente — Agente Vagas TI", f"Gerado em: {time.strftime('%Y-%m-%d %H:%M')}", ""]

    linhas.append("## Git")
    linhas.append(f"- Branch: {run('git branch --show-current')}")
    linhas.append(f"- Último commit: {run('git log -1 --oneline')}")
    linhas.append(f"- Status: {run('git status --short') or 'limpo'}")

    linhas.append("\n## Testes")
    out = run("python -m pytest -q 2>&1")
    linhas.append(out.splitlines()[-1] if "passed" in out else out[:200])

    linhas.append("\n## Arquivos do projeto")
    for f in ["vagas_agent.py", "streamlit_app.py", "README.md", "requirements.txt", "agente_linkedin.py", "agente_linkedin_full.py"]:
        p = BASE / f
        linhas.append(f"- {f}: {'✅' if p.exists() else '❌'} ({p.stat().st_size if p.exists() else 0} bytes)")

    linhas.append("\n## Vagas (última execução)")
    vf = BASE / "ultimas_vagas.json"
    if vf.exists():
        try:
            vagas = json.loads(vf.read_text(encoding="utf-8"))
            linhas.append(f"- Total: {len(vagas)}")
            linhas.append(f"- Top (≥60): {sum(v.get('score',0) >= 60 for v in vagas)}")
        except Exception as e:
            linhas.append(f"- Erro: {e}")
    else:
        linhas.append("- ultimas_vagas.json não encontrado")

    linhas.append("\n## Pendências")
    linhas.append("- [ ] Autenticar gh CLI (descrição, topics, release, pin)")
    linhas.append("- [ ] Deploy do FinanceTracker (Render/Railway)")
    linhas.append("- [ ] Criar repo de perfil GitHub (lucass1108/lucass1108)")
    linhas.append("- [ ] Post no LinkedIn")

    RELATORIO.write_text("\n".join(linhas), encoding="utf-8")
    print(RELATORIO.read_text(encoding="utf-8"))

if __name__ == "__main__":
    main()
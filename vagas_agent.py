#!/usr/bin/env python3
"""Agente Vagas TI v5.0 - busca (Gupy/Adzuna), score, historico e email HTML."""
import os, sys, json, re, smtplib, argparse
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from pathlib import Path

import requests

BASE = Path(__file__).parent
HIST_FILE = BASE / "historico_vagas.json"
OUT_FILE = BASE / "ultimas_vagas.json"
REPO_URL = "https://github.com/lucass1108/agente-vagas-ti"

EMAIL_USER = os.getenv("EMAIL_USER", "lucasbarbosapedro1108@gmail.com")
EMAIL_TO = os.getenv("EMAIL_TO", EMAIL_USER)
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
ADZUNA_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_KEY = os.getenv("ADZUNA_APP_KEY", "")

# ---------- PERFIL (embutido) ----------
PERFIL = {
    "cidades": ["são paulo", "sao paulo", "taboão da serra", "taboao da serra",
                "osasco", "embu", "remoto", "home office", "sp"],
    "stack": {
        "python": 8, "sql": 6, "flask": 4, "mysql": 4, "git": 3, "node": 3,
        "javascript": 3, "html": 2, "css": 1, "dados": 4, "data": 4,
        "suporte": 3, "backend": 4, "back-end": 4, "desenvolvimento": 3,
        "desenvolvedor": 3, "sistemas": 2, "api": 2, "automação": 3,
    },
    "nivel": ["estágio", "estagio", "estagiário", "estagiario", "jovem aprendiz",
              "aprendiz", "trainee", "júnior", "junior"],
    "ti": ["ti", "tecnologia", "software", "desenvolv", "sistemas", "dados",
           "programa", "suporte", "analista", "dev", "qa", "infra"],
    "evitar": ["sênior", "senior", "pleno", "especialista", "líder", "lider",
               "coordenador", "gerente", "arquiteto", "staff", "tech lead"],
}
TERMOS_BUSCA = [
    "estágio desenvolvimento", "estágio python", "estágio ti", "estágio dados",
    "estágio suporte ti", "jovem aprendiz ti", "jovem aprendiz tecnologia",
    "estágio backend", "estágio sistemas",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (AgenteVagasTI/5.0)"}
TOP_MIN, MEDIA_MIN = 60, 40


# ---------- FONTES ----------
def buscar_bing(termo):
    vagas = []
    try:
        from urllib.parse import quote_plus
        from bs4 import BeautifulSoup
        url = f"https://www.bing.com/search?q={quote_plus(termo + ' site:gupy.io OR site:vagas.com.br OR site:indeed.com.br')}"
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for result in soup.select("li.b_algo"):
            title_el = result.select_one("h2 a")
            snippet_el = result.select_one(".b_caption p")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link = title_el.get("href", "")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            combined = (title + " " + snippet).lower()
            ti_kw = ["ti", "tecnologia", "suporte", "desenvolvimento", "dados", "sistemas",
                     "informática", "informatica", "help desk", "analista", "dev", "software",
                     "python", "sql", "estágio", "estagio", "aprendiz", "trainee", "jovem aprendiz"]
            if not any(kw in combined for kw in ti_kw):
                continue
            other = ["rio de janeiro", "curitiba", "porto alegre", "belo horizonte", "salvador",
                     "fortaleza", "recife", "brasília", "manaus", "florianópolis"]
            if any(c in combined for c in other):
                continue
            vagas.append({
                "titulo": title,
                "empresa": "",
                "cidade": "São Paulo",
                "url": link,
                "tipo": "",
                "remoto": "remoto" in combined or "home office" in combined,
                "descricao": snippet,
                "data": "",
                "fonte": "Bing",
            })
    except Exception as e:
        print(f"[aviso] Bing '{termo}': {e}")
    return vagas


def buscar_adzuna(termo):
    if not (ADZUNA_ID and ADZUNA_KEY):
        return []
    vagas = []
    try:
        r = requests.get(
            "https://api.adzuna.com/v1/api/jobs/br/search/1",
            params={"app_id": ADZUNA_ID, "app_key": ADZUNA_KEY, "what": termo,
                    "where": "São Paulo", "results_per_page": 30,
                    "sort_by": "date"},
            headers=HEADERS, timeout=25,
        )
        r.raise_for_status()
        for j in r.json().get("results", []):
            vagas.append({
                "titulo": (j.get("title") or "").strip(),
                "empresa": ((j.get("company") or {}).get("display_name") or "").strip(),
                "cidade": ((j.get("location") or {}).get("display_name") or ""),
                "url": j.get("redirect_url") or "",
                "tipo": "",
                "remoto": False,
                "descricao": j.get("description") or "",
                "data": j.get("created") or "",
                "fonte": "Adzuna",
            })
    except Exception as e:
        print(f"[aviso] Adzuna '{termo}': {e}")
    return vagas


# ---------- VALIDAÇÃO / SCORE ----------
def valida(v):
    return (len(v["titulo"]) > 5 and v["url"].startswith("http")
            and not v["titulo"].isdigit())


def dias_desde(data_iso):
    try:
        d = datetime.fromisoformat(data_iso.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).days
    except Exception:
        return None


def calcula_score(v):
    titulo = v["titulo"].lower()
    texto = f"{titulo} {re.sub(r'<[^>]+>', ' ', v['descricao']).lower()}"
    local = f"{v['cidade']} {titulo}".lower()
    score, motivos = 0, []

    if any(n in titulo for n in PERFIL["nivel"]) or any(
            t in v["tipo"] for t in ("intern", "apprentice", "trainee")):
        score += 25; motivos.append("nível compatível")
    if any(t in titulo for t in PERFIL["ti"]):
        score += 20; motivos.append("área TI")

    stack = [(k, p) for k, p in PERFIL["stack"].items()
             if re.search(rf"\b{re.escape(k)}", texto)]
    pts = min(30, sum(p for _, p in stack))
    if pts:
        score += pts; motivos.append("stack: " + ", ".join(k for k, _ in stack[:4]))

    if v["remoto"] or any(c in local for c in PERFIL["cidades"]):
        score += 15; motivos.append("local ok")

    d = dias_desde(v["data"])
    if d is not None and d <= 7:
        score += 10; motivos.append("recente")

    if any(e in titulo for e in PERFIL["evitar"]):
        score -= 50; motivos.append("nível acima")

    v["score"] = max(0, min(100, score))
    v["motivos"] = motivos
    return v


# ---------- HISTÓRICO ----------
def carrega_hist():
    try:
        return set(json.loads(HIST_FILE.read_text(encoding="utf-8")))
    except Exception:
        return set()


def salva_hist(urls):
    HIST_FILE.write_text(json.dumps(sorted(urls)[-3000:], ensure_ascii=False),
                         encoding="utf-8")


# ---------- COLETA ----------
def coletar():
    bruto = []
    for t in TERMOS_BUSCA:
        bruto += buscar_bing(t)
        bruto += buscar_adzuna(t)
    vistos, unicas = set(), []
    for v in bruto:
        if valida(v) and v["url"] not in vistos:
            vistos.add(v["url"])
            unicas.append(calcula_score(v))
    unicas = [v for v in unicas if v["score"] >= 20]
    unicas.sort(key=lambda x: x["score"], reverse=True)

    hist = carrega_hist()
    for v in unicas:
        v["nova"] = v["url"] not in hist
    return unicas, hist


# ---------- EMAIL ----------
def cor(score):
    return "#16a34a" if score >= TOP_MIN else "#f59e0b" if score >= MEDIA_MIN else "#ef4444"


def monta_html(vagas, top_n=10):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    total = len(vagas)
    tops = sum(v["score"] >= TOP_MIN for v in vagas)
    medias = sum(MEDIA_MIN <= v["score"] < TOP_MIN for v in vagas)
    novas = sum(v["nova"] for v in vagas)

    def stat(n, label):
        return (f'<td align="center" style="padding:10px 14px;background:#f1f5f9;'
                f'border-radius:8px"><div style="font-size:22px;font-weight:700;'
                f'color:#4f46e5">{n}</div><div style="font-size:11px;color:#64748b">'
                f'{label}</div></td><td width="8"></td>')

    cards = ""
    for i, v in enumerate(vagas[:top_n], 1):
        c = cor(v["score"])
        badge_novo = ('<span style="background:#4f46e5;color:#fff;font-size:10px;'
                      'padding:2px 6px;border-radius:8px;margin-left:6px">NOVA</span>'
                      if v["nova"] else "")
        meta = " · ".join(x for x in [v["empresa"], v["cidade"], v["fonte"]] if x)
        mot = escape(" • ".join(v["motivos"])) or "—"
        cards += f'''
<tr><td style="padding:6px 0">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;
border-left:4px solid {c};border-radius:8px"><tr><td style="padding:12px 14px">
<div style="font-size:15px;font-weight:700;color:#0f172a">{i}. {escape(v["titulo"])}{badge_novo}</div>
<div style="font-size:12px;color:#64748b;margin:3px 0">{escape(meta)}</div>
<div style="font-size:12px;color:#475569;margin-bottom:6px">{mot}</div>
<span style="background:{c};color:#fff;font-size:12px;font-weight:700;
padding:3px 10px;border-radius:12px">{v["score"]}/100</span>
&nbsp;<a href="{escape(v["url"])}" style="color:#4f46e5;font-size:13px;
text-decoration:none;font-weight:600">Ver vaga →</a>
</td></tr></table></td></tr>'''

    return f'''<!DOCTYPE html><html><body style="margin:0;background:#e2e8f0;
font-family:Arial,Helvetica,sans-serif"><table width="100%" cellpadding="0"
cellspacing="0"><tr><td align="center" style="padding:16px">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;
background:#fff;border-radius:12px;overflow:hidden">
<tr><td align="center" style="background:#4f46e5;padding:24px;color:#fff">
<div style="font-size:22px;font-weight:700">Vagas TI - Lucas</div>
<div style="font-size:12px;opacity:.9;margin-top:4px">{agora} | {total} vagas | {novas} novas</div>
</td></tr>
<tr><td style="padding:18px"><table cellpadding="0" cellspacing="0"><tr>
{stat(total, "Total")}{stat(tops, f"Top ({TOP_MIN}+)")}{stat(medias, "Médias")}{stat(novas, "Novas")}
</tr></table></td></tr>
<tr><td style="padding:0 18px"><div style="font-size:16px;font-weight:700;color:#0f172a;
border-bottom:2px solid #4f46e5;padding-bottom:6px;margin-bottom:6px">Top {min(top_n, total)} vagas</div>
<table width="100%" cellpadding="0" cellspacing="0">{cards}</table></td></tr>
<tr><td align="center" style="padding:20px"><a href="{REPO_URL}"
style="background:#4f46e5;color:#ffffff;text-decoration:none;font-weight:700;
padding:12px 24px;border-radius:8px;display:inline-block">Ver todas no GitHub</a></td></tr>
<tr><td align="center" style="padding:0 18px 18px;font-size:11px;color:#94a3b8">
Agente Vagas TI v5.0 · gerado automaticamente</td></tr>
</table></td></tr></table></body></html>'''


def envia_email(html, assunto):
    if not EMAIL_PASSWORD:
        sys.exit("EMAIL_PASSWORD não definido.")
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = assunto, EMAIL_USER, EMAIL_TO
    msg.attach(MIMEText("Abra este email em um cliente com suporte a HTML.", "plain"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_USER, EMAIL_PASSWORD)
        s.sendmail(EMAIL_USER, [EMAIL_TO], msg.as_string())
    print("Email enviado.")


# ---------- OBSIDIAN NOTE ----------
def gera_nota_obsidian(vagas):
    """Gera nota markdown para o Obsidian."""
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    top = [v for v in vagas if v["score"] >= TOP_MIN]
    mid = [v for v in vagas if MEDIA_MIN <= v["score"] < TOP_MIN]
    low = [v for v in vagas if v["score"] < MEDIA_MIN]

    lines = [
        "---",
        "tags: [vagas, ti, estagio, jovem-aprendiz]",
        f"updated: {datetime.now().strftime('%Y-%m-%d')}",
        f"total_vagas: {len(vagas)}",
        f"novas: {sum(v['nova'] for v in vagas)}",
        "---",
        "",
        "# Vagas TI",
        f"> Relatório gerado em {agora} · Agente v5.0",
        f"> Total: {len(vagas)} vagas · Novas: {sum(v['nova'] for v in vagas)} · Top: {len(top)} · Médias: {len(mid)}",
        "",
    ]

    novas = [v for v in vagas if v["nova"]]
    if novas:
        lines += ["## 🆕 Novas desde a última execução", "",
                  "| # | Vaga | Score | Empresa | Link |", "|---|---|---|---|---|"]
        for i, v in enumerate(sorted(novas, key=lambda x: x["score"], reverse=True), 1):
            lines.append(f"| {i} | {v['titulo'][:50]} | {v['score']} | {v['empresa'][:20]} | [ver]({v['url']}) |")
        lines.append("")

    lines += ["## 🟢 Top Matches (score ≥ 60)", "",
              "| # | Vaga | Score | Empresa | Cidade | Link |", "|---|---|---|---|---|---|"]
    for i, v in enumerate(top, 1):
        novo = " 🆕" if v["nova"] else ""
        lines.append(f"| {i} | {v['titulo'][:50]}{novo} | {v['score']} | {v['empresa'][:20]} | {v['cidade'][:20]} | [ver]({v['url']}) |")

    lines += ["", "### Detalhes (Top)", ""]
    for i, v in enumerate(top, 1):
        novo = " 🆕 NOVA" if v["nova"] else ""
        mot = " • ".join(v["motivos"]) or "—"
        lines += [f"#### {i}. {v['titulo']}{novo}",
                  f"- **Score:** {v['score']}/100", f"- **Empresa:** {v['empresa']}",
                  f"- **Cidade:** {v['cidade']}", f"- **Fonte:** {v['fonte']}",
                  f"- **Motivos:** {mot}", f"- **Link:** {v['url']}", ""]

    if mid:
        lines += ["## 🟡 Matches médios (score 40-59)", "",
                  "| # | Vaga | Score | Empresa | Link |", "|---|---|---|---|---|"]
        for i, v in enumerate(mid, 1):
            lines.append(f"| {i} | {v['titulo'][:50]} | {v['score']} | {v['empresa'][:20]} | [ver]({v['url']}) |")

    lines += ["", "---", f"> Total: {len(vagas)} · Novas: {sum(v['nova'] for v in vagas)} · Top: {len(top)} · Médias: {len(mid)}",
              "> Para rodar: `python vagas_agent.py --email`"]

    return "\n".join(lines)


# ---------- FUNÇÕES LEGADAS (candidaturas, entrevista, etc.) ----------
import json as _json
from pathlib import Path as _Path

_VAULT = _Path(os.environ.get("VAULT_PATH", r"C:\Users\Pichau\Downloads\Nova pasta\Estudos TI"))
_CAND_FILE = _VAULT / "candidaturas.json"

def load_applications():
    if _CAND_FILE.exists():
        try:
            return _json.loads(_CAND_FILE.read_text(encoding="utf-8")).get("candidaturas", [])
        except Exception:
            return []
    return []

def save_applications(apps):
    _CAND_FILE.write_text(_json.dumps({"candidaturas": apps}, ensure_ascii=False, indent=2), encoding="utf-8")

def find_application(title):
    apps = load_applications()
    title_lower = title.lower().strip()
    for app in apps:
        if title_lower in app["vaga"].lower() or app["vaga"].lower() in title_lower:
            return app
    return None

APPLICATION_STATUSES = {
    "nao_candidatado": {"label": "Não candidatado", "icon": "⬜"},
    "candidatado": {"label": "Candidatado", "icon": "🟦"},
    "em_analise": {"label": "Em análise", "icon": "🟨"},
    "entrevista": {"label": "Entrevista", "icon": "🟩"},
    "rejeitado": {"label": "Não selecionado", "icon": "🔴"},
    "aprovado": {"label": "Aprovado!", "icon": "🟢"},
}

def track_application(title, status="candidatado", notes="", link="", score=0, empresa="", proximo_passo=""):
    apps = load_applications()
    existing = find_application(title)
    if existing:
        existing["status"] = status
        existing["notas"] = notes if notes else existing.get("notas", "")
        existing["data_atualizacao"] = datetime.now().isoformat()
        if link: existing["link"] = link
        if empresa: existing["empresa"] = empresa
        if proximo_passo: existing["proximo_passo"] = proximo_passo
        print(f"[OK] Atualizada: {title} → {APPLICATION_STATUSES[status]['label']}")
    else:
        new_app = {
            "vaga": title, "empresa": empresa or "N/A", "link": link or "",
            "score": score, "status": status,
            "data_candidatura": datetime.now().strftime("%Y-%m-%d"),
            "data_atualizacao": datetime.now().isoformat(),
            "notas": notes or "", "proximo_passo": proximo_passo or "",
        }
        apps.append(new_app)
        print(f"[OK] Registrada: {title} → {APPLICATION_STATUSES[status]['label']}")
    save_applications(apps)

def get_application_stats():
    apps = load_applications()
    stats = {s: 0 for s in APPLICATION_STATUSES}
    for app in apps:
        st = app.get("status", "nao_candidatado")
        if st in stats: stats[st] += 1
    stats["total"] = len(apps)
    responded = sum(stats.get(s, 0) for s in ["em_analise", "entrevista", "rejeitado", "aprovado"])
    stats["taxa_resposta"] = round((responded / stats["total"] * 100), 1) if stats["total"] > 0 else 0
    stats["taxa_entrevista"] = round((stats.get("entrevista", 0) + stats.get("aprovado", 0)) / stats["total"] * 100, 1) if stats["total"] > 0 else 0
    return stats

def list_applications():
    apps = load_applications()
    if not apps:
        print("Nenhuma candidatura registrada.")
        return
    print("\n" + "=" * 70)
    print("  CANDIDATURAS")
    print("=" * 70)
    for i, app in enumerate(apps, 1):
        st = APPLICATION_STATUSES.get(app["status"], APPLICATION_STATUSES["nao_candidatado"])
        print(f"\n  {i}. {st['icon']} {app['vaga']}")
        print(f"     Empresa: {app.get('empresa', 'N/A')} | Status: {st['label']} | Data: {app.get('data_candidatura', 'N/A')}")
        if app.get("notas"): print(f"     Notas: {app['notas']}")
        if app.get("link"): print(f"     Link: {app['link']}")
    print("\n" + "=" * 70)
    stats = get_application_stats()
    print(f"  Total: {stats['total']} | Resposta: {stats['taxa_resposta']}% | Entrevista: {stats['taxa_entrevista']}%")

def get_followup_reminders():
    apps = load_applications()
    reminders = []
    now = datetime.now()
    for app in apps:
        if app["status"] in ("candidatado", "em_analise"):
            try:
                data = datetime.fromisoformat(app.get("data_candidatura", app.get("data_atualizacao", "")))
                days = (now - data).days
                if days >= 7:
                    reminders.append((app, days))
            except (ValueError, TypeError):
                pass
    return reminders

def generate_interview_prep(vaga_title):
    app = None
    for a in load_applications():
        if vaga_title.lower() in a["vaga"].lower():
            app = a
            break
    vaga = app["vaga"] if app else vaga_title
    empresa = app.get("empresa", "N/A") if app else "N/A"
    lines = [f"# Prep de Entrevista — {vaga}", f"> Empresa: {empresa}", "",
             "## Perguntas gerais",
             "- Fale sobre você.", "- Por que esta empresa?", "- Pontos fortes/fracos?",
             "- Onde se vê em 5 anos?", "- Por que TI?",
             "", "## Perguntas técnicas",
             "- Diferença frontend/backend?", "- O que é BD relacional?",
             "- Como funciona Git?", "- O que é API REST?", "- SQL: SELECT, INSERT, UPDATE, DELETE?",
             "- O que é Flask?", "- Como resolver problema de rede?",
             "", "## Perguntas comportamentais",
             "- Desafio superado?", "- Prazos apertados?", "- Trabalho em equipe?",
             "- Priorização de tarefas?", "- O que faz quando não sabe?",
             "", "## Dicas", "- Pesquise a empresa", "- Use técnica STAR",
             "- Tenha perguntas para o entrevistador", "- Chegue 10 min antes",
             "", "---", "> Gerado pelo Agente Vagas TI v5.0"]
    content = "\n".join(lines)
    filepath = _VAULT / f"Entrevista - {vaga[:40]}.md"
    filepath.write_text(content, encoding="utf-8")
    print(f"[OK] Prep de entrevista salvo em: {filepath}")
    print(content)
    return content

def generate_tailored_resume(vaga_title):
    app = None
    for a in load_applications():
        if vaga_title.lower() in a["vaga"].lower():
            app = a
            break
    vaga = app["vaga"] if app else vaga_title
    empresa = app.get("empresa", "N/A") if app else "N/A"
    score = app.get("score", 0) if app else 0
    lines = [f"# Currículo Personalizado — {vaga}",
             f"> Empresa: {empresa} | Score: {score}/100", "",
             "## Skills destacadas", "- Python, SQL, Flask, MySQL, Git, HTML/CSS",
             "", "## Sugestões", "- Destaque projetos do GitHub (FinanceTracker, BrutalFit)",
             "- Mencione medalha CUCO/USP", "- Enfatize vontade de aprender",
             "", "## Prompt para IA",
             f"Adapte meu currículo para a vaga de {vaga} na {empresa}.",
             "Meu perfil: estudante de ADS 2º sem, Python/SQL/Flask/MySQL,",
             "projetos FinanceTracker e BrutalFit no GitHub, experiência em backoffice Sercom/Claro.",
             "Diferenciais: medalhista CUCO/USP, OBMEP, OMASP.",
             "", "---", "> Gerado pelo Agente Vagas TI v5.0"]
    content = "\n".join(lines)
    filepath = _VAULT / f"Curriculo - {vaga[:40]}.md"
    filepath.write_text(content, encoding="utf-8")
    print(f"[OK] Currículo personalizado salvo em: {filepath}")
    print(content)
    return content

def generate_dashboard():
    content = '''filters:
  and:
    - file.hasTag("vaga")
formulas:
  score_label: 'if(score >= 60, "Top", if(score >= 40, "Medio", "Baixo"))'
views:
  - type: table
    name: "Todas as Vagas"
    sort:
      - property: score
        direction: DESC
  - type: table
    name: "Top Matches"
    filters:
      and:
        - score >= 60
'''
    filepath = _VAULT / "Vagas Dashboard.base"
    filepath.write_text(content, encoding="utf-8")
    print(f"[OK] Dashboard salvo em: {filepath}")

def show_analytics():
    apps = load_applications()
    print("\n" + "=" * 60)
    print("  ANALYTICS")
    print("=" * 60)
    stats = get_application_stats()
    print(f"  Candidaturas: {stats['total']}")
    print(f"  Taxa de resposta: {stats['taxa_resposta']}%")
    print(f"  Taxa de entrevista: {stats['taxa_entrevista']}%")
    for st_key, st_info in APPLICATION_STATUSES.items():
        if stats.get(st_key, 0) > 0:
            print(f"  {st_info['icon']} {st_info['label']}: {stats[st_key]}")
    print("=" * 60)

def send_telegram(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("[INFO] Telegram nao configurado.")
        return
    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        print("[OK] Telegram enviado!")
    except Exception as e:
        print(f"[ERRO] Telegram: {e}")


# ---------- SCORE WRAPPER (para Streamlit) ----------
def score_job(vaga):
    """Wrapper: calcula score de uma vaga (dict com titulo, descricao, etc.)"""
    if isinstance(vaga, dict) and "titulo" in vaga:
        return calcula_score(vaga)["score"]
    # Formato antigo (title, description)
    v = {"titulo": vaga.get("title", ""), "descricao": vaga.get("description", ""),
         "cidade": "", "url": vaga.get("link", ""), "tipo": "", "remoto": False,
         "empresa": "", "data": "", "fonte": vaga.get("source", "")}
    return calcula_score(v)["score"]

def score_job_generic(job, skills):
    """Scoring generico baseado em skills do curriculo."""
    text = (job.get("title", job.get("titulo", "")) + " " + job.get("description", job.get("descricao", ""))).lower()
    score = 0
    for skill in skills:
        if skill.lower() in text:
            score += 8
    score = min(score, 40)
    ti_kw = ["ti", "tecnologia", "suporte", "desenvolvimento", "dados", "sistemas"]
    score += min(sum(1 for kw in ti_kw if kw in text) * 4, 20)
    level_kw = ["jovem aprendiz", "estágio", "estagiário", "aprendiz", "trainee", "estagio"]
    if any(kw in text for kw in level_kw):
        score += 20
    if "são paulo" in text or "sao paulo" in text or "sp" in text:
        score += 10
    elif "remoto" in text or "híbrido" in text:
        score += 8
    other = ["rio de janeiro", "curitiba", "porto alegre", "belo horizonte"]
    if any(c in text for c in other):
        score -= 30
    return max(0, min(100, score))

def search_jobs(skills, area=""):
    """Busca vagas (usada pelo Streamlit)."""
    # Busca via Gupy e Adzuna
    queries = [area] if area and area != "Todas as vagas de TI" else TERMOS_BUSCA[:6]
    for skill in skills[:3]:
        queries.append(f"estágio {skill}")
    jobs = []
    seen = set()
    for q in queries:
        for v in buscar_gupy(q):
            if valida(v) and v["url"] not in seen:
                seen.add(v["url"])
                v = calcula_score(v)
                jobs.append({"title": v["titulo"], "link": v["url"],
                             "description": v["descricao"][:200], "source": v["fonte"],
                             "score": v["score"], "empresa": v["empresa"]})
        if ADZUNA_ID:
            for v in buscar_adzuna(q):
                if valida(v) and v["url"] not in seen:
                    seen.add(v["url"])
                    v = calcula_score(v)
                    jobs.append({"title": v["titulo"], "link": v["url"],
                                 "description": v["descricao"][:200], "source": v["fonte"],
                                 "score": v["score"], "empresa": v["empresa"]})
    jobs.sort(key=lambda j: j["score"], reverse=True)
    return jobs


# ---------- MAIN ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", action="store_true", help="busca e envia email")
    ap.add_argument("--dry-run", action="store_true", help="gera preview.html sem enviar")
    ap.add_argument("--telegram", action="store_true", help="envia via Telegram")
    ap.add_argument("--schedule", action="store_true", help="modo agendado (diario)")
    ap.add_argument("--candidatura", type=str, help="registrar candidatura")
    ap.add_argument("--status", type=str, default="candidatado", choices=list(APPLICATION_STATUSES.keys()))
    ap.add_argument("--nota", type=str, default="", help="notas")
    ap.add_argument("--empresa", type=str, default="", help="empresa")
    ap.add_argument("--link", type=str, default="", help="link da vaga")
    ap.add_argument("--score", type=int, default=0, help="score")
    ap.add_argument("--proximo-passo", type=str, default="", dest="proximo_passo")
    ap.add_argument("--listar", action="store_true", help="listar candidaturas")
    ap.add_argument("--stats", action="store_true", help="estatisticas")
    ap.add_argument("--entrevista", type=str, help="prep de entrevista")
    ap.add_argument("--curriculo", type=str, help="curriculo personalizado")
    ap.add_argument("--dashboard", action="store_true", help="gerar dashboard")
    ap.add_argument("--analytics", action="store_true", help="analytics completo")
    args = ap.parse_args()

    # Comandos que nao precisam de busca
    if args.listar:
        list_applications()
        return
    if args.stats:
        stats = get_application_stats()
        print(f"\nTotal: {stats['total']} | Resposta: {stats['taxa_resposta']}% | Entrevista: {stats['taxa_entrevista']}%")
        for st_key, st_info in APPLICATION_STATUSES.items():
            if stats.get(st_key, 0) > 0:
                print(f"  {st_info['icon']} {st_info['label']}: {stats[st_key]}")
        print()
        return
    if args.entrevista:
        generate_interview_prep(args.entrevista)
        return
    if args.curriculo:
        generate_tailored_resume(args.curriculo)
        return
    if args.dashboard:
        generate_dashboard()
        return
    if args.analytics:
        show_analytics()
        return
    if args.candidatura:
        track_application(title=args.candidatura, status=args.status, notes=args.nota,
                          link=args.link, score=args.score, empresa=args.empresa,
                          proximo_passo=args.proximo_passo)
        print("Rode 'python vagas_agent.py' para atualizar.")
        return

    # Busca de vagas
    print("=" * 50)
    print("  Agente de Vagas TI v5.0")
    print("=" * 50)
    vagas, hist = coletar()
    if not vagas:
        sys.exit("ERRO: nenhuma vaga valida encontrada (verifique fontes/parsers).")

    OUT_FILE.write_text(json.dumps(vagas, ensure_ascii=False, indent=2), encoding="utf-8")
    salva_hist(hist | {v["url"] for v in vagas})

    print(f"{len(vagas)} vagas | top: {sum(v['score'] >= TOP_MIN for v in vagas)}")
    for v in vagas[:5]:
        print(f"  {v['score']:>3} | {v['titulo']} | {v['empresa']}")

    # Gera nota Obsidian
    note_path = _VAULT / "Vagas TI - Lucas.md"
    note_path.write_text(gera_nota_obsidian(vagas), encoding="utf-8")
    print(f"Nota salva em: {note_path}")

    html = monta_html(vagas)
    assunto = f"Vagas TI - {datetime.now():%d/%m/%Y} - {len(vagas)} vagas"

    if args.dry_run:
        (BASE / "preview.html").write_text(html, encoding="utf-8")
        print("preview.html gerado.")
    elif args.email:
        envia_email(html, assunto)
    elif args.telegram:
        send_telegram(f"Vagas TI: {len(vagas)} vagas encontradas. Top: {vagas[0]['titulo'] if vagas else 'N/A'}")

    if args.schedule:
        print("Modo agendado: rodando a cada 24h")
        import time as _time
        while True:
            _time.sleep(86400)
            main()


if __name__ == "__main__":
    main()

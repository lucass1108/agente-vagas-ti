#!/usr/bin/env python3
"""Agente Vagas TI v6.2 - busca (Gupy/Adzuna/Bing), score, historico e email HTML."""
import os, sys, json, re, time, base64, smtplib, argparse, urllib.parse, urllib.request
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape, unescape
from pathlib import Path

import requests

BASE = Path(__file__).parent
HIST_FILE = BASE / "historico_vagas.json"
OUT_FILE = BASE / "ultimas_vagas.json"
REPO_URL = "https://github.com/lucass1108/agente-vagas-ti"
EM_ACTIONS = bool(os.getenv("GITHUB_ACTIONS"))

EMAIL_USER = os.getenv("EMAIL_USER", "lucasbarbosapedro1108@gmail.com")
EMAIL_TO = os.getenv("EMAIL_TO", EMAIL_USER)
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
ADZUNA_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_KEY = os.getenv("ADZUNA_APP_KEY", "")

_LOCAL = Path(r"C:\Users\Pichau\Downloads\Nova pasta\Estudos TI")
_VAULT = Path(os.environ.get("VAULT_PATH") or (_LOCAL if _LOCAL.exists() else BASE / "dados_locais"))
_VAULT.mkdir(parents=True, exist_ok=True)
_CAND_FILE = _VAULT / "candidaturas.json"

DEBUG = False
_debug_gupy_feito = False

# ---------- PERFIL (embutido: funciona no GitHub Actions) ----------
PERFIL = {
    "cidades": ["são paulo", "sao paulo", "taboão da serra", "taboao da serra",
                "osasco", "embu das artes", "embu", "barueri", "cotia",
                "carapicuíba", "itapecerica da serra", "sp"],
    "stack": {
        "python": 8, "sql": 6, "flask": 4, "mysql": 4, "git": 3, "node": 3,
        "javascript": 3, "html": 2, "css": 1, "dados": 4, "data": 4,
        "suporte": 3, "backend": 4, "back-end": 4, "desenvolvimento": 3,
        "desenvolvedor": 3, "sistemas": 2, "api": 2, "automação": 3,
    },
    # radicais: "estági" casa estágio/estágios; "estagi" casa estagio/estagiaria/estagiária
    "nivel": ["estági", "estagi", "jovem aprendiz", "aprendiz", "trainee", "júnior", "junior"],
    "ti": ["ti", "tecnologia", "software", "desenvolv", "sistemas", "dados",
           "programa", "suporte", "analista de", "dev", "qa", "infra", "informática",
           "informatica", "help desk", "redes", "cloud", "backend", "frontend"],
    "evitar": ["sênior", "senior", "pleno", "especialista", "líder", "lider",
               "coordenador", "gerente", "arquiteto", "staff", "tech lead"],
}
TERMOS_BUSCA = [
    "estágio desenvolvimento", "estágio python", "estágio ti", "estágio dados",
    "estágio suporte ti", "jovem aprendiz ti", "jovem aprendiz tecnologia",
    "estágio backend", "estágio sistemas",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (AgenteVagasTI/6.2)"}
TOP_MIN, MEDIA_MIN, SCORE_MIN = 60, 40, 30
APENAS_REGIAO = True          # descarta vagas fora da região (exceto remotas)
GUPY_URL = "https://portal.gupy.io/api/job-search/jobs"
GUPY_LIMIT = 50
GUPY_PAGINAS = 5
GUPY_ESTADOS = ("São Paulo", "")  # tenta filtrar por estado; se vier vazio, tenta sem filtro
# Bing: só aceita links que são vaga individual (não homepage de portal)
VAGA_URL_RE = re.compile(
    r"gupy\.io/(?:jobs?|job)/|vagas\.com\.br/vagas/v\d+|indeed\.com\.br/(?:viewjob|rc/clk)"
    r"|linkedin\.com/jobs/view|catho\.com\.br/vagas/|infojobs\.com\.br/vaga|99jobs\.com/.+/jobs/",
    re.I)


# ---------- UTILIDADES ----------
def limpa_html(s):
    return unescape(re.sub(r"<[^>]+>", " ", s or ""))


def _pat(termo):
    t = re.escape(termo)
    # termos curtos: palavra inteira; longos: início de palavra (radicais)
    return rf"(?<!\w){t}(?!\w)" if len(termo) <= 3 else rf"(?<!\w){t}"


def acha(termos, texto):
    return [t for t in termos if re.search(_pat(t), texto)]


def _g(d, *keys):
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return ""


def fmt_prazo(p):
    try:
        return datetime.strptime(p[:10], "%Y-%m-%d").strftime("%d/%m")
    except Exception:
        return ""


# ---------- FONTES ----------
def _gupy_get(termo, offset, estado):
    params = {"jobName": termo, "limit": GUPY_LIMIT, "offset": offset}
    if estado:
        params["state"] = estado
    r = requests.get(GUPY_URL, params=params, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return r.json().get("data") or []


def buscar_gupy(termo, paginas=GUPY_PAGINAS):
    vagas = []
    for estado in GUPY_ESTADOS:
        offset = 0
        for p in range(paginas):
            try:
                dados = _gupy_get(termo, offset, p and estado or estado)
            except Exception as e:
                print(f"[aviso] Gupy '{termo}': {e}")
                break
            if DEBUG and dados and p == 0 and not vagas:
                print(f"[debug] Gupy campos: {sorted(dados[0].keys())}")
                print(f"[debug] Gupy 1ª vaga: {json.dumps(dados[0], ensure_ascii=False)[:600]}")
            if not dados:
                break
            offset += len(dados)  # avança pelo que a API realmente devolveu
            for j in dados:
                tipo = str(_g(j, "type", "jobType", "job_type")).lower()
                if "talent_pool" in tipo:
                    continue
                cidade = ", ".join(str(x) for x in [j.get("city"), j.get("state")] if x)
                vagas.append({
                    "titulo": str(_g(j, "name", "title")).strip(),
                    "empresa": str(_g(j, "careerPageName", "companyName", "company_name", "company")).strip(),
                    "cidade": cidade,
                    "url": str(_g(j, "jobUrl", "applyUrl", "apply_url", "url")),
                    "tipo": tipo,
                    "remoto": "remote" in str(_g(j, "workplaceType", "workplace_type")).lower(),
                    "descricao": limpa_html(str(j.get("description") or "")),
                    "data": str(_g(j, "publishedDate", "published_date")),
                    "prazo": str(j.get("applicationDeadline") or "")[:10],
                    "fonte": "Gupy",
                })
            time.sleep(0.3)
        if vagas:
            break
    return vagas


def buscar_adzuna(termo):
    if not (ADZUNA_ID and ADZUNA_KEY):
        return []
    vagas = []
    try:
        r = requests.get(
            "https://api.adzuna.com/v1/api/jobs/br/search/1",
            params={"app_id": ADZUNA_ID, "app_key": ADZUNA_KEY, "what": termo,
                    "where": "São Paulo", "results_per_page": 30, "sort_by": "date"},
            headers=HEADERS, timeout=25)
        r.raise_for_status()
        for j in r.json().get("results", []):
            vagas.append({
                "titulo": (j.get("title") or "").strip(),
                "empresa": ((j.get("company") or {}).get("display_name") or "").strip(),
                "cidade": ((j.get("location") or {}).get("display_name") or ""),
                "url": j.get("redirect_url") or "",
                "tipo": "", "remoto": False,
                "descricao": limpa_html(j.get("description") or ""),
                "data": j.get("created") or "", "prazo": "",
                "fonte": "Adzuna",
            })
    except Exception as e:
        print(f"[aviso] Adzuna '{termo}': {e}")
    return vagas


def decode_bing_url(url):
    if "bing.com/ck" not in url:
        return url
    try:
        params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        u = params.get("u", [""])[0]
        if u.startswith("a1"):
            u = u[2:]
        u += "=" * (-len(u) % 4)
        dec = base64.urlsafe_b64decode(u).decode("utf-8")
        if dec.startswith("http"):
            return dec
    except Exception:
        pass
    return url


def buscar_bing(termo):
    vagas = []
    try:
        from bs4 import BeautifulSoup
        q = termo + " site:gupy.io OR site:vagas.com.br OR site:indeed.com.br"
        r = requests.get("https://www.bing.com/search?q=" + urllib.parse.quote_plus(q),
                         headers=HEADERS, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for res in soup.select("li.b_algo"):
            a = res.select_one("h2 a")
            if not a:
                continue
            link = decode_bing_url(a.get("href", ""))
            if not VAGA_URL_RE.search(link):
                continue  # descarta homepages e portais
            sn = res.select_one(".b_caption p")
            snippet = sn.get_text(strip=True) if sn else ""
            vagas.append({
                "titulo": a.get_text(strip=True), "empresa": "", "cidade": "",
                "url": link, "tipo": "",
                "remoto": bool(re.search(r"remoto|home office", (a.get_text() + snippet).lower())),
                "descricao": snippet, "data": "", "prazo": "", "fonte": "Bing",
            })
    except Exception as e:
        print(f"[aviso] Bing '{termo}': {e}")
    return vagas


def buscar_todas(termo):
    return buscar_gupy(termo) + buscar_adzuna(termo) + buscar_bing(termo)


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
    texto = f"{titulo} {v['descricao'].lower()}"
    cidade_nome = re.split(r"\s*[,\-]\s*", v["cidade"].lower())[0] if v["cidade"] else ""
    score, motivos = 0, []

    v["ti_ok"] = bool(acha(PERFIL["ti"], titulo))
    if acha(PERFIL["nivel"], titulo) or any(t in v["tipo"] for t in ("intern", "apprentic", "trainee")):
        score += 25; motivos.append("nível compatível")
    if v["ti_ok"]:
        score += 20; motivos.append("área TI")

    stack = [(k, p) for k, p in PERFIL["stack"].items() if re.search(_pat(k), texto)]
    pts = min(30, sum(p for _, p in stack))
    if pts:
        score += pts; motivos.append("stack: " + ", ".join(k for k, _ in stack[:4]))

    if v["remoto"] or acha(["remoto", "home office"], titulo):
        score += 15; motivos.append("remoto")
    elif cidade_nome and acha(PERFIL["cidades"], cidade_nome):
        score += 15; motivos.append("local ok")
    elif cidade_nome:
        score -= 20; motivos.append("fora da região")

    d = dias_desde(v["data"])
    if d is not None and d <= 7:
        score += 10; motivos.append("recente")

    if acha(PERFIL["evitar"], titulo):
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
    HIST_FILE.write_text(json.dumps(sorted(urls)[-3000:], ensure_ascii=False), encoding="utf-8")


# ---------- COLETA ----------
def coletar():
    bruto, stats = [], {}
    for t in TERMOS_BUSCA:
        for v in buscar_todas(t):
            stats[v["fonte"]] = stats.get(v["fonte"], 0) + 1
            bruto.append(v)
    hoje = datetime.now().strftime("%Y-%m-%d")
    vistos, chaves, unicas = set(), set(), []
    descartes = {"invalida/duplicada": 0, "fora da região": 0, "encerrada": 0, "não TI/score baixo": 0}
    for v in bruto:
        chave = (v["titulo"].lower(), v["empresa"].lower())
        if not valida(v) or v["url"] in vistos or (v["empresa"] and chave in chaves):
            descartes["invalida/duplicada"] += 1
            continue
        vistos.add(v["url"]); chaves.add(chave)
        v = calcula_score(v)
        if APENAS_REGIAO and "fora da região" in v["motivos"]:
            descartes["fora da região"] += 1
            continue
        if v.get("prazo") and v["prazo"] < hoje:
            descartes["encerrada"] += 1
            continue
        if not (v["ti_ok"] and v["score"] >= SCORE_MIN):
            descartes["não TI/score baixo"] += 1
            continue
        unicas.append(v)
    unicas.sort(key=lambda x: x["score"], reverse=True)
    hist = carrega_hist()
    for v in unicas:
        v["nova"] = v["url"] not in hist
    print(f"Bruto por fonte: {stats or 'nenhuma'} | aprovadas: {len(unicas)}")
    print(f"Descartadas: {descartes}")
    return unicas, hist, stats


# ---------- EMAIL ----------
def cor(score):
    return "#16a34a" if score >= TOP_MIN else "#f59e0b" if score >= MEDIA_MIN else "#ef4444"


def monta_html(vagas, stats=None, top_n=10):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    total = len(vagas)
    tops = sum(v["score"] >= TOP_MIN for v in vagas)
    medias = sum(MEDIA_MIN <= v["score"] < TOP_MIN for v in vagas)
    novas = sum(v["nova"] for v in vagas)
    fontes = " · ".join(f"{k} {n}" for k, n in (stats or {}).items()) or "—"

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
        prazo = fmt_prazo(v.get("prazo", ""))
        meta = " · ".join(x for x in [v["empresa"], v["cidade"], v["fonte"],
                                      f"inscrições até {prazo}" if prazo else ""] if x)
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
&nbsp;<a href="{v["url"]}" target="_blank" style="color:#4f46e5;font-size:13px;
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
Fontes: {escape(fontes)}<br>Agente Vagas TI v6.2 · gerado automaticamente</td></tr>
</table></td></tr></table></body></html>'''


def envia_email(html, assunto):
    if not EMAIL_PASSWORD:
        sys.exit("EMAIL_PASSWORD não definido.")
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = assunto, EMAIL_USER, EMAIL_TO
    msg.attach(MIMEText(f"Vagas TI - {datetime.now():%d/%m/%Y}\n\nAbra em um cliente com suporte a HTML.", "plain"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_USER, EMAIL_PASSWORD)
        s.sendmail(EMAIL_USER, [EMAIL_TO], msg.as_string())
    print("Email enviado.")


def send_telegram(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("[INFO] Telegram não configurado.")
        return
    try:
        data = json.dumps({"chat_id": chat_id, "text": msg}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                     data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        print("[OK] Telegram enviado!")
    except Exception as e:
        print(f"[ERRO] Telegram: {e}")


# ---------- OBSIDIAN NOTE (só uso local) ----------
def gera_nota_obsidian(vagas):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    top = [v for v in vagas if v["score"] >= TOP_MIN]
    mid = [v for v in vagas if MEDIA_MIN <= v["score"] < TOP_MIN]
    n_novas = sum(v["nova"] for v in vagas)
    lines = ["---", "tags: [vagas, ti, estagio, jovem-aprendiz]",
             f"updated: {datetime.now().strftime('%Y-%m-%d')}", f"total_vagas: {len(vagas)}",
             f"novas: {n_novas}", "---", "", "# Vagas TI",
             f"> Relatório gerado em {agora} · Agente v6.2",
             f"> Total: {len(vagas)} · Novas: {n_novas} · Top: {len(top)} · Médias: {len(mid)}", ""]

    def tabela(titulo, lista):
        out = [titulo, "", "| # | Vaga | Score | Empresa | Cidade | Até | Link |", "|---|---|---|---|---|---|---|"]
        for i, v in enumerate(lista, 1):
            novo = " 🆕" if v["nova"] else ""
            out.append(f"| {i} | {v['titulo'][:50]}{novo} | {v['score']} | {v['empresa'][:20]} | "
                       f"{v['cidade'][:20]} | {fmt_prazo(v.get('prazo', ''))} | [ver]({v['url']}) |")
        return out + [""]

    if top:
        lines += tabela("## 🟢 Top Matches (score ≥ 60)", top)
    if mid:
        lines += tabela("## 🟡 Matches médios (40-59)", mid)
    lines += ["---", "> Para rodar: `python vagas_agent.py --email`"]
    return "\n".join(lines)


# ---------- CANDIDATURAS / ENTREVISTA / CURRÍCULO (locais) ----------
APPLICATION_STATUSES = {
    "nao_candidatado": {"label": "Não candidatado", "icon": "⬜"},
    "candidatado": {"label": "Candidatado", "icon": "🟦"},
    "em_analise": {"label": "Em análise", "icon": "🟨"},
    "entrevista": {"label": "Entrevista", "icon": "🟩"},
    "rejeitado": {"label": "Não selecionado", "icon": "🔴"},
    "aprovado": {"label": "Aprovado!", "icon": "🟢"},
}


def load_applications():
    if _CAND_FILE.exists():
        try:
            return json.loads(_CAND_FILE.read_text(encoding="utf-8")).get("candidaturas", [])
        except Exception:
            return []
    return []


def save_applications(apps):
    _CAND_FILE.write_text(json.dumps({"candidaturas": apps}, ensure_ascii=False, indent=2), encoding="utf-8")


def find_application(title):
    t = title.lower().strip()
    for app in load_applications():
        if t in app["vaga"].lower() or app["vaga"].lower() in t:
            return app
    return None


def track_application(title, status="candidatado", notes="", link="", score=0, empresa="", proximo_passo=""):
    apps = load_applications()
    existing = next((a for a in apps if title.lower().strip() in a["vaga"].lower()
                     or a["vaga"].lower() in title.lower().strip()), None)
    if existing:
        existing["status"] = status
        existing["notas"] = notes or existing.get("notas", "")
        existing["data_atualizacao"] = datetime.now().isoformat()
        if link: existing["link"] = link
        if empresa: existing["empresa"] = empresa
        if proximo_passo: existing["proximo_passo"] = proximo_passo
        print(f"[OK] Atualizada: {title} → {APPLICATION_STATUSES[status]['label']}")
    else:
        apps.append({"vaga": title, "empresa": empresa or "N/A", "link": link or "",
                     "score": score, "status": status,
                     "data_candidatura": datetime.now().strftime("%Y-%m-%d"),
                     "data_atualizacao": datetime.now().isoformat(),
                     "notas": notes or "", "proximo_passo": proximo_passo or ""})
        print(f"[OK] Registrada: {title} → {APPLICATION_STATUSES[status]['label']}")
    save_applications(apps)


def get_application_stats():
    apps = load_applications()
    stats = {s: 0 for s in APPLICATION_STATUSES}
    for app in apps:
        st = app.get("status", "nao_candidatado")
        if st in stats:
            stats[st] += 1
    total = len(apps)
    stats["total"] = total
    resp = sum(stats[s] for s in ["em_analise", "entrevista", "rejeitado", "aprovado"])
    stats["taxa_resposta"] = round(resp / total * 100, 1) if total else 0
    stats["taxa_entrevista"] = round((stats["entrevista"] + stats["aprovado"]) / total * 100, 1) if total else 0
    return stats


def list_applications():
    apps = load_applications()
    if not apps:
        print("Nenhuma candidatura registrada.")
        return
    print("\n" + "=" * 70 + "\n  CANDIDATURAS\n" + "=" * 70)
    for i, app in enumerate(apps, 1):
        st = APPLICATION_STATUSES.get(app["status"], APPLICATION_STATUSES["nao_candidatado"])
        print(f"\n  {i}. {st['icon']} {app['vaga']}")
        print(f"     Empresa: {app.get('empresa', 'N/A')} | Status: {st['label']} | Data: {app.get('data_candidatura', 'N/A')}")
        if app.get("notas"): print(f"     Notas: {app['notas']}")
        if app.get("link"): print(f"     Link: {app['link']}")
    s = get_application_stats()
    print("\n" + "=" * 70)
    print(f"  Total: {s['total']} | Resposta: {s['taxa_resposta']}% | Entrevista: {s['taxa_entrevista']}%")


def get_followup_reminders():
    reminders, now = [], datetime.now()
    for app in load_applications():
        if app["status"] in ("candidatado", "em_analise"):
            try:
                d = datetime.fromisoformat(app.get("data_candidatura", app.get("data_atualizacao", "")))
                if (now - d).days >= 7:
                    reminders.append((app, (now - d).days))
            except (ValueError, TypeError):
                pass
    return reminders


def _acha_app(titulo):
    return next((a for a in load_applications() if titulo.lower() in a["vaga"].lower()), None)


def generate_interview_prep(vaga_title):
    app = _acha_app(vaga_title)
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
             "", "---", "> Gerado pelo Agente Vagas TI v6.2"]
    content = "\n".join(lines)
    _safe = re.sub(r"[^\w\s-]", "", vaga)[:40]
    p = _VAULT / f"Entrevista - {_safe}.md"
    p.write_text(content, encoding="utf-8")
    print(f"[OK] Prep de entrevista salvo em: {p}")
    print(content)
    return content


def generate_tailored_resume(vaga_title):
    app = _acha_app(vaga_title)
    vaga = app["vaga"] if app else vaga_title
    empresa = app.get("empresa", "N/A") if app else "N/A"
    score = app.get("score", 0) if app else 0
    lines = [f"# Currículo Personalizado — {vaga}", f"> Empresa: {empresa} | Score: {score}/100", "",
             "## Skills destacadas", "- Python, SQL, Flask, MySQL, Git, HTML/CSS", "",
             "## Sugestões", "- Destaque projetos do GitHub (FinanceTracker, BrutalFit)",
             "- Mencione medalha CUCO/USP", "- Enfatize vontade de aprender", "",
             "## Prompt para IA", f"Adapte meu currículo para a vaga de {vaga} na {empresa}.",
             "Meu perfil: estudante de ADS 2º sem, Python/SQL/Flask/MySQL,",
             "projetos FinanceTracker e BrutalFit no GitHub, experiência em backoffice.",
             "Diferenciais: medalhista CUCO/USP, OBMEP, OMASP.", "",
             "---", "> Gerado pelo Agente Vagas TI v6.2"]
    content = "\n".join(lines)
    _safe = re.sub(r"[^\w\s-]", "", vaga)[:40]
    p = _VAULT / f"Curriculo - {_safe}.md"
    p.write_text(content, encoding="utf-8")
    print(f"[OK] Currículo personalizado salvo em: {p}")
    print(content)
    return content


def generate_dashboard():
    content = '''filters:
  and:
    - file.hasTag("vagas")
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
    p = _VAULT / "Vagas Dashboard.base"
    p.write_text(content, encoding="utf-8")
    print(f"[OK] Dashboard salvo em: {p}")


def show_analytics():
    s = get_application_stats()
    print("\n" + "=" * 60 + "\n  ANALYTICS\n" + "=" * 60)
    print(f"  Candidaturas: {s['total']}")
    print(f"  Taxa de resposta: {s['taxa_resposta']}%")
    print(f"  Taxa de entrevista: {s['taxa_entrevista']}%")
    for k, info in APPLICATION_STATUSES.items():
        if s.get(k, 0) > 0:
            print(f"  {info['icon']} {info['label']}: {s[k]}")
    for app, dias in get_followup_reminders():
        print(f"  ⏰ Follow-up: {app['vaga']} ({dias} dias sem resposta)")
    print("=" * 60)


# ---------- COMPATIBILIDADE COM O STREAMLIT ----------
def score_job(vaga):
    if isinstance(vaga, dict) and "titulo" in vaga:
        return calcula_score(vaga)["score"]
    v = {"titulo": vaga.get("title", ""), "descricao": vaga.get("description", ""),
         "cidade": "", "url": vaga.get("link", ""), "tipo": "", "remoto": False,
         "empresa": "", "data": "", "prazo": "", "fonte": vaga.get("source", "")}
    return calcula_score(v)["score"]


def score_job_generic(job, skills):
    text = (job.get("title", job.get("titulo", "")) + " " + job.get("description", job.get("descricao", ""))).lower()
    score = min(sum(8 for s in skills if s.lower() and re.search(_pat(s.lower()), text)), 40)
    score += min(len(acha(PERFIL["ti"], text)) * 4, 20)
    if acha(PERFIL["nivel"], text):
        score += 20
    if acha(["são paulo", "sao paulo", "sp"], text):
        score += 10
    elif acha(["remoto", "híbrido", "hibrido"], text):
        score += 8
    if acha(["rio de janeiro", "curitiba", "porto alegre", "belo horizonte"], text):
        score -= 30
    return max(0, min(100, score))


def search_jobs(skills, area=""):
    queries = [area] if area and area != "Todas as vagas de TI" else TERMOS_BUSCA[:6]
    queries += [f"estágio {s}" for s in skills[:3]]
    hoje = datetime.now().strftime("%Y-%m-%d")
    jobs, seen = [], set()
    for q in queries:
        for v in buscar_todas(q):
            if valida(v) and v["url"] not in seen:
                seen.add(v["url"])
                if v.get("prazo") and v["prazo"] < hoje:
                    continue
                v = calcula_score(v)
                jobs.append({"title": v["titulo"], "link": v["url"], "description": v["descricao"][:200],
                             "source": v["fonte"], "score": v["score"], "empresa": v["empresa"],
                             "cidade": v["cidade"], "prazo": v.get("prazo", "")})
    jobs.sort(key=lambda j: j["score"], reverse=True)
    return jobs


# ---------- EXECUÇÃO ----------
def executar(args):
    print("=" * 50 + "\n  Agente de Vagas TI v6.2\n" + "=" * 50)
    vagas, hist, stats = coletar()
    if not vagas:
        print("ERRO: nenhuma vaga válida encontrada (verifique fontes/parsers).")
        return False

    OUT_FILE.write_text(json.dumps(vagas, ensure_ascii=False, indent=2), encoding="utf-8")
    salva_hist(hist | {v["url"] for v in vagas})

    print(f"{len(vagas)} vagas | top: {sum(v['score'] >= TOP_MIN for v in vagas)}")
    for v in vagas[:5]:
        print(f"  {v['score']:>3} | {v['titulo']} | {v['empresa']} | {v['cidade']} | até {fmt_prazo(v.get('prazo', '')) or '-'}")

    if not EM_ACTIONS:
        note = _VAULT / "Vagas TI - Lucas.md"
        note.write_text(gera_nota_obsidian(vagas), encoding="utf-8")
        print(f"Nota salva em: {note}")

    html = monta_html(vagas, stats)
    assunto = f"Vagas TI - {datetime.now():%d/%m/%Y} - {len(vagas)} vagas"
    if args.dry_run:
        (BASE / "preview.html").write_text(html, encoding="utf-8")
        print("preview.html gerado.")
    elif args.email:
        envia_email(html, assunto)
    if args.telegram:
        linhas = [f"Vagas TI: {len(vagas)} vagas ({sum(v['nova'] for v in vagas)} novas)"]
        linhas += [f"{v['score']} | {v['titulo']} | {v['url']}" for v in vagas[:5]]
        send_telegram("\n".join(linhas))
    return True


def main():
    global DEBUG
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", action="store_true", help="busca e envia email")
    ap.add_argument("--dry-run", action="store_true", help="gera preview.html sem enviar")
    ap.add_argument("--debug", action="store_true", help="mostra campos e estados brutos da Gupy")
    ap.add_argument("--telegram", action="store_true", help="envia resumo via Telegram")
    ap.add_argument("--schedule", action="store_true", help="modo agendado (a cada 24h)")
    ap.add_argument("--candidatura", type=str, help="registrar candidatura")
    ap.add_argument("--status", type=str, default="candidatado", choices=list(APPLICATION_STATUSES))
    ap.add_argument("--nota", type=str, default="")
    ap.add_argument("--empresa", type=str, default="")
    ap.add_argument("--link", type=str, default="")
    ap.add_argument("--score", type=int, default=0)
    ap.add_argument("--proximo-passo", type=str, default="", dest="proximo_passo")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--entrevista", type=str)
    ap.add_argument("--curriculo", type=str)
    ap.add_argument("--dashboard", action="store_true")
    ap.add_argument("--analytics", action="store_true")
    args = ap.parse_args()
    DEBUG = args.debug

    if args.listar:
        return list_applications()
    if args.stats or args.analytics:
        return show_analytics()
    if args.entrevista:
        generate_interview_prep(args.entrevista); return
    if args.curriculo:
        generate_tailored_resume(args.curriculo); return
    if args.dashboard:
        generate_dashboard(); return
    if args.candidatura:
        track_application(args.candidatura, args.status, args.nota, args.link,
                          args.score, args.empresa, args.proximo_passo)
        return

    ok = executar(args)
    if args.schedule:
        print("Modo agendado: rodando a cada 24h")
        while True:
            time.sleep(86400)
            executar(args)
    elif not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()

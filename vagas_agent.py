#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agente de Vagas TI - Lucas Barbosa Pedro (v2.0)
Busca vagas de Jovem Aprendiz / Estágio em TI compatíveis com o currículo
e gera um relatório no Obsidian. Opcionalmente envia por email e notifica no Windows.
"""

import os
import re
import sys
import json
import time
import smtplib
import schedule
import subprocess
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote_plus, urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Instale as dependências: pip install requests beautifulsoup4 schedule")
    sys.exit(1)

# ============================================================
# CONFIG
# ============================================================
CONFIG = {
    "vault_path": r"C:\Users\Pichau\Downloads\Nova pasta\Estudos TI",
    "note_name": "Vagas TI - Lucas.md",
    "history_file": "vagas_history.json",
    "email_enabled": True,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "email_from": "lucasbarbosapedro1108@gmail.com",
    "email_password": os.environ.get("EMAIL_PASSWORD", "afkg jkym lviw kvql"),
    "email_to": "lucasbarbosapedro1108@gmail.com",
    "toast_enabled": True,
    "max_retries": 3,
    "retry_delay": 2,
    "schedule_hours": 24,
}

# ============================================================
# PERFIL DO CANDIDATO
# ============================================================
PROFILE = {
    "name": "Lucas Barbosa Pedro",
    "skills": ["python", "sql", "html", "css", "flask", "mysql", "git", "github",
               "windows", "excel", "office", "redes", "linux", "atendimento",
               "backoffice", "suporte", "flask", "workbench"],
    "area_keywords": ["suporte", "dados", "desenvolvimento", "ti", "tecnologia",
                      "informática", "help desk", "infraestrutura", "programação",
                      "analista", "back-end", "frontend", "fullstack", "dev"],
    "level_keywords": ["jovem aprendiz", "estágio", "estagiário", "aprendiz",
                       "trainee"],
    "negative_keywords": ["experiência prévia em ti", "experiência em ti",
                          "inglês avançado", "inglês fluente", "3 anos",
                          "2 anos de experiência", "experiência comprovada"],
    "education": "Análise e Desenvolvimento de Sistemas (ADS)",
    "city": "Taboão da Serra",
}

# ============================================================
# FONTES DE BUSCA
# ============================================================
SEARCH_QUERIES = [
    "jovem aprendiz ti Taboão da Serra",
    "estágio ti suporte Taboão da Serra",
    "estágio desenvolvimento python São Paulo",
    "estágio dados São Paulo",
    "jovem aprendiz suporte técnico São Paulo",
    "estágio help desk São Paulo",
    "estágio infraestrutura São Paulo",
    "estágio back-end python São Paulo",
    "jovem aprendiz ti São Paulo sem experiência",
]

DIRECT_SEARCH_URLS = [
    ("Indeed", "https://br.indeed.com/jobs?q=jovem+aprendiz+ti&l=S%C3%A3o+Paulo%2C+SP"),
    ("Indeed", "https://br.indeed.com/jobs?q=est%C3%A1gio+ti+suporte&l=Tabo%C3%A3o+da+Serra%2C+SP"),
    ("Vagas.com", "https://www.vagas.com.br/vagas-de-jovem-aprendiz-ti"),
    ("Vagas.com", "https://www.vagas.com.br/vagas-de-estagio-ti"),
    ("Gupy", "https://portal.gupy.io/job-search?jobName=jovem+aprendiz+ti"),
    ("CIEE", "https://www.ciee.org.br/portal/estudantes/vagas"),
]

# ============================================================
# SCORING
# ============================================================
def score_job(job: dict) -> int:
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    score = 0

    area_hits = sum(1 for kw in PROFILE["area_keywords"] if kw in text)
    score += min(area_hits * 5, 30)

    strong_skills = ["python", "sql", "flask", "mysql"]
    for kw in PROFILE["skills"]:
        if kw in text:
            score += 4 if kw in strong_skills else 2
    score = min(score, 55)

    level_hits = sum(1 for kw in PROFILE["level_keywords"] if kw in text)
    score += min(level_hits * 10, 20)

    if "taboão" in text or "taboao" in text:
        score += 15
    elif "são paulo" in text or "sao paulo" in text:
        score += 10
    elif "remoto" in text or "híbrido" in text or "hibrido" in text:
        score += 12
    elif "osasco" in text or "embu" in text or "cotia" in text or "itapecerica" in text:
        score += 8

    if "6h" in text or "30h" in text or "meio período" in text or "part-time" in text or "6 horas" in text:
        score += 10
    elif "40h" in text:
        score += 3

    if "primeira experiência" in text or "sem experiência" in text or "sem experiencia" in text:
        score += 5
    if "capacitação" in text or "treinamento" in text or "mentoria" in text or "capacitacao" in text:
        score += 3
    if "remoto" in text or "home office" in text or "home-office" in text:
        score += 3

    for neg in PROFILE["negative_keywords"]:
        if neg in text:
            score -= 20
    if "inglês avançado" in text or "ingles avancado" in text or "inglês fluente" in text:
        score -= 15
    if "experiência na área" in text or "experiencia na area" in text:
        score -= 10
    if not any(kw in text for kw in PROFILE["level_keywords"]):
        score -= 20

    return max(0, min(100, score))

# ============================================================
# BUSCA COM RETRY
# ============================================================
def fetch_with_retry(url, headers, max_retries=None):
    if max_retries is None:
        max_retries = CONFIG["max_retries"]
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp
            elif resp.status_code == 429:
                time.sleep(CONFIG["retry_delay"] * (attempt + 1))
            else:
                time.sleep(CONFIG["retry_delay"])
        except requests.exceptions.RequestException as e:
            print(f"  [AVISO] Tentativa {attempt+1}/{max_retries} falhou: {e}")
            time.sleep(CONFIG["retry_delay"] * (attempt + 1))
    return None

def search_bing(query):
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }
    url = f"https://www.bing.com/search?q={quote_plus(query)}"
    resp = fetch_with_retry(url, headers)
    if not resp:
        return results
    soup = BeautifulSoup(resp.text, "html.parser")
    for result in soup.select("li.b_algo"):
        title_el = result.select_one("h2 a")
        snippet_el = result.select_one(".b_caption p")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        link = title_el.get("href", "")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        results.append({"title": title, "link": link, "description": snippet, "source": "Bing"})
    return results

def search_jobs() -> list[dict]:
    jobs = []
    seen = set()

    print("  [1/2] Buscando no Bing...")
    for query in SEARCH_QUERIES:
        try:
            res = search_bing(query)
            for r in res:
                combined = (r["title"] + " " + r["description"]).lower()
                if not any(kw in combined for kw in PROFILE["level_keywords"]):
                    continue
                key = r["title"].lower().strip()
                if key in seen:
                    continue
                seen.add(key)
                jobs.append(r)
            time.sleep(1)
        except Exception as e:
            print(f"  [AVISO] Erro na busca '{query}': {e}")

    print(f"  [2/2] Buscando em sites diretos...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }
    for source_name, url in DIRECT_SEARCH_URLS:
        try:
            resp = fetch_with_retry(url, headers)
            if not resp:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a"):
                text = a.get_text(strip=True)
                href = a.get("href", "")
                if len(text) < 10 or len(text) > 120:
                    continue
                combined = text.lower()
                if not any(kw in combined for kw in PROFILE["level_keywords"] + PROFILE["area_keywords"]):
                    continue
                key = text.lower().strip()
                if key in seen:
                    continue
                seen.add(key)
                jobs.append({
                    "title": text,
                    "link": urljoin(url, href) if href else url,
                    "description": f"Fonte: {source_name}",
                    "source": source_name,
                })
            time.sleep(1)
        except Exception as e:
            print(f"  [AVISO] Erro ao acessar {source_name}: {e}")

    return jobs

# ============================================================
# DEDUPLICAÇÃO
# ============================================================
def deduplicate(jobs):
    unique = []
    seen_titles = set()
    for job in jobs:
        norm = re.sub(r'[^a-z0-9]', '', job["title"].lower())
        norm = norm[:40]
        if norm in seen_titles:
            continue
        seen_titles.add(norm)
        unique.append(job)
    return unique

# ============================================================
# HISTÓRICO
# ============================================================
def load_history():
    path = os.path.join(CONFIG["vault_path"], CONFIG["history_file"])
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"seen": [], "last_run": None}
    return {"seen": [], "last_run": None}

def save_history(jobs):
    path = os.path.join(CONFIG["vault_path"], CONFIG["history_file"])
    history = load_history()
    seen = set(history.get("seen", []))
    for job in jobs:
        seen.add(job["title"].lower().strip())
    history["seen"] = list(seen)
    history["last_run"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_new_jobs(jobs, history):
    seen = set(history.get("seen", []))
    return [j for j in jobs if j["title"].lower().strip() not in seen]

# ============================================================
# GERAÇÃO DA NOTA
# ============================================================
def generate_note(jobs, new_jobs):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    scored = sorted(jobs, key=score_job, reverse=True)
    history = load_history()

    top = [j for j in scored if score_job(j) >= 70]
    mid = [j for j in scored if 40 <= score_job(j) < 70]
    low = [j for j in scored if score_job(j) < 40]
    new_set = {j["title"].lower().strip() for j in new_jobs}

    lines = [
        "---",
        "tags: [vagas, ti, estagio, jovem-aprendiz]",
        f"updated: {datetime.now().strftime('%Y-%m-%d')}",
        f"total_vagas: {len(jobs)}",
        f"novas: {len(new_jobs)}",
        "---",
        "",
        "# Vagas TI — Lucas Barbosa Pedro",
        f"> Relatório gerado em {now} · Busca automática v2.0",
        f"> Total: {len(jobs)} vagas · Novas: {len(new_jobs)} · Top: {len(top)} · Médias: {len(mid)}",
        "",
    ]

    if new_jobs:
        lines += [
            "## 🆕 Novas desde a última execução",
            "",
            "| # | Vaga | Score | Fonte | Link |",
            "|---|---|---|---|---|",
        ]
        new_scored = sorted(new_jobs, key=score_job, reverse=True)
        for i, job in enumerate(new_scored, 1):
            s = score_job(job)
            lines.append(f"| {i} | {job['title'][:60]} | {s} | {job.get('source','?')} | [ver]({job['link']}) |")
        lines.append("")

    lines += [
        "## 🟢 Top Matches (score ≥ 70)",
        "",
        "| # | Vaga | Score | Fonte | Novo? | Link |",
        "|---|---|---|---|---|---|",
    ]
    for i, job in enumerate(top, 1):
        s = score_job(job)
        is_new = "🆕" if job["title"].lower().strip() in new_set else ""
        lines.append(f"| {i} | {job['title'][:60]} | {s} | {job.get('source','?')} | {is_new} | [ver]({job['link']}) |")

    lines += ["", "### Detalhes (Top)", ""]
    for i, job in enumerate(top, 1):
        s = score_job(job)
        is_new = " 🆕 NOVA" if job["title"].lower().strip() in new_set else ""
        lines += [
            f"#### {i}. {job['title']}{is_new}",
            f"- **Score:** {s}/100",
            f"- **Fonte:** {job.get('source', '?')}",
            f"- **Descrição:** {job['description'][:200]}",
            f"- **Link:** {job['link']}",
            "",
        ]

    lines += [
        "## 🟡 Matches médios (score 40-69)",
        "",
        "| # | Vaga | Score | Fonte | Link |",
        "|---|---|---|---|---|",
    ]
    for i, job in enumerate(mid, 1):
        s = score_job(job)
        lines.append(f"| {i} | {job['title'][:60]} | {s} | {job.get('source','?')} | [ver]({job['link']}) |")

    if low:
        lines += [
            "",
            "## 🔴 Baixa compatibilidade (score < 40)",
            "",
            "| # | Vaga | Score | Fonte | Link |",
            "|---|---|---|---|---|",
        ]
        for i, job in enumerate(low, 1):
            s = score_job(job)
            lines.append(f"| {i} | {job['title'][:60]} | {s} | {job.get('source','?')} | [ver]({job['link']}) |")

    lines += [
        "",
        "---",
        f"> Total: {len(jobs)} · Novas: {len(new_jobs)} · Top: {len(top)} · Médias: {len(mid)} · Baixos: {len(low)}",
        f"> Última execução: {history.get('last_run', 'N/A')}",
        "> Para rodar novamente: `python vagas_agent.py`",
    ]

    return "\n".join(lines)

# ============================================================
# EMAIL
# ============================================================
def send_email(content: str):
    if not CONFIG["email_enabled"]:
        print("[INFO] Email desativado.")
        return
    try:
        msg = MIMEMultipart()
        msg["From"] = CONFIG["email_from"]
        msg["To"] = CONFIG["email_to"]
        msg["Subject"] = f"Vagas TI - Lucas ({datetime.now().strftime('%d/%m/%Y')})"
        msg.attach(MIMEText(content, "plain"))
        with smtplib.SMTP(CONFIG["smtp_server"], CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(CONFIG["email_from"], CONFIG["email_password"])
            server.send_message(msg)
        print("[OK] Email enviado com sucesso!")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar email: {e}")

# ============================================================
# NOTIFICAÇÃO WINDOWS (TOAST)
# ============================================================
def send_toast(title, message):
    if not CONFIG.get("toast_enabled", False):
        return
    try:
        ps_script = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$textNodes = $template.GetElementsByTagName("text")
$textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) | Out-Null
$textNodes.Item(1).AppendChild($template.CreateTextNode("{message}")) | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Agente Vagas TI").Show($toast)
'''
        subprocess.run(["powershell", "-Command", ps_script], capture_output=True, timeout=10)
    except Exception as e:
        print(f"[AVISO] Toast não enviado: {e}")

# ============================================================
# MAIN
# ============================================================
def run_agent(send_email_flag=False):
    print("=" * 50)
    print("  Agente de Vagas TI - Lucas (v2.0)")
    print("=" * 50)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando busca...")

    history = load_history()

    jobs = search_jobs()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(jobs)} vagas brutas encontradas.")

    if not jobs:
        print("[AVISO] Nenhuma vaga encontrada. Tente novamente mais tarde.")
        return

    jobs = deduplicate(jobs)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(jobs)} vagas após deduplicação.")

    new_jobs = get_new_jobs(jobs, history)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(new_jobs)} vagas novas.")

    note_content = generate_note(jobs, new_jobs)
    note_path = os.path.join(CONFIG["vault_path"], CONFIG["note_name"])
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(note_content)
    print(f"[OK] Nota salva em: {note_path}")

    save_history(jobs)

    if send_email_flag:
        send_email(note_content)

    if new_jobs:
        send_toast("Agente Vagas TI", f"{len(new_jobs)} novas vagas encontradas!")

    scored = sorted(jobs, key=score_job, reverse=True)
    print("\n--- TOP 5 VAGAS ---")
    for job in scored[:5]:
        print(f"  [{score_job(job):3d}] {job['title'][:60]}")
    print()

def main():
    if "--email" in sys.argv:
        run_agent(send_email_flag=True)
    elif "--schedule" in sys.argv:
        print(f"Modo agendado: a cada {CONFIG['schedule_hours']}h")
        run_agent(send_email_flag=True)
        schedule.every(CONFIG["schedule_hours"]).hours.do(lambda: run_agent(send_email_flag=True))
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        run_agent()

if __name__ == "__main__":
    main()

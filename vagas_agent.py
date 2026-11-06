#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agente de Vagas TI - Lucas Barbosa Pedro (v4.0 — Completo)
============================================================
Busca vagas de Jovem Aprendiz / Estágio em TI, ranqueia por compatibilidade,
gera relatório no Obsidian + email + Telegram, rastreia candidaturas,
gera prep de entrevista, currículo personalizado, dashboard e analytics.

Uso:
    python vagas_agent.py                    # busca e gera nota
    python vagas_agent.py --email            # busca + email
    python vagas_agent.py --telegram         # busca + Telegram
    python vagas_agent.py --schedule         # modo agendado
    python vagas_agent.py --candidatura "Vaga" --status candidatado
    python vagas_agent.py --listar           # listar candidaturas
    python vagas_agent.py --stats            # estatísticas
    python vagas_agent.py --entrevista "Vaga"  # prep de entrevista
    python vagas_agent.py --curriculo "Vaga"    # currículo personalizado
    python vagas_agent.py --dashboard         # gerar dashboard Obsidian Base
    python vagas_agent.py --analytics         # analytics completo

Dependências:
    pip install requests beautifulsoup4 schedule
"""

import os
import re
import sys
import json
import time
import smtplib
import schedule
import subprocess
import argparse
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote_plus, urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Instale: pip install requests beautifulsoup4 schedule")
    sys.exit(1)

# ============================================================
# CONFIG
# ============================================================
CONFIG = {
    "vault_path": os.environ.get("VAULT_PATH", os.getcwd() if not os.path.exists(r"C:\Users\Pichau\Downloads\Nova pasta\Estudos TI") else r"C:\Users\Pichau\Downloads\Nova pasta\Estudos TI"),
    "note_name": "Vagas TI - Lucas.md",
    "history_file": "vagas_history.json",
    "applications_file": "candidaturas.json",
    "salaries_file": "salarios.json",
    "email_enabled": True,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "email_from": "lucasbarbosapedro1108@gmail.com",
    "email_password": os.environ.get("EMAIL_PASSWORD", "afkg jkym lviw kvql"),
    "email_to": "lucasbarbosapedro1108@gmail.com",
    "telegram_enabled": False,
    "telegram_bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
    "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID", ""),
    "toast_enabled": True,
    "max_retries": 3,
    "retry_delay": 2,
    "schedule_hours": 24,
    "followup_days": 7,
    "cities": ["Taboão da Serra", "São Paulo", "Osasco", "Embu", "Cotia", "Itapecerica"],
    "llm_api_key": os.environ.get("LLM_API_KEY", ""),
    "llm_provider": "openai",  # openai, anthropic, gemini
}

# ============================================================
# PERFIL DO CANDIDATO
# ============================================================
PROFILE = {
    "name": "Lucas Barbosa Pedro",
    "phone": "(11) 91508-2460",
    "email": "lucasbarbosapedro1108@gmail.com",
    "linkedin": "linkedin.com/in/lucasbarbosapedro",
    "github": "github.com/lucass1108",
    "location": "Taboão da Serra - SP",
    "education": "Análise e Desenvolvimento de Sistemas (ADS) — UNIFECAF (2º sem)",
    "skills": {
        "strong": ["python", "sql", "flask", "mysql"],
        "medium": ["git", "github", "html", "css", "linux"],
        "basic": ["windows", "excel", "office", "redes", "atendimento", "backoffice"],
    },
    "projects": [
        {"name": "FinanceTracker", "tech": "Python, Flask, MySQL, Git",
         "desc": "App web de controle financeiro: receitas, despesas, limites, metas, alertas"},
        {"name": "BrutalFit Expo", "tech": "Python, MySQL",
         "desc": "Sistema de gestão de academia: CRUD completo, 2 perfis (ADM/ALUNO)"},
    ],
    "experience": "Agente de Relacionamento I (Backoffice) — Sercom/Claro (jan/2026-atual)",
    "achievements": ["Medalha de ouro CUCO/USP 2023", "Medalhista OBMEP", "Medalhista OMASP"],
    "english": "Intermediário (CNA)",
    "area_keywords": ["suporte", "dados", "desenvolvimento", "ti", "tecnologia",
                      "informática", "help desk", "infraestrutura", "programação",
                      "analista", "back-end", "frontend", "fullstack", "dev"],
    "level_keywords": ["jovem aprendiz", "estágio", "estagiário", "aprendiz", "trainee"],
    "negative_keywords": ["experiência prévia em ti", "experiência em ti",
                          "inglês avançado", "inglês fluente", "3 anos",
                          "2 anos de experiência", "experiência comprovada"],
}

APPLICATION_STATUSES = {
    "nao_candidatado": {"label": "Não candidatado", "icon": "⬜", "color": "gray"},
    "candidatado": {"label": "Candidatado", "icon": "🟦", "color": "blue"},
    "em_analise": {"label": "Em análise", "icon": "🟨", "color": "yellow"},
    "entrevista": {"label": "Entrevista", "icon": "🟩", "color": "green"},
    "rejeitado": {"label": "Não selecionado", "icon": "🔴", "color": "red"},
    "aprovado": {"label": "Aprovado! 🎉", "icon": "🟢", "color": "green"},
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
    "estágio analista dados São Paulo",
    "estágio desenvolvedor web São Paulo",
    "trainee ti São Paulo",
]

DIRECT_SEARCH_URLS = [
    ("Indeed", "https://br.indeed.com/jobs?q=jovem+aprendiz+ti&l=S%C3%A3o+Paulo%2C+SP"),
    ("Indeed", "https://br.indeed.com/jobs?q=est%C3%A1gio+ti+suporte&l=Tabo%C3%A3o+da+Serra%2C+SP"),
    ("Indeed", "https://br.indeed.com/jobs?q=est%C3%A1gio+python&l=S%C3%A3o+Paulo%2C+SP"),
    ("Vagas.com", "https://www.vagas.com.br/vagas-de-jovem-aprendiz-ti"),
    ("Vagas.com", "https://www.vagas.com.br/vagas-de-estagio-ti"),
    ("Vagas.com", "https://www.vagas.com.br/vagas-de-estagio-python"),
    ("Gupy", "https://portal.gupy.io/job-search?jobName=jovem+aprendiz+ti"),
    ("Gupy", "https://portal.gupy.io/job-search?jobName=estagio+ti"),
    ("CIEE", "https://www.ciee.org.br/portal/estudantes/vagas"),
    ("NUBE", "https://www.nube.com.br/vagas-de-estagio"),
    ("Catho", "https://www.catho.com.br/vagas/estagio-ti/"),
    ("99jobs", "https://99jobs.com/vagas?search=estagio+ti"),
]

# ============================================================
# SCORING
# ============================================================
def score_job(job: dict) -> int:
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    score = 0

    area_hits = sum(1 for kw in PROFILE["area_keywords"] if kw in text)
    score += min(area_hits * 5, 30)

    all_skills = PROFILE["skills"]["strong"] + PROFILE["skills"]["medium"] + PROFILE["skills"]["basic"]
    for kw in all_skills:
        if kw in text:
            score += 5 if kw in PROFILE["skills"]["strong"] else (3 if kw in PROFILE["skills"]["medium"] else 1)
    score = min(score, 55)

    level_hits = sum(1 for kw in PROFILE["level_keywords"] if kw in text)
    score += min(level_hits * 10, 20)

    if "taboão" in text or "taboao" in text:
        score += 15
    elif "são paulo" in text or "sao paulo" in text:
        score += 10
    elif "remoto" in text or "híbrido" in text or "hibrido" in text:
        score += 12
    elif any(c.lower() in text for c in CONFIG["cities"]):
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
# RASTREAMENTO DE CANDIDATURAS
# ============================================================
def load_applications():
    path = os.path.join(CONFIG["vault_path"], CONFIG["applications_file"])
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("candidaturas", [])
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_applications(apps):
    path = os.path.join(CONFIG["vault_path"], CONFIG["applications_file"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"candidaturas": apps}, f, ensure_ascii=False, indent=2)

def find_application(title):
    apps = load_applications()
    title_lower = title.lower().strip()
    for app in apps:
        if title_lower in app["vaga"].lower() or app["vaga"].lower() in title_lower:
            return app
    return None

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
            "prazo": "", "salario": "",
        }
        apps.append(new_app)
        print(f"[OK] Registrada: {title} → {APPLICATION_STATUSES[status]['label']}")
    save_applications(apps)
    return existing or apps[-1]

def get_followup_reminders():
    apps = load_applications()
    reminders = []
    now = datetime.now()
    for app in apps:
        if app["status"] in ("candidatado", "em_analise"):
            try:
                data = datetime.fromisoformat(app.get("data_candidatura", app.get("data_atualizacao", "")))
                days = (now - data).days
                if days >= CONFIG["followup_days"]:
                    reminders.append((app, days))
            except (ValueError, TypeError):
                pass
    return reminders

def get_application_stats():
    apps = load_applications()
    stats = {s: 0 for s in APPLICATION_STATUSES}
    for app in apps:
        st = app.get("status", "nao_candidatado")
        if st in stats: stats[st] += 1
    stats["total"] = len(apps)
    # Taxa de resposta
    responded = stats.get("em_analise", 0) + stats.get("entrevista", 0) + stats.get("rejeitado", 0) + stats.get("aprovado", 0)
    stats["taxa_resposta"] = round((responded / stats["total"] * 100), 1) if stats["total"] > 0 else 0
    stats["taxa_entrevista"] = round((stats.get("entrevista", 0) + stats.get("aprovado", 0)) / stats["total"] * 100, 1) if stats["total"] > 0 else 0
    return stats

def list_applications():
    apps = load_applications()
    if not apps:
        print("Nenhuma candidatura registrada.")
        print('Use: python vagas_agent.py --candidatura "Nome da vaga" --status candidatado')
        return
    print("\n" + "=" * 70)
    print("  CANDIDATURAS — Lucas Barbosa Pedro")
    print("=" * 70)
    for i, app in enumerate(apps, 1):
        st = APPLICATION_STATUSES.get(app["status"], APPLICATION_STATUSES["nao_candidatado"])
        print(f"\n  {i}. {st['icon']} {app['vaga']}")
        print(f"     Empresa: {app.get('empresa', 'N/A')}")
        print(f"     Status: {st['label']}  |  Data: {app.get('data_candidatura', 'N/A')}")
        if app.get("notas"): print(f"     Notas: {app['notas']}")
        if app.get("link"): print(f"     Link: {app['link']}")
        if app.get("proximo_passo"): print(f"     Próximo: {app['proximo_passo']}")
    print("\n" + "=" * 70)
    stats = get_application_stats()
    print(f"\n  📊 Total: {stats['total']} | Resposta: {stats['taxa_resposta']}% | Entrevista: {stats['taxa_entrevista']}%")
    for st_key, st_info in APPLICATION_STATUSES.items():
        if stats[st_key] > 0:
            print(f"     {st_info['icon']} {st_info['label']}: {stats[st_key]}")
    print()

# ============================================================
# SALÁRIOS
# ============================================================
def load_salaries():
    path = os.path.join(CONFIG["vault_path"], CONFIG["salaries_file"])
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("salarios", [])
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_salaries(sals):
    path = os.path.join(CONFIG["vault_path"], CONFIG["salaries_file"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"salarios": sals}, f, ensure_ascii=False, indent=2)

def extract_salary(text):
    """Extrai faixa salarial de um texto."""
    patterns = [
        r'R\$\s*([\d.,]+)\s*(?:a|à|-|até)\s*R\$\s*([\d.,]+)',
        r'R\$\s*([\d.,]+)',
        r'salário[:\s]*R\$\s*([\d.,]+)',
        r'bolsa[:\s]*R\$\s*([\d.,]+)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            groups = m.groups()
            if len(groups) == 2:
                return (groups[0], groups[1])
            return (groups[0], groups[0])
    return None

# ============================================================
# PREP DE ENTREVISTA
# ============================================================
INTERVIEW_QUESTIONS = {
    "geral": [
        "Fale sobre você e sua trajetória.",
        "Por que você quer trabalhar nesta empresa?",
        "Quais são seus pontos fortes e fracos?",
        "Onde você se vê em 5 anos?",
        "Por que escolheu a área de TI?",
    ],
    "tecnico": [
        "Explique a diferença entre frontend e backend.",
        "O que é um banco de dados relacional? Cite exemplos.",
        "Como funciona o Git e para que serve?",
        "O que é uma API REST?",
        "Explique o que é SQL e dê exemplos de comandos (SELECT, INSERT, UPDATE, DELETE).",
        "O que é Flask e como funciona?",
        "Como você resolveria um problema de rede (IP, DNS)?",
        "O que é versionamento de código?",
    ],
    "comportamental": [
        "Conte sobre um desafio que você superou.",
        "Como você lida com prazos apertados?",
        "Descreva uma situação de trabalho em equipe.",
        "Como você prioriza tarefas?",
        "O que você faz quando não sabe resolver um problema?",
    ],
    "projetos": [
        "Fale sobre o FinanceTracker. Como funciona?",
        "Quais tecnologias você usou no BrutalFit Expo?",
        "Como você organizou o banco de dados do FinanceTracker?",
        "Por que usou Blueprints no Flask?",
        "Como você garante a segurança das credenciais do banco?",
    ],
}

def generate_interview_prep(vaga_title):
    """Gera preparação de entrevista para uma vaga."""
    app = find_application(vaga_title)
    vaga = app["vaga"] if app else vaga_title
    empresa = app.get("empresa", "N/A") if app else "N/A"

    lines = [
        f"# 🎯 Prep de Entrevista — {vaga}",
        f"> Empresa: {empresa} | Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "## 📌 Sobre a vaga",
        f"- **Vaga:** {vaga}",
        f"- **Empresa:** {empresa}",
        f"- **Score:** {app.get('score', 'N/A') if app else 'N/A'}/100" if app else "",
        "",
        "## 💬 Perguntas gerais",
    ]
    for q in INTERVIEW_QUESTIONS["geral"]:
        lines.append(f"- {q}")

    lines += ["", "## 🔧 Perguntas técnicas"]
    for q in INTERVIEW_QUESTIONS["tecnico"]:
        lines.append(f"- {q}")

    lines += ["", "## 🧠 Perguntas comportamentais"]
    for q in INTERVIEW_QUESTIONS["comportamental"]:
        lines.append(f"- {q}")

    lines += ["", "## 🚀 Perguntas sobre seus projetos"]
    for q in INTERVIEW_QUESTIONS["projetos"]:
        lines.append(f"- {q}")

    lines += [
        "",
        "## 📝 Dicas para a entrevista",
        "- Pesquise sobre a empresa antes da entrevista",
        "- Prepare exemplos concretos (use a técnica STAR: Situação, Tarefa, Ação, Resultado)",
        "- Tenha perguntas para fazer ao entrevistador",
        "- Chegue 10 min antes (se presencial) ou teste a câmera (se online)",
        "- Vista-se adequadamente para a empresa",
        "",
        "## 🎤 Suas perguntas para o entrevistador",
        "- Quais são as principais atividades do dia a dia?",
        "- Existe possibilidade de efetivação após o estágio?",
        "- Como funciona o acompanhamento do estagiário?",
        "- Quais tecnologias a equipe utiliza?",
        "",
        "---",
        "> Gerado pelo Agente Vagas TI v4.0",
    ]

    content = "\n".join(lines)
    filename = f"Entrevista - {vaga[:40]}.md"
    filepath = os.path.join(CONFIG["vault_path"], filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Prep de entrevista salvo em: {filepath}")
    print(content)
    return content

# ============================================================
# CURRÍCULO PERSONALIZADO
# ============================================================
def generate_tailored_resume(vaga_title):
    """Gera sugestões de currículo personalizado para uma vaga."""
    app = find_application(vaga_title)
    vaga = app["vaga"] if app else vaga_title
    empresa = app.get("empresa", "N/A") if app else "N/A"
    score = app.get("score", 0) if app else 0

    # Identifica skills relevantes
    text = vaga.lower()
    relevant_skills = []
    for skill in PROFILE["skills"]["strong"] + PROFILE["skills"]["medium"] + PROFILE["skills"]["basic"]:
        if skill in text:
            relevant_skills.append(skill)

    lines = [
        f"# 📄 Currículo Personalizado — {vaga}",
        f"> Empresa: {empresa} | Score: {score}/100 | Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "## 🎯 Skills destacadas para esta vaga",
    ]
    if relevant_skills:
        for s in relevant_skills:
            lines.append(f"- ✅ {s.title()}")
    else:
        lines.append("- (Nenhuma skill específica detectada — destaque Python, SQL e Git)")

    lines += [
        "",
        "## 📝 Sugestões de adaptação do currículo",
        "",
        "### Objetivo",
        f"> Jovem Aprendiz / Estágio em TI — {vaga} na {empresa}",
        "",
        "### Resumo profissional (adaptado)",
        f"> Estudante do 2º semestre de ADS (UNIFECAF), com experiência em backoffice e atendimento. "
        f"Desenvolve projetos próprios com Python, Flask e MySQL. Busca oportunidade de estágio/JA em {vaga.lower()} "
        f"na {empresa}, aplicando conhecimentos em " + ", ".join(s.title() for s in relevant_skills[:5] if relevant_skills) + ".",
        "",
        "### Projetos (destacar)",
    ]
    for proj in PROFILE["projects"]:
        lines.append(f"- **{proj['name']}** ({proj['tech']}): {proj['desc']}")

    lines += [
        "",
        "### Experiência (adaptar descrição)",
        f"- **Agente de Relacionamento I (Backoffice)** — Sercom/Claro (jan/2026-atual)",
        "  - Atendimento de solicitações comerciais e operacionais",
        "  - Cumprimento de metas e SLA",
        "  - " + ("Experiência com sistemas e processos — relevante para " + vaga if "suporte" in text or "atendimento" in text else "Experiência em atendimento ao cliente"),
        "",
        "### Dicas para esta candidatura",
        "- Destaque os projetos do GitHub (FinanceTracker e BrutalFit)",
        "- Mencione a medalha de ouro na CUCO/USP como diferencial",
        "- Enfatize vontade de aprender e crescimento na área",
    ]
    if "python" in text:
        lines.append("- Destaque sua experiência prática com Python e Flask")
    if "sql" in text or "dados" in text or "banco" in text:
        lines.append("- Destaque seu conhecimento em SQL e modelagem de banco de dados")
    if "suporte" in text or "help desk" in text:
        lines.append("- Destaque sua experiência com atendimento e backoffice")
    if "remoto" in text:
        lines.append("- Mencione disponibilidade para trabalho remoto")

    lines += [
        "",
        "### 🤖 Prompt para IA (copie e cole no ChatGPT/Claude)",
        "```",
        f"Adapte meu currículo para a vaga de {vaga} na {empresa}.",
        f"Meu perfil: estudante de ADS 2º semestre, Python/SQL/Flask/MySQL, ",
        f"projetos FinanceTracker e BrutalFit no GitHub, experiência em backoffice Sercom/Claro.",
        f"Diferenciais: medalhista CUCO/USP, OBMEP, OMASP.",
        f"Destaque as skills mais relevantes para esta vaga e sugira melhorias.",
        "```",
        "",
        "---",
        "> Gerado pelo Agente Vagas TI v4.0",
    ]

    content = "\n".join(lines)
    filename = f"Curriculo - {vaga[:40]}.md"
    filepath = os.path.join(CONFIG["vault_path"], filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Currículo personalizado salvo em: {filepath}")
    print(content)
    return content

# ============================================================
# TELEGRAM
# ============================================================
def send_telegram(message):
    """Envia mensagem via Telegram Bot."""
    if not CONFIG["telegram_enabled"]:
        print("[INFO] Telegram desativado. Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID.")
        return
    token = CONFIG["telegram_bot_token"]
    chat_id = CONFIG["telegram_chat_id"]
    if not token or not chat_id:
        print("[AVISO] Telegram não configurado.")
        return
    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        print("[OK] Mensagem enviada via Telegram!")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar Telegram: {e}")

# ============================================================
# EMAIL
# ============================================================
def send_email(content: str):
    if not CONFIG["email_enabled"]:
        print("[INFO] Email desativado.")
        return
    try:
        # Gera versão mobile-friendly do email
        scored_jobs = []
        # Extrai top vagas do conteúdo (simplificado)
        msg = MIMEMultipart("alternative")
        msg["From"] = CONFIG["email_from"]
        msg["To"] = CONFIG["email_to"]
        msg["Subject"] = f"📋 Vagas TI - {datetime.now().strftime('%d/%m/%Y')}"

        # Versão texto simples (mobile-friendly)
        text_version = f"""VAGAS TI - LUCAS BARBOSA PEDRO
{datetime.now().strftime('%d/%m/%Y %H:%M')}

{content}

---
Agente Vagas TI v4.0
Para mais detalhes, veja a nota no Obsidian.
"""

        # Versão HTML (mais bonita no celular)
        html_version = f"""<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 16px; background: #f5f5f5; color: #333; }}
  .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  h1 {{ color: #2563eb; font-size: 20px; margin-bottom: 4px; }}
  .subtitle {{ color: #666; font-size: 13px; margin-bottom: 16px; }}
  .section {{ margin: 16px 0; padding: 12px; border-radius: 8px; background: #f8f9fa; }}
  .section h2 {{ font-size: 16px; margin: 0 0 8px 0; }}
  .job {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
  .job:last-child {{ border-bottom: none; }}
  .score {{ display: inline-block; background: #2563eb; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
  .score-high {{ background: #16a34a; }}
  .score-med {{ background: #ca8a04; }}
  .score-low {{ background: #dc2626; }}
  .link {{ color: #2563eb; text-decoration: none; font-size: 13px; }}
  .footer {{ text-align: center; color: #999; font-size: 11px; margin-top: 20px; padding-top: 12px; border-top: 1px solid #eee; }}
  pre {{ white-space: pre-wrap; word-wrap: break-word; font-size: 12px; background: #f1f1f1; padding: 8px; border-radius: 6px; }}
</style>
</head>
<body>
<div class="container">
  <h1>📋 Vagas TI — Lucas</h1>
  <p class="subtitle">{datetime.now().strftime('%d/%m/%Y %H:%M')} · Agente v4.0</p>
  <div class="section">
    <pre>{content[:3000]}</pre>
  </div>
  <div class="footer">
    Agente Vagas TI · Gerado automaticamente<br>
    Para mais detalhes, veja a nota no Obsidian.
  </div>
</div>
</body>
</html>"""

        msg.attach(MIMEText(text_version, "plain"))
        msg.attach(MIMEText(html_version, "html"))

        with smtplib.SMTP(CONFIG["smtp_server"], CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(CONFIG["email_from"], CONFIG["email_password"])
            server.send_message(msg)
        print("[OK] Email enviado com sucesso! (versão mobile)")
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
# OBSIDIAN BASE DASHBOARD
# ============================================================
def generate_dashboard():
    """Gera um arquivo .base para dashboard no Obsidian."""
    content = '''filters:
  and:
    - file.hasTag("vaga")
    - file.inFolder("Vagas")

formulas:
  score_label: 'if(score >= 70, "🟢 Top", if(score >= 40, "🟡 Médio", "🔴 Baixo"))'
  dias_sem_resposta: '(now() - file.ctime).days'

properties:
  score:
    displayName: Score
  status:
    displayName: Status
  fonte:
    displayName: Fonte
  empresa:
    displayName: Empresa

views:
  - type: table
    name: "Todas as Vagas"
    order:
      - file.name
      - score
      - status
      - fonte
      - empresa
    sort:
      - property: score
        direction: DESC

  - type: table
    name: "Top Matches (≥70)"
    filters:
      and:
        - score >= 70
    sort:
      - property: score
        direction: DESC

  - type: table
    name: "Candidaturas Ativas"
    filters:
      and:
        - status != "nao_candidatado"
        - status != "rejeitado"
    sort:
      - property: file.ctime
        direction: DESC

  - type: cards
    name: "Cards por Score"
    order:
      - file.name
      - score
    sort:
      - property: score
        direction: DESC

  - type: table
    name: "Follow-up (7+ dias)"
    filters:
      and:
        - status == "candidatado"
        - '(now() - file.ctime).days >= 7'
    sort:
      - property: file.ctime
        direction: ASC
'''
    filepath = os.path.join(CONFIG["vault_path"], "Vagas Dashboard.base")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Dashboard salvo em: {filepath}")
    print("Abra no Obsidian para visualizar as vagas em tabela/cards!")

# ============================================================
# GERAÇÃO DA NOTA (completa)
# ============================================================
def generate_note(jobs, new_jobs):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    scored = sorted(jobs, key=score_job, reverse=True)
    history = load_history()
    apps = load_applications()
    reminders = get_followup_reminders()

    top = [j for j in scored if score_job(j) >= 70]
    mid = [j for j in scored if 40 <= score_job(j) < 70]
    low = [j for j in scored if score_job(j) < 40]
    new_set = {j["title"].lower().strip() for j in new_jobs}

    # Salários
    salaries = []
    for job in jobs:
        sal = extract_salary(job.get("description", "") + " " + job.get("title", ""))
        if sal:
            salaries.append((job["title"], sal))

    lines = [
        "---",
        "tags: [vagas, ti, estagio, jovem-aprendiz, candidaturas]",
        f"updated: {datetime.now().strftime('%Y-%m-%d')}",
        f"total_vagas: {len(jobs)}",
        f"novas: {len(new_jobs)}",
        f"total_candidaturas: {len(apps)}",
        f"followups_pendentes: {len(reminders)}",
        "---",
        "",
        "# Vagas TI — Lucas Barbosa Pedro",
        f"> Relatório gerado em {now} · Agente v4.0 (completo)",
        f"> Total: {len(jobs)} vagas · Novas: {len(new_jobs)} · Candidaturas: {len(apps)} · Follow-ups: {len(reminders)}",
        "",
    ]

    # Follow-ups
    if reminders:
        lines += ["## ⏰ Lembretes de Follow-up", ""]
        for app, days in reminders:
            st = APPLICATION_STATUSES.get(app["status"], APPLICATION_STATUSES["candidatado"])
            lines.append(f"- {st['icon']} **{app['vaga']}** — {days} dias sem resposta. Envie follow-up!")
        lines.append("")

    # Novas vagas
    if new_jobs:
        lines += [
            "## 🆕 Novas desde a última execução",
            "",
            "| # | Vaga | Score | Fonte | Link |",
            "|---|---|---|---|---|",
        ]
        for i, job in enumerate(sorted(new_jobs, key=score_job, reverse=True), 1):
            s = score_job(job)
            lines.append(f"| {i} | {job['title'][:60]} | {s} | {job.get('source','?')} | [ver]({job['link']}) |")
        lines.append("")

    # Top matches
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
        app = find_application(job["title"])
        app_status = ""
        if app:
            st = APPLICATION_STATUSES.get(app["status"], APPLICATION_STATUSES["nao_candidatado"])
            app_status = f"\n- **Candidatura:** {st['icon']} {st['label']} ({app.get('data_candidatura', 'N/A')})"
        sal = extract_salary(job.get("description", "") + " " + job.get("title", ""))
        sal_str = f"\n- **Salário:** R$ {sal[0]}" + (f" a R$ {sal[1]}" if sal and sal[0] != sal[1] else "") if sal else ""
        lines += [
            f"#### {i}. {job['title']}{is_new}",
            f"- **Score:** {s}/100",
            f"- **Fonte:** {job.get('source', '?')}",
            f"- **Descrição:** {job['description'][:200]}",
            f"- **Link:** {job['link']}{app_status}{sal_str}",
            "",
        ]

    # Matches médios
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

    # Candidaturas
    lines += ["", "## 📋 Minhas Candidaturas", ""]
    if apps:
        lines += [
            "| # | Vaga | Empresa | Status | Data | Score |",
            "|---|---|---|---|---|---|",
        ]
        for i, app in enumerate(apps, 1):
            st = APPLICATION_STATUSES.get(app["status"], APPLICATION_STATUSES["nao_candidatado"])
            lines.append(
                f"| {i} | {app['vaga'][:40]} | {app.get('empresa','N/A')[:20]} | "
                f"{st['icon']} {st['label']} | {app.get('data_candidatura','N/A')} | {app.get('score',0)} |"
            )
        lines.append("")
        lines += ["### Detalhes das Candidaturas", ""]
        for i, app in enumerate(apps, 1):
            st = APPLICATION_STATUSES.get(app["status"], APPLICATION_STATUSES["nao_candidatado"])
            lines += [
                f"#### {i}. {st['icon']} {app['vaga']}",
                f"- **Empresa:** {app.get('empresa', 'N/A')}",
                f"- **Status:** {st['label']}",
                f"- **Data:** {app.get('data_candidatura', 'N/A')}",
                f"- **Score:** {app.get('score', 0)}/100",
            ]
            if app.get("notas"): lines.append(f"- **Notas:** {app['notas']}")
            if app.get("link"): lines.append(f"- **Link:** {app['link']}")
            if app.get("proximo_passo"): lines.append(f"- **Próximo passo:** {app['proximo_passo']}")
            lines.append("")
        stats = get_application_stats()
        lines += [
            "### 📊 Estatísticas",
            "",
            f"- **Total:** {stats['total']}",
            f"- **Taxa de resposta:** {stats['taxa_resposta']}%",
            f"- **Taxa de entrevista:** {stats['taxa_entrevista']}%",
        ]
        for st_key, st_info in APPLICATION_STATUSES.items():
            if stats[st_key] > 0:
                lines.append(f"- {st_info['icon']} {st_info['label']}: {stats[st_key]}")
        lines.append("")
    else:
        lines += ["> Nenhuma candidatura registrada.", "> Use: `python vagas_agent.py --candidatura \"Vaga\" --status candidatado`", ""]

    # Salários
    if salaries:
        lines += ["## 💰 Faixas Salariais Encontradas", ""]
        for title, (min_s, max_s) in salaries[:10]:
            if min_s != max_s:
                lines.append(f"- {title[:50]}: R$ {min_s} a R$ {max_s}")
            else:
                lines.append(f"- {title[:50]}: R$ {min_s}")
        lines.append("")

    lines += [
        "---",
        f"> Total vagas: {len(jobs)} · Novas: {len(new_jobs)} · Candidaturas: {len(apps)} · Follow-ups: {len(reminders)}",
        f"> Última execução: {history.get('last_run', 'N/A')}",
        "> Comandos: `--email` `--telegram` `--listar` `--stats` `--entrevista` `--curriculo` `--dashboard` `--analytics`",
    ]

    return "\n".join(lines)

# ============================================================
# ANALYTICS
# ============================================================
def show_analytics():
    """Mostra analytics completo no console."""
    apps = load_applications()
    history = load_history()
    stats = get_application_stats()

    print("\n" + "=" * 60)
    print("  📊 ANALYTICS — Agente Vagas TI")
    print("=" * 60)

    print(f"\n  📋 Candidaturas: {stats['total']}")
    print(f"     Taxa de resposta: {stats['taxa_resposta']}%")
    print(f"     Taxa de entrevista: {stats['taxa_entrevista']}%")
    for st_key, st_info in APPLICATION_STATUSES.items():
        if stats[st_key] > 0:
            bar = "█" * stats[st_key]
            print(f"     {st_info['icon']} {st_info['label']}: {stats[st_key]} {bar}")

    # Timeline
    if apps:
        print(f"\n  📅 Timeline de candidaturas:")
        sorted_apps = sorted(apps, key=lambda a: a.get("data_candidatura", ""))
        for app in sorted_apps:
            st = APPLICATION_STATUSES.get(app["status"], APPLICATION_STATUSES["nao_candidatado"])
            print(f"     {app.get('data_candidatura', 'N/A')} — {st['icon']} {app['vaga'][:40]} ({app.get('empresa', 'N/A')})")

    # Follow-ups pendentes
    reminders = get_followup_reminders()
    if reminders:
        print(f"\n  ⏰ Follow-ups pendentes: {len(reminders)}")
        for app, days in reminders:
            print(f"     - {app['vaga']} ({days} dias)")

    print(f"\n  📈 Histórico: {len(history.get('seen', []))} vagas vistas")
    print(f"     Última execução: {history.get('last_run', 'N/A')}")
    print("\n" + "=" * 60)

# ============================================================
# MAIN
# ============================================================
def run_agent(send_email_flag=False, send_telegram_flag=False):
    print("=" * 50)
    print("  Agente de Vagas TI - Lucas (v4.0)")
    print("=" * 50)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando busca...")

    history = load_history()

    jobs = search_jobs()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(jobs)} vagas brutas encontradas.")

    if not jobs:
        print("[AVISO] Nenhuma vaga encontrada.")
        return

    jobs = deduplicate(jobs)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(jobs)} vagas após deduplicação.")

    new_jobs = get_new_jobs(jobs, history)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(new_jobs)} vagas novas.")

    reminders = get_followup_reminders()
    if reminders:
        print(f"\n  ⏰ {len(reminders)} candidatura(s) precisam de follow-up!")

    note_content = generate_note(jobs, new_jobs)
    note_path = os.path.join(CONFIG["vault_path"], CONFIG["note_name"])
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(note_content)
    print(f"[OK] Nota salva em: {note_path}")

    save_history(jobs)

    if send_email_flag:
        send_email(note_content)

    if send_telegram_flag or CONFIG["telegram_enabled"]:
        # Envia resumo via Telegram
        top_jobs = sorted(jobs, key=score_job, reverse=True)[:5]
        tg_msg = f"📋 *Vagas TI — {datetime.now().strftime('%d/%m/%Y')}*\n\n"
        tg_msg += f"🔍 {len(jobs)} vagas · 🆕 {len(new_jobs)} novas\n\n"
        tg_msg += "*Top 5:*\n"
        for i, job in enumerate(top_jobs, 1):
            tg_msg += f"{i}. [{score_job(job)}] {job['title'][:50]}\n   {job['link']}\n"
        if new_jobs:
            tg_msg += f"\n🆕 {len(new_jobs)} vagas novas desde a última busca!"
        if reminders:
            tg_msg += f"\n⏰ {len(reminders)} follow-ups pendentes!"
        send_telegram(tg_msg)

    if new_jobs:
        send_toast("Agente Vagas TI", f"{len(new_jobs)} novas vagas encontradas!")

    scored = sorted(jobs, key=score_job, reverse=True)
    print("\n--- TOP 5 VAGAS ---")
    for job in scored[:5]:
        print(f"  [{score_job(job):3d}] {job['title'][:60]}")
    print()

def main():
    parser = argparse.ArgumentParser(description="Agente de Vagas TI - Lucas v4.0")
    parser.add_argument("--email", action="store_true", help="Enviar por email")
    parser.add_argument("--telegram", action="store_true", help="Enviar via Telegram")
    parser.add_argument("--schedule", action="store_true", help="Modo agendado")
    parser.add_argument("--candidatura", type=str, help="Registrar candidatura")
    parser.add_argument("--status", type=str, default="candidatado", choices=list(APPLICATION_STATUSES.keys()))
    parser.add_argument("--nota", type=str, default="", help="Notas")
    parser.add_argument("--empresa", type=str, default="", help="Empresa")
    parser.add_argument("--link", type=str, default="", help="Link")
    parser.add_argument("--score", type=int, default=0, help="Score")
    parser.add_argument("--proximo-passo", type=str, default="", dest="proximo_passo")
    parser.add_argument("--listar", action="store_true", help="Listar candidaturas")
    parser.add_argument("--stats", action="store_true", help="Estatísticas")
    parser.add_argument("--entrevista", type=str, help="Prep de entrevista para vaga")
    parser.add_argument("--curriculo", type=str, help="Currículo personalizado para vaga")
    parser.add_argument("--dashboard", action="store_true", help="Gerar dashboard Obsidian Base")
    parser.add_argument("--analytics", action="store_true", help="Analytics completo")
    parser.add_argument("--salario", type=str, help="Registrar salário (formato: \"Vaga:R$1000-R$2000\")")

    args = parser.parse_args()

    if args.listar:
        list_applications()
        return
    if args.stats:
        stats = get_application_stats()
        print(f"\n📊 Total: {stats['total']} | Resposta: {stats['taxa_resposta']}% | Entrevista: {stats['taxa_entrevista']}%")
        for st_key, st_info in APPLICATION_STATUSES.items():
            if stats[st_key] > 0:
                print(f"   {st_info['icon']} {st_info['label']}: {stats[st_key]}")
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
    if args.salario:
        parts = args.salario.split(":")
        if len(parts) == 2:
            vaga = parts[0].strip()
            sal_range = parts[1].strip()
            m = re.search(r'R?\$?\s*([\d.,]+)\s*[-–aà]+\s*R?\$?\s*([\d.,]+)', sal_range)
            if m:
                sals = load_salaries()
                sals.append({"vaga": vaga, "min": m.group(1), "max": m.group(2), "data": datetime.now().strftime("%Y-%m-%d")})
                save_salaries(sals)
                print(f"[OK] Salário registrado: {vaga} → R$ {m.group(1)} a R$ {m.group(2)}")
            else:
                print("[ERRO] Formato inválido. Use: --salario \"Vaga:R$1000-R$2000\"")
        return

    if args.candidatura:
        track_application(
            title=args.candidatura, status=args.status, notes=args.nota,
            link=args.link, score=args.score, empresa=args.empresa,
            proximo_passo=args.proximo_passo,
        )
        print("\n[INFO] Rode 'python vagas_agent.py' para atualizar a nota completa.")
        return

    if args.schedule:
        print(f"Modo agendado: a cada {CONFIG['schedule_hours']}h")
        run_agent(send_email_flag=True, send_telegram_flag=True)
        schedule.every(CONFIG["schedule_hours"]).hours.do(lambda: run_agent(send_email_flag=True, send_telegram_flag=True))
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        run_agent(send_email_flag=args.email, send_telegram_flag=args.telegram)

if __name__ == "__main__":
    main()

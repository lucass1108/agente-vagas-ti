import streamlit as st
import json
import os
import sys
import re
import time
from datetime import datetime

# ============================================================
# GEMINI AI (gratuito)
# ============================================================
GEMINI_API_KEY = None
try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
except Exception:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Rate limiting para Gemini free tier (15 req/min)
if "gemini_last_call" not in st.session_state:
    st.session_state.gemini_last_call = 0
if "gemini_call_count" not in st.session_state:
    st.session_state.gemini_call_count = 0
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def gemini_available():
    """Verifica se pode fazer chamada ao Gemini (rate limit)."""
    now = time.time()
    # Reset contador a cada minuto
    if now - st.session_state.gemini_last_call > 60:
        st.session_state.gemini_call_count = 0
    if st.session_state.gemini_call_count >= 14:
        wait = 60 - (now - st.session_state.gemini_last_call)
        return False, max(0, int(wait))
    return True, 0

def call_gemini(prompt, context=""):
    """Chama a API do Gemini (gratuito)."""
    if not GEMINI_API_KEY:
        return "Chave do Gemini nao configurada. Adicione GEMINI_API_KEY nos Secrets do Streamlit."

    available, wait = gemini_available()
    if not available:
        return f"Limite de requisições atingido. Aguarde {wait} segundos e tente novamente."

    try:
        import urllib.request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        full_prompt = f"""Voce e um assistente de carreira especializado em vagas de TI para Lucas Barbosa Pedro.

PERFIL DO LUCAS:
- Nome: Lucas Barbosa Pedro
- Localizacao: Sao Paulo - SP
- Formacao: ADS (UNIFECAF, 2 semestre)
- Skills: Python, SQL, Flask, MySQL, Git, HTML/CSS, Windows, Redes, Linux
- Experiencia: Backoffice/Atendimento (Sercom/Claro) desde jan/2026
- Projetos: FinanceTracker (Python+Flask+MySQL), BrutalFit Expo (Python+MySQL)
- Diferenciais: Medalhista CUCO/USP (ouro), OBMEP, OMASP; ingles intermediario
- Objetivo: Jovem Aprendiz / Estagio em TI (suporte, dados ou desenvolvimento)

{context}

Responda de forma concisa e util. Use portugues brasileiro.

Pergunta do usuario: {prompt}"""

        data = json.dumps({
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
        }).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        text = result["candidates"][0]["content"]["parts"][0]["text"]

        st.session_state.gemini_last_call = time.time()
        st.session_state.gemini_call_count += 1
        return text
    except Exception as e:
        return f"Erro ao chamar Gemini: {str(e)}"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Buscador de Vagas TI",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS CUSTOMIZADO
# ============================================================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 { margin: 0; font-size: 2.2rem; }
    .main-header p { margin: 0.5rem 0 0 0; opacity: 0.9; }
    .admin-header {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    .admin-header h1 { margin: 0; font-size: 2.2rem; }
    .admin-header p { margin: 0.5rem 0 0 0; opacity: 0.9; }
    .job-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .score-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        color: white;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .score-high { background: #22c55e; }
    .score-med { background: #eab308; }
    .score-low { background: #ef4444; }
    .skill-tag {
        display: inline-block;
        background: #e0e7ff;
        color: #4338ca;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 2px;
    }
    .stat-card {
        background: white;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stat-number { font-size: 2rem; font-weight: bold; color: #667eea; }
    .stat-label { color: #666; font-size: 0.85rem; }
    .admin-badge {
        background: #f5576c;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# ESTADO DA SESSÃO
# ============================================================
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "resume_skills" not in st.session_state:
    st.session_state.resume_skills = []
if "jobs" not in st.session_state:
    st.session_state.jobs = []
if "searched" not in st.session_state:
    st.session_state.searched = False
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False
if "selected_area" not in st.session_state:
    st.session_state.selected_area = "Todas as vagas de TI"

# ============================================================
# FUNÇÕES DE ANÁLISE DE CURRÍCULO
# ============================================================
SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c#", "c++", "php", "ruby", "go", "rust",
    "sql", "mysql", "postgresql", "mongodb", "redis", "oracle", "sqlite",
    "html", "css", "react", "angular", "vue", "node", "django", "flask", "spring",
    "docker", "kubernetes", "aws", "azure", "gcp", "linux", "windows", "git", "github",
    "excel", "office", "power bi", "tableau", "figma", "photoshop",
    "redes", "networking", "tcp/ip", "dns", "wifi", "firewall",
    "suporte", "help desk", "atendimento", "backoffice",
    "dados", "data", "analytics", "machine learning",
    "scrum", "agile", "kanban", "jira", "trello",
    "ingles", "english", "espanhol", "spanish",
]

def extract_skills_from_text(text):
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        if skill in text_lower:
            found.append(skill)
    return list(set(found))

def extract_experience_years(text):
    patterns = [
        r'(\d+)\s*anos?\s*(?:de\s*)?experiência',
        r'(\d+)\s*years?\s*(?:of\s*)?experience',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return 0

# ============================================================
# FUNÇÕES DE BUSCA
# ============================================================
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

def fetch_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp
            time.sleep(2)
        except Exception:
            time.sleep(2)
    return None

def search_jobs(skills, area=""):
    area_queries = {
        "Todas as vagas de TI": [
            "jovem aprendiz ti São Paulo", "estágio ti São Paulo",
            "estágio ti suporte São Paulo", "estágio desenvolvimento São Paulo",
            "estágio dados São Paulo", "estágio help desk São Paulo",
            "trainee ti São Paulo",
        ],
        "Jovem Aprendiz TI": ["jovem aprendiz ti São Paulo", "jovem aprendiz tecnologia São Paulo", "jovem aprendiz informatica São Paulo"],
        "Estagio Suporte Tecnico": ["estágio suporte técnico São Paulo", "estágio suporte ti São Paulo", "estágio help desk São Paulo"],
        "Estagio Desenvolvimento (Backend)": ["estágio desenvolvimento backend São Paulo", "estágio desenvolvedor python São Paulo", "estágio back-end São Paulo"],
        "Estagio Desenvolvimento (Frontend)": ["estágio desenvolvimento frontend São Paulo", "estágio desenvolvedor web São Paulo", "estágio frontend react São Paulo"],
        "Estagio Desenvolvimento (Full Stack)": ["estágio desenvolvimento full stack São Paulo", "estágio desenvolvedor fullstack São Paulo"],
        "Estagio Dados / BI": ["estágio dados São Paulo", "estágio analista dados São Paulo", "estágio business intelligence São Paulo"],
        "Estagio Infraestrutura / Redes": ["estágio infraestrutura São Paulo", "estágio redes São Paulo", "estágio infra ti São Paulo"],
        "Estagio Help Desk": ["estágio help desk São Paulo", "estágio suporte técnico São Paulo"],
        "Estagio Analista de Sistemas": ["estágio analista sistemas São Paulo", "estágio analista ti São Paulo"],
        "Trainee TI": ["trainee ti São Paulo", "trainee tecnologia São Paulo"],
    }
    queries = area_queries.get(area, ["estágio ti São Paulo", "jovem aprendiz ti São Paulo"])
    for skill in skills[:3]:
        queries.append(f"estágio {skill} São Paulo")
    if area and area not in area_queries:
        queries.insert(0, f"estágio {area} São Paulo")

    jobs = []
    seen = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9",
    }
    for query in queries:
        try:
            url = f"https://www.bing.com/search?q={quote_plus(query)}"
            resp = fetch_with_retry(url, headers)
            if not resp:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
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
                         "hardware", "redes", "python", "sql", "flask", "mysql", "estágio", "estagio",
                         "aprendiz", "trainee", "jovem aprendiz"]
                if not any(kw in combined for kw in ti_kw):
                    continue
                other = ["rio de janeiro", "curitiba", "porto alegre", "belo horizonte", "salvador",
                         "fortaleza", "recife", "brasília", "manaus", "florianópolis"]
                if any(c in combined for c in other):
                    continue
                key = title.lower().strip()
                if key in seen:
                    continue
                seen.add(key)
                jobs.append({"title": title, "link": link, "description": snippet, "source": "Bing"})
            import time
            time.sleep(0.5)
        except Exception:
            pass
    return jobs

def score_job_generic(job, skills):
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    score = 0
    skill_hits = sum(1 for s in skills if s in text)
    score += min(skill_hits * 8, 40)
    ti_kw = ["ti", "tecnologia", "suporte", "desenvolvimento", "dados", "sistemas",
             "informática", "informatica", "help desk", "analista", "dev", "software"]
    area_hits = sum(1 for kw in ti_kw if kw in text)
    score += min(area_hits * 4, 20)
    level_kw = ["jovem aprendiz", "estágio", "estagiário", "aprendiz", "trainee", "estagiario"]
    if any(kw in text for kw in level_kw):
        score += 20
    if "são paulo" in text or "sao paulo" in text or "sp" in text:
        score += 10
    elif "remoto" in text or "híbrido" in text or "hibrido" in text:
        score += 8
    other_cities = ["rio de janeiro", "curitiba", "porto alegre", "belo horizonte", "salvador",
                    "fortaleza", "recife", "brasília", "manaus", "florianópolis"]
    if any(c in text for c in other_cities):
        score -= 30
    return max(0, min(100, score))

# ============================================================
# DADOS DO ADMIN (Lucas) — carregados apenas com chave
# ============================================================
ADMIN_PROFILE = {
    "name": "Lucas Barbosa Pedro",
    "location": "São Paulo - SP",
    "skills": ["python", "sql", "html", "css", "flask", "mysql", "git", "github",
               "windows", "excel", "office", "redes", "linux", "atendimento",
               "backoffice", "suporte"],
    "education": "ADS — UNIFECAF (2º semestre)",
    "experience": "Agente de Relacionamento I (Backoffice) — Sercom/Claro",
    "projects": ["FinanceTracker (Python, Flask, MySQL)", "BrutalFit Expo (Python, MySQL)"],
    "achievements": ["Medalha de ouro CUCO/USP", "Medalhista OBMEP", "Medalhista OMASP"],
}

# ============================================================
# VERIFICAÇÃO DE ADMIN
# ============================================================
ADMIN_KEY = os.environ.get("ADMIN_KEY", "Lucas0812")

def check_admin(key):
    return key == ADMIN_KEY

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## Buscador de Vagas TI")
    st.markdown("---")

    if st.session_state.admin_mode:
        st.markdown('<span class="admin-badge">MODO ADMIN</span>', unsafe_allow_html=True)
        st.markdown("---")
        page = st.radio("Menu", [
            "Buscar Vagas",
            "Meu Curriculo",
            "Candidaturas",
            "Prep Entrevista",
            "Curriculo Personalizado",
            "Analytics",
            "Agente IA",
            "Acesso Admin",
        ], label_visibility="collapsed")
    else:
        page = st.radio("Menu", [
            "Buscar Vagas",
            "Meu Curriculo",
            "Acesso Admin",
        ], label_visibility="collapsed")

    st.markdown("---")
    if not st.session_state.admin_mode:
        st.markdown("**Dica:** Cole seu curriculo para buscas personalizadas!")

# ============================================================
# HEADER
# ============================================================
if st.session_state.admin_mode:
    st.markdown("""
    <div class="admin-header">
        <h1>Painel Admin — Lucas</h1>
        <p>Modo administrador ativado. Todas as ferramentas disponíveis.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="main-header">
        <h1>Buscador de Vagas em TI</h1>
        <p>Encontre vagas de Jovem Aprendiz e Estagio em TI em Sao Paulo</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# PÁGINA: AGENTE IA (ADMIN)
# ============================================================
elif page == "Agente IA":
    if not st.session_state.admin_mode:
        st.error("Acesso restrito. Va para 'Acesso Admin' e insira sua chave.")
    else:
        st.title("Agente IA - Assistente de Carreira")
        st.markdown("Converse com o agente de IA para obter ajuda com vagas, candidaturas, entrevistas e carreira.")

        # Contexto atual
        context_parts = []
        try:
            from vagas_agent import load_applications, load_history, get_application_stats, get_followup_reminders
            apps = load_applications()
            history = load_history()
            reminders = get_followup_reminders()
            stats = get_application_stats()

            context_parts.append(f"CANDIDATURAS: {len(apps)} total, {stats['taxa_resposta']}% taxa de resposta")
            if apps:
                for app in apps[:5]:
                    context_parts.append(f"  - {app['vaga']} ({app.get('empresa','N/A')}) - Status: {app['status']}")
            if reminders:
                context_parts.append(f"FOLLOW-UPS PENDENTES: {len(reminders)}")
                for app, days in reminders:
                    context_parts.append(f"  - {app['vaga']} ({days} dias sem resposta)")
            context_parts.append(f"VAGAS VISTAS: {len(history.get('seen', []))}")
        except Exception:
            pass

        if st.session_state.jobs:
            jobs = st.session_state.jobs
            context_parts.append(f"VAGAS ENCONTRADAS NA ULTIMA BUSCA: {len(jobs)}")
            top = sorted(jobs, key=lambda j: __import__('vagas_agent').score_job_generic(j, st.session_state.resume_skills), reverse=True)[:5]
            for job in top:
                context_parts.append(f"  - {job['title'][:50]} (score: {__import__('vagas_agent').score_job_generic(job, st.session_state.resume_skills)})")

        if st.session_state.resume_skills:
            context_parts.append(f"SKILLS DO CURRICULO: {', '.join(st.session_state.resume_skills)}")

        context = "\n".join(context_parts)

        # Botoes de acao rapida
        st.subheader("Acoes rapidas")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("Buscar vagas"):
                st.session_state.chat_history.append({"role": "user", "content": "Busque vagas de TI em Sao Paulo para mim"})
                st.rerun()
        with col2:
            if st.button("Ver candidaturas"):
                st.session_state.chat_history.append({"role": "user", "content": "Liste minhas candidaturas e estatisticas"})
                st.rerun()
        with col3:
            if st.button("Follow-ups"):
                st.session_state.chat_history.append({"role": "user", "content": "Quais candidaturas precisam de follow-up?"})
                st.rerun()
        with col4:
            if st.button("Limpar chat"):
                st.session_state.chat_history = []
                st.rerun()

        # Exibir historico do chat
        st.subheader("Chat")
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f"**Voce:** {msg['content']}")
                else:
                    st.markdown(f"**Agente:** {msg['content']}")
                st.markdown("---")

        # Input do usuario
        user_input = st.text_input("Digite sua pergunta:", key="chat_input", placeholder="Ex: Quais vagas sao mais compatíveis com meu perfil?")
        if st.button("Enviar") and user_input.strip():
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            with st.spinner("Pensando..."):
                response = call_gemini(user_input, context)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()

        # Status do Gemini
        available, wait = gemini_available()
        if not available:
            st.warning(f"Limite de requisicoes atingido. Aguarde {wait}s.")
        else:
            st.caption(f"Gemini gratuito - {14 - st.session_state.gemini_call_count} requisicoes restantes neste minuto")

# ============================================================
# PÁGINA: ACESSO ADMIN
# ============================================================
if page == "Acesso Admin":
    st.title("Acesso Administrador")

    if st.session_state.admin_mode:
        st.success("Modo administrador ativado!")
        st.markdown(f"**Bem-vindo, {ADMIN_PROFILE['name']}!**")
        st.markdown(f"- Localização: {ADMIN_PROFILE['location']}")
        st.markdown(f"- Formação: {ADMIN_PROFILE['education']}")
        st.markdown(f"- Experiência: {ADMIN_PROFILE['experience']}")
        st.markdown(f"- Skills: {', '.join(ADMIN_PROFILE['skills'][:8])}")
        st.markdown(f"- Projetos: {', '.join(ADMIN_PROFILE['projects'])}")
        if st.button("Sair do modo admin"):
            st.session_state.admin_mode = False
            st.rerun()
    else:
        st.markdown("Insira sua chave de acesso para desbloquear o painel administrador.")
        key_input = st.text_input("Chave de acesso:", type="password", placeholder="Digite a chave...")
        if st.button("Entrar"):
            if check_admin(key_input):
                st.session_state.admin_mode = True
                st.success("Acesso concedido! Modo administrador ativado.")
                st.rerun()
            else:
                st.error("Chave inválida. Acesso negado.")

# ============================================================
# PÁGINA: MEU CURRÍCULO
# ============================================================
elif page == "Meu Curriculo":
    st.title("Meu Curriculo")
    st.markdown("Cole seu curriculo abaixo para que o buscador encontre vagas compatíveis com seu perfil.")

    st.subheader("Qual area/vaga voce busca?")
    area_options = [
        "Todas as vagas de TI",
        "Jovem Aprendiz TI",
        "Estagio Suporte Tecnico",
        "Estagio Desenvolvimento (Backend)",
        "Estagio Desenvolvimento (Frontend)",
        "Estagio Desenvolvimento (Full Stack)",
        "Estagio Dados / BI",
        "Estagio Infraestrutura / Redes",
        "Estagio Help Desk",
        "Estagio Analista de Sistemas",
        "Trainee TI",
        "Outro (personalizado)",
    ]
    selected_area = st.selectbox("Selecione a area desejada:", area_options)
    if selected_area == "Outro (personalizado)":
        custom_area = st.text_input("Digite a area/vaga desejada:")
        selected_area = custom_area if custom_area else "Estagio TI"

    st.session_state.selected_area = selected_area
    st.info(f"Area selecionada: {selected_area}")

    col1, col2 = st.columns([2, 1])

    with col1:
        resume_input = st.text_area(
            "Cole seu curriculo aqui:",
            value=st.session_state.resume_text,
            height=300,
            placeholder="Cole o texto do seu curriculo...\n\nExemplo:\nNome: João Silva\nObjetivo: Estágio em TI\nHabilidades: Python, SQL, Excel...\nExperiência: ...\nFormação: ...",
        )

        uploaded_file = st.file_uploader("Ou envie um arquivo (.txt)", type=["txt"])
        if uploaded_file:
            resume_input = uploaded_file.read().decode("utf-8")

        if st.button("Analisar Curriculo", type="primary"):
            if resume_input.strip():
                st.session_state.resume_text = resume_input
                skills = extract_skills_from_text(resume_input)
                st.session_state.resume_skills = skills
                exp_years = extract_experience_years(resume_input)
                st.success(f"Curriculo analisado! {len(skills)} skills encontradas.")

                st.subheader("Skills detectadas:")
                for skill in skills:
                    st.markdown(f'<span class="skill-tag">{skill}</span>', unsafe_allow_html=True)

                if exp_years > 0:
                    st.info(f"Experiencia estimada: {exp_years} anos")
            else:
                st.warning("Cole ou envie um curriculo primeiro.")

    with col2:
        if st.session_state.resume_skills:
            st.subheader("Resumo do Perfil")
            st.markdown(f"**Skills ({len(st.session_state.resume_skills)}):**")
            for skill in st.session_state.resume_skills:
                st.markdown(f"- {skill}")
        else:
            st.info("Nenhum curriculo analisado ainda.")

# ============================================================
# PÁGINA: BUSCAR VAGAS
# ============================================================
elif page == "Buscar Vagas":
    st.title("Buscar Vagas")

    skills = st.session_state.resume_skills
    area = st.session_state.get("selected_area", "Todas as vagas de TI")

    if not skills:
        st.warning("Nenhum curriculo analisado. Vá para 'Meu Curriculo' para melhores resultados.")
        st.info("Buscando com termos genericos de TI...")

    st.info(f"Area: {area} | Skills: {', '.join(skills) if skills else 'nenhuma'}")

    if st.button("Buscar Vagas Agora", type="primary"):
        with st.spinner("Buscando vagas... (pode levar ate 30s)"):
            try:
                jobs = search_jobs(skills, area)
                st.session_state.jobs = jobs
                st.session_state.searched = True

                if len(jobs) == 0:
                    st.warning("Nenhuma vaga encontrada. Tente novamente.")
                else:
                    st.success(f"{len(jobs)} vagas encontradas!")
            except Exception as e:
                st.error(f"Erro na busca: {str(e)}")
                st.session_state.jobs = []
                st.session_state.searched = True

    if st.session_state.searched and st.session_state.jobs:
        jobs = st.session_state.jobs
        scored = sorted(jobs, key=lambda j: score_job_generic(j, skills), reverse=True)

        st.subheader(f"Resultados ({len(scored)} vagas)")

        for job in scored[:30]:
            s = score_job_generic(job, skills)
            color_class = "score-high" if s >= 70 else ("score-med" if s >= 40 else "score-low")
            with st.expander(f"[{s}] {job['title'][:70]}"):
                st.markdown(f'<span class="score-badge {color_class}">{s}/100</span>', unsafe_allow_html=True)
                st.markdown(f"**Fonte:** {job.get('source', '?')}")
                st.markdown(f"**Descricao:** {job['description'][:200]}")
                st.markdown(f"**Link:** [{job['link']}]({job['link']})")

                job_text = (job.get("title", "") + " " + job.get("description", "")).lower()
                matched = [sk for sk in skills if sk in job_text]
                if matched:
                    st.markdown("**Skills que combinam:** " + ", ".join(matched))

# ============================================================
# PÁGINAS ADMIN (apenas com chave)
# ============================================================
elif page == "Candidaturas":
    if not st.session_state.admin_mode:
        st.error("Acesso restrito. Va para 'Acesso Admin' e insira sua chave.")
    else:
        st.title("Minhas Candidaturas")
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from vagas_agent import load_applications, get_application_stats, APPLICATION_STATUSES, track_application, get_followup_reminders
            apps = load_applications()
            if not apps:
                st.info("Nenhuma candidatura registrada ainda.")
            else:
                import pandas as pd
                df = pd.DataFrame([{
                    "Vaga": a["vaga"][:40],
                    "Empresa": a.get("empresa", "N/A"),
                    "Status": APPLICATION_STATUSES.get(a["status"], {}).get("label", a["status"]),
                    "Data": a.get("data_candidatura", "N/A"),
                    "Score": a.get("score", 0),
                } for a in apps])
                st.dataframe(df, use_container_width=True)

            stats = get_application_stats()
            st.subheader("Estatisticas")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total", stats["total"])
            col2.metric("Taxa de Resposta", f"{stats['taxa_resposta']}%")
            col3.metric("Taxa de Entrevista", f"{stats['taxa_entrevista']}%")

            reminders = get_followup_reminders()
            if reminders:
                st.subheader("Follow-ups Pendentes")
                for app, days in reminders:
                    st.warning(f"{app['vaga']} - {days} dias sem resposta")
        except Exception as e:
            st.error(f"Erro ao carregar candidaturas: {e}")

elif page == "Prep Entrevista":
    if not st.session_state.admin_mode:
        st.error("Acesso restrito. Va para 'Acesso Admin' e insira sua chave.")
    else:
        st.title("Preparacao para Entrevista")
        try:
            from vagas_agent import load_applications, generate_interview_prep
            apps = load_applications()
            if not apps:
                st.info("Registre candidaturas primeiro.")
            else:
                vaga_sel = st.selectbox("Selecione a vaga", [a["vaga"] for a in apps])
                if st.button("Gerar Prep de Entrevista"):
                    with st.spinner("Gerando..."):
                        content = generate_interview_prep(vaga_sel)
                    st.markdown(content)
        except Exception as e:
            st.error(f"Erro: {e}")

elif page == "Curriculo Personalizado":
    if not st.session_state.admin_mode:
        st.error("Acesso restrito. Va para 'Acesso Admin' e insira sua chave.")
    else:
        st.title("Curriculo Personalizado")
        try:
            from vagas_agent import load_applications, generate_tailored_resume
            apps = load_applications()
            if not apps:
                st.info("Registre candidaturas primeiro.")
            else:
                vaga_sel = st.selectbox("Selecione a vaga", [a["vaga"] for a in apps])
                if st.button("Gerar Curriculo Personalizado"):
                    with st.spinner("Gerando..."):
                        content = generate_tailored_resume(vaga_sel)
                    st.markdown(content)
        except Exception as e:
            st.error(f"Erro: {e}")

elif page == "Analytics":
    if not st.session_state.admin_mode:
        st.error("Acesso restrito. Va para 'Acesso Admin' e insira sua chave.")
    else:
        st.title("Analytics")
        try:
            from vagas_agent import load_applications, get_application_stats, APPLICATION_STATUSES, load_history
            apps = load_applications()
            history = load_history()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Vagas vistas", len(history.get("seen", [])))
            col2.metric("Candidaturas", len(apps))
            stats = get_application_stats()
            col3.metric("Taxa de resposta", f"{stats['taxa_resposta']}%")
            col4.metric("Taxa de entrevista", f"{stats['taxa_entrevista']}%")

            if apps:
                import pandas as pd
                df = pd.DataFrame([{
                    "Data": a.get("data_candidatura", "N/A"),
                    "Vaga": a["vaga"][:30],
                    "Status": APPLICATION_STATUSES.get(a["status"], {}).get("label", a["status"]),
                    "Score": a.get("score", 0),
                } for a in apps])
                st.subheader("Timeline de Candidaturas")
                st.dataframe(df, use_container_width=True)

                st.subheader("Distribuicao de Status")
                status_counts = {}
                for a in apps:
                    st_label = APPLICATION_STATUSES.get(a["status"], {}).get("label", a["status"])
                    status_counts[st_label] = status_counts.get(st_label, 0) + 1
                st.bar_chart(status_counts)

            if st.session_state.jobs:
                jobs = st.session_state.jobs
                skills = st.session_state.resume_skills
                scored = sorted(jobs, key=lambda j: score_job_generic(j, skills), reverse=True)
                st.subheader(f"Distribuicao de Scores ({len(scored)} vagas)")
                score_dist = {}
                for job in scored:
                    s = score_job_generic(job, skills)
                    bucket = "70-100" if s >= 70 else ("40-69" if s >= 40 else "0-39")
                    score_dist[bucket] = score_dist.get(bucket, 0) + 1
                st.bar_chart(score_dist)
        except Exception as e:
            st.error(f"Erro: {e}")

# ============================================================
# RODAPÉ
# ============================================================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #999; font-size: 0.8rem;'>"
    "Buscador de Vagas em TI - Sao Paulo"
    "</div>",
    unsafe_allow_html=True,
)

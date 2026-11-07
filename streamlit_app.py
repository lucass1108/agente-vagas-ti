import streamlit as st
import json
import os
import sys
import re
from datetime import datetime

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
# CSS CUSTOMIZADO (design bonito)
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
    .job-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1.2rem;
        margin: 0.8rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: box-shadow 0.2s;
    }
    .job-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
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
    .sidebar-section { padding: 0.5rem 0; }
    .upload-box {
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        background: #f8f9ff;
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
    "dados", "data", "analytics", "machine learning", "ia", "ai",
    "scrum", "agile", "kanban", "jira", "trello",
    "ingles", "english", "espanhol", "spanish",
]

def extract_skills_from_text(text):
    """Extrai skills de um texto de currículo."""
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        if skill in text_lower:
            found.append(skill)
    return list(set(found))

def extract_experience_years(text):
    """Estima anos de experiência."""
    patterns = [
        r'(\d+)\s*anos?\s*(?:de\s*)?experiência',
        r'(\d+)\s*years?\s*(?:of\s*)?experience',
        r'experiência.*?(\d+)\s*anos?',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return 0

def score_job_generic(job, skills):
    """Pontua uma vaga com base nas skills do currículo."""
    text = (job.get("title", "") + " " + job.get("description", "")).lower()
    score = 0

    # Skills match (40 pts max)
    skill_hits = sum(1 for s in skills if s in text)
    score += min(skill_hits * 8, 40)

    # Área TI (20 pts)
    ti_kw = ["ti", "tecnologia", "suporte", "desenvolvimento", "dados", "sistemas",
             "informática", "informatica", "help desk", "analista", "dev", "software"]
    area_hits = sum(1 for kw in ti_kw if kw in text)
    score += min(area_hits * 4, 20)

    # Nível (20 pts)
    level_kw = ["jovem aprendiz", "estágio", "estagiário", "aprendiz", "trainee", "estagiario"]
    if any(kw in text for kw in level_kw):
        score += 20

    # Localização SP (10 pts)
    if "são paulo" in text or "sao paulo" in text or "sp" in text:
        score += 10
    elif "remoto" in text or "híbrido" in text or "hibrido" in text:
        score += 8

    # Penalidades
    other_cities = ["rio de janeiro", "curitiba", "porto alegre", "belo horizonte", "salvador",
                    "fortaleza", "recife", "brasília", "manaus", "florianópolis"]
    if any(c in text for c in other_cities):
        score -= 30

    return max(0, min(100, score))

# ============================================================
# FUNÇÕES DE BUSCA
# ============================================================
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin

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

def search_bing(query):
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9",
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
        combined = (title + " " + snippet).lower()
        ti_kw = ["ti", "tecnologia", "suporte", "desenvolvimento", "dados", "sistemas",
                 "informática", "informatica", "help desk", "analista", "dev", "software",
                 "hardware", "redes", "python", "sql", "flask", "mysql", "estágio", "estagio",
                 "aprendiz", "trainee", "jovem aprendiz"]
        if not any(kw in combined for kw in ti_kw):
            continue
        # Filtra São Paulo
        other = ["rio de janeiro", "curitiba", "porto alegre", "belo horizonte", "salvador",
                 "fortaleza", "recife", "brasília", "manaus", "florianópolis", "campinas"]
        if any(c in combined for c in other):
            continue
        results.append({"title": title, "link": link, "description": snippet, "source": "Bing"})
    return results

def search_jobs(skills, area=""):
    area_queries = {
        "Todas as vagas de TI": ["jovem aprendiz ti São Paulo", "estágio ti São Paulo", "estágio ti suporte São Paulo", "estágio desenvolvimento São Paulo", "estágio dados São Paulo", "estágio help desk São Paulo", "trainee ti São Paulo"],
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
    # Adiciona skills do currículo às queries
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
                         "python", "sql", "flask", "mysql", "estágio", "estagio", "aprendiz",
                         "trainee", "jovem aprendiz"]
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

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("## Buscador de Vagas TI")
    st.markdown("---")
    page = st.radio("Menu", [
        "Buscar Vagas",
        "Meu Curriculo",
        "Candidaturas",
        "Prep Entrevista",
        "Analytics",
    ], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("**Dica:** Cole seu curriculo na aba 'Meu Curriculo' para buscas personalizadas!")

# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div class="main-header">
    <h1>Buscador de Vagas em TI</h1>
    <p>Encontre vagas de Jovem Aprendiz e Estagio em TI em Sao Paulo</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# PÁGINA: MEU CURRÍCULO
# ============================================================
if page == "Meu Curriculo":
    st.title("Meu Curriculo")
    st.markdown("Cole seu curriculo abaixo para que o buscador encontre vagas compatíveis com seu perfil.")

    col1, col2 = st.columns([2, 1])

    with col1:
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

        resume_input = st.text_area(
            "Cole seu curriculo aqui:",
            value=st.session_state.resume_text,
            height=400,
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
    if not skills:
        st.warning("Nenhum curriculo analisado. Vá para 'Meu Curriculo' para melhores resultados.")
        st.info("Buscando com termos genericos de TI...")

    if st.button("Buscar Vagas Agora", type="primary"):
        with st.spinner("Buscando vagas... (pode levar ate 30s)"):
            area = st.session_state.get("selected_area", "")
            jobs = search_jobs(skills, area)
            st.session_state.jobs = jobs
            st.session_state.searched = True

        if len(jobs) == 0:
            st.warning("Nenhuma vaga encontrada. Tente novamente.")
        else:
            st.success(f"{len(jobs)} vagas encontradas!")

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

                # Skills match
                job_text = (job.get("title", "") + " " + job.get("description", "")).lower()
                matched = [sk for sk in skills if sk in job_text]
                if matched:
                    st.markdown("**Skills que combinam:** " + ", ".join(matched))

# ============================================================
# PÁGINA: CANDIDATURAS
# ============================================================
elif page == "Candidaturas":
    st.title("Minhas Candidaturas")
    st.info("Funcionalidade de candidaturas disponível na versao local (python vagas_agent.py)")

# ============================================================
# PÁGINA: PREP ENTREVISTA
# ============================================================
elif page == "Prep Entrevista":
    st.title("Preparacao para Entrevista")
    st.info("Funcionalidade disponível na versao local. Use: python vagas_agent.py --entrevista \"Nome da vaga\"")

# ============================================================
# PÁGINA: ANALYTICS
# ============================================================
elif page == "Analytics":
    st.title("Analytics")
    st.info("Analytics completo disponível na versao local. Use: python vagas_agent.py --analytics")

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

# ============================================================
# RODAPÉ
# ============================================================
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #999; font-size: 0.8rem;'>"
    "Buscador de Vagas em TI - Sao Paulo | Desenvolvido com Streamlit"
    "</div>",
    unsafe_allow_html=True,
)

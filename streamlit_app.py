import streamlit as st
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vagas_agent import (
    CONFIG, PROFILE, score_job, search_jobs, deduplicate,
    load_history, save_history, get_new_jobs,
    load_applications, save_applications, find_application,
    track_application, get_followup_reminders, get_application_stats,
    APPLICATION_STATUSES, generate_interview_prep, generate_tailored_resume,
    extract_salary, load_salaries,
)

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Agente Vagas TI - Lucas",
    page_icon="🤖",
    layout="wide",
)

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.title("🤖 Agente Vagas TI")
st.sidebar.markdown(f"**Lucas Barbosa Pedro**")
st.sidebar.markdown(f"ADS — UNIFECAF (2º sem)")
st.sidebar.markdown("---")

page = st.sidebar.radio("Navegação", [
    "🔍 Buscar Vagas",
    "📋 Candidaturas",
    "🎯 Prep Entrevista",
    "📄 Currículo",
    "📊 Analytics",
    "⚙️ Configurações",
])

st.sidebar.markdown("---")
st.sidebar.markdown("**Comandos rápidos:**")
st.sidebar.code("python vagas_agent.py --email")
st.sidebar.code("python vagas_agent.py --telegram")

# ============================================================
# PÁGINA: BUSCAR VAGAS
# ============================================================
if page == "🔍 Buscar Vagas":
    st.title("🔍 Buscar Vagas de TI")
    st.markdown("Busca vagas de Jovem Aprendiz e Estágio em TI compatíveis com seu perfil.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Buscar Vagas Agora", type="primary"):
            with st.spinner("Buscando vagas..."):
                jobs = search_jobs()
                jobs = deduplicate(jobs)
                history = load_history()
                new_jobs = get_new_jobs(jobs, history)
                save_history(jobs)

                st.success(f"✅ {len(jobs)} vagas encontradas! ({len(new_jobs)} novas)")

                # Top vagas
                scored = sorted(jobs, key=score_job, reverse=True)
                st.subheader(f"🟢 Top Matches ({len([j for j in scored if score_job(j) >= 70])})")
                for job in [j for j in scored if score_job(j) >= 70][:10]:
                    s = score_job(job)
                    color = "green" if s >= 70 else "orange"
                    with st.expander(f"[{s}] {job['title'][:60]}"):
                        st.markdown(f"**Score:** {s}/100")
                        st.markdown(f"**Fonte:** {job.get('source', '?')}")
                        st.markdown(f"**Descrição:** {job['description'][:200]}")
                        st.markdown(f"**Link:** [{job['link']}]({job['link']})")

                        # Botão para registrar candidatura
                        if st.button(f"Registrar candidatura", key=f"reg_{job['title'][:20]}"):
                            track_application(
                                title=job["title"],
                                status="candidatado",
                                link=job["link"],
                                score=s,
                            )
                            st.success("Candidatura registrada!")

                st.subheader(f"🟡 Matches Médios ({len([j for j in scored if 40 <= score_job(j) < 70])})")
                for job in [j for j in scored if 40 <= score_job(j) < 70][:10]:
                    s = score_job(job)
                    with st.expander(f"[{s}] {job['title'][:60]}"):
                        st.markdown(f"**Score:** {s}/100 | **Fonte:** {job.get('source', '?')}")
                        st.markdown(f"**Link:** [{job['link']}]({job['link']})")

    with col2:
        st.subheader("🆕 Vagas Novas")
        history = load_history()
        if history.get("last_run"):
            st.info(f"Última busca: {history['last_run']}")
        else:
            st.warning("Nenhuma busca realizada ainda.")

        reminders = get_followup_reminders()
        if reminders:
            st.subheader("⏰ Follow-ups Pendentes")
            for app, days in reminders:
                st.warning(f"{app['vaga']} — {days} dias sem resposta")

# ============================================================
# PÁGINA: CANDIDATURAS
# ============================================================
elif page == "📋 Candidaturas":
    st.title("📋 Minhas Candidaturas")

    apps = load_applications()
    if not apps:
        st.info("Nenhuma candidatura registrada ainda.")
    else:
        # Tabela
        import pandas as pd
        df = pd.DataFrame([{
            "Vaga": a["vaga"][:40],
            "Empresa": a.get("empresa", "N/A"),
            "Status": APPLICATION_STATUSES.get(a["status"], {}).get("label", a["status"]),
            "Data": a.get("data_candidatura", "N/A"),
            "Score": a.get("score", 0),
        } for a in apps])
        st.dataframe(df, use_container_width=True)

        # Atualizar status
        st.subheader("Atualizar Status")
        col1, col2, col3 = st.columns(3)
        with col1:
            vaga_sel = st.selectbox("Vaga", [a["vaga"] for a in apps])
        with col2:
            new_status = st.selectbox("Novo Status", list(APPLICATION_STATUSES.keys()),
                                     format_func=lambda x: APPLICATION_STATUSES[x]["label"])
        with col3:
            if st.button("Atualizar"):
                track_application(title=vaga_sel, status=new_status)
                st.success(f"Status atualizado para {APPLICATION_STATUSES[new_status]['label']}")
                st.rerun()

        # Estatísticas
        stats = get_application_stats()
        st.subheader("📊 Estatísticas")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total", stats["total"])
        col2.metric("Taxa de Resposta", f"{stats['taxa_resposta']}%")
        col3.metric("Taxa de Entrevista", f"{stats['taxa_entrevista']}%")

        for st_key, st_info in APPLICATION_STATUSES.items():
            if stats[st_key] > 0:
                st.markdown(f"{st_info['icon']} {st_info['label']}: **{stats[st_key]}**")

# ============================================================
# PÁGINA: PREP ENTREVISTA
# ============================================================
elif page == "🎯 Prep Entrevista":
    st.title("🎯 Preparação para Entrevista")

    apps = load_applications()
    if not apps:
        st.info("Registre candidaturas primeiro para gerar prep de entrevista.")
    else:
        vaga_sel = st.selectbox("Selecione a vaga", [a["vaga"] for a in apps])
        if st.button("Gerar Prep de Entrevista"):
            with st.spinner("Gerando..."):
                content = generate_interview_prep(vaga_sel)
            st.markdown(content)

# ============================================================
# PÁGINA: CURRÍCULO
# ============================================================
elif page == "📄 Currículo":
    st.title("📄 Currículo Personalizado")

    apps = load_applications()
    if not apps:
        st.info("Registre candidaturas primeiro para gerar currículo personalizado.")
    else:
        vaga_sel = st.selectbox("Selecione a vaga", [a["vaga"] for a in apps])
        if st.button("Gerar Currículo Personalizado"):
            with st.spinner("Gerando..."):
                content = generate_tailored_resume(vaga_sel)
            st.markdown(content)

# ============================================================
# PÁGINA: ANALYTICS
# ============================================================
elif page == "📊 Analytics":
    st.title("📊 Analytics")

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

        # Gráfico de status
        st.subheader("Distribuição de Status")
        status_counts = {}
        for a in apps:
            st_label = APPLICATION_STATUSES.get(a["status"], {}).get("label", a["status"])
            status_counts[st_label] = status_counts.get(st_label, 0) + 1
        st.bar_chart(status_counts)

    # Follow-ups
    reminders = get_followup_reminders()
    if reminders:
        st.subheader("⏰ Follow-ups Pendentes")
        for app, days in reminders:
            st.warning(f"{app['vaga']} — {days} dias sem resposta")

# ============================================================
# PÁGINA: CONFIGURAÇÕES
# ============================================================
elif page == "⚙️ Configurações":
    st.title("⚙️ Configurações")

    st.subheader("Perfil do Candidato")
    st.json(PROFILE)

    st.subheader("Configuração Atual")
    st.json({k: v for k, v in CONFIG.items() if "password" not in k and "token" not in k})

    st.subheader("Como configurar Telegram")
    st.markdown("""
    1. Abra o Telegram e procure por **@BotFather**
    2. Envie `/newbot` e siga as instruções
    3. Copie o **token** do bot
    4. Configure a variável de ambiente `TELEGRAM_BOT_TOKEN`
    5. Obtenha seu Chat ID enviando uma mensagem para o bot e acessando:
       `https://api.telegram.org/bot<TOKEN>/getUpdates`
    6. Configure `TELEGRAM_CHAT_ID`
    7. Rode: `python telegram_bot.py`
    """)

    st.subheader("Como hospedar no Streamlit Cloud")
    st.markdown("""
    1. Acesse [streamlit.io/cloud](https://streamlit.io/cloud)
    2. Conecte seu repositório GitHub
    3. Selecione `streamlit_app.py` como arquivo principal
    4. Configure as variáveis de ambiente (EMAIL_PASSWORD, etc.)
    5. Clique em Deploy!
    """)

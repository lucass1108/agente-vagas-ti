import json
import random
import time
from datetime import datetime
from pathlib import Path

# ==============================================================================
# CONFIGURAÇÕES E PERFIL BASE (LUCAS BARBOSA PEDRO)
# ==============================================================================
PERFIL_LUCAS = {
    "nome": "Lucas Barbosa Pedro",
    "telefone": "(11) 91508-2460",
    "email": "lucasbarbosapedro1108@gmail.com",
    "localizacao": "Taboão da Serra - SP",
    "linkedin": "https://linkedin.com/in/lucasbarbosapedro",
    "github": "https://github.com/lucass1108",
    "objetivo": "Jovem Aprendiz / Estágio na área de TI (suporte, dados ou desenvolvimento)",
    "formacao": "Tecnólogo em Análise e Desenvolvimento de Sistemas (UNIFECAF - 2º semestre)",
    "experiencia": "Agente de Relacionamento I (Backoffice) na Sercom Contact Center / Claro (Jan/2026 - Atual)",
    "skills": [
        "Python", "SQL", "Flask", "MySQL", "Git", "GitHub",
        "HTML", "CSS", "Windows", "Redes (IP, DNS, Wi-Fi)", "Linux", "Pacote Office/Excel"
    ],
    "projetos": [
        "FinanceTracker (Python, Flask, MySQL, Blueprints)",
        "BrutalFit Expo (Python, MySQL, CRUD completo)"
    ],
    "diferenciais": "Medalhista de ouro na CUCO/USP, medalhista na OBMEP e OMASP, Inglês intermediário (CNA)"
}

# ==============================================================================
# CONFIGURAÇÕES DE SEGURANÇA
# ==============================================================================
BASE_DIR = Path(__file__).parent
DELAY_ENTRE_ENVIOS_SEG = 90       # segundos entre envios (mínimo recomendado)
LIMITE_DIARIO = 10                # máximo de envios por dia
ARQUIVO_ULTIMO_ENVIO = BASE_DIR / ".ultimo_envio_linkedin.json"
LOG_JSON = BASE_DIR / "candidaturas_linkedin.json"
LOG_OBSIDIAN = BASE_DIR / "Log - Candidaturas LinkedIn.md"
MENSAGENS_MD = BASE_DIR / "Mensagens LinkedIn - Para Enviar.md"


def salvar_mensagem_para_envio(registro: dict) -> None:
    if not MENSAGENS_MD.exists():
        MENSAGENS_MD.write_text("# Mensagens LinkedIn — Para Enviar\n\n", encoding="utf-8")
    bloco = (
        f"## {registro['empresa']} — {registro['cargo']}\n"
        f"- **Recrutador:** {registro.get('recrutador', '-')}\n"
        f"- **Link da vaga:** {registro.get('url', '-')}\n"
        f"- **Perfil do recrutador:** {registro.get('perfil_recrutador_url', '-')}\n\n"
        f"```\n{registro['mensagem_enviada']}\n```\n\n"
        f"> Copie a mensagem acima e envie no LinkedIn (celular ou navegador).\n\n---\n\n"
    )
    with open(MENSAGENS_MD, "a", encoding="utf-8") as f:
        f.write(bloco)
CDP_URL = "http://localhost:9222"


def enviar_mensagem_linkedin_playwright(perfil_recrutador_url: str, mensagem: str) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("\n⚠️ Playwright não está instalado. Rode: pip install playwright && python -m playwright install chromium")
        return False

    print("\n🌐 Conectando ao navegador para enviar a mensagem...")
    with sync_playwright() as p:
        # Tenta conectar ao Chrome/Edge já aberto (evita bloqueio de segurança)
        browser = None
        context = None
        via_cdp = False
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            via_cdp = True
            print("🔗 Conectado ao navegador existente via CDP.")
        except Exception:
            print("⚠️ Navegador com debug não encontrado. Abrindo Chromium persistente.")
            context = p.chromium.launch_persistent_context(user_data_dir=str(SESSION_DIR), headless=False)

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(perfil_recrutador_url, timeout=60000)
        time.sleep(3)

        if "login" in page.url or "uas/login" in page.url:
            input("🔐 Faça login no LinkedIn no navegador aberto e pressione ENTER para continuar...")
            page.goto(perfil_recrutador_url, timeout=60000)
            time.sleep(3)

        try:
            # 1) Tenta "Enviar mensagem" (1º grau / Open Profile)
            btn_msg = page.locator("button:has-text('Enviar mensagem'), button:has-text('Message')").first
            if btn_msg.count() > 0 and btn_msg.is_visible():
                btn_msg.click(timeout=10000)
                time.sleep(2)
                caixa = page.locator("div.msg-form__contenteditable[role='textbox']").first
                caixa.fill(mensagem)
                time.sleep(1)
                print("📝 Mensagem preenchida. Clique em ENVIAR no navegador e pressione ENTER aqui para registrar.")
                input()
                if not via_cdp:
                    context.close()
                return True

            # 2) Fallback: "Conectar" + nota (2º/3º grau)
            btn_conn = page.locator("button:has-text('Conectar'), button:has-text('Connect')").first
            if btn_conn.count() > 0 and btn_conn.is_visible():
                btn_conn.click(timeout=10000)
                time.sleep(2)
                btn_nota = page.locator("button:has-text('Adicionar nota'), button:has-text('Add a note')").first
                if btn_nota.count() > 0:
                    btn_nota.click(timeout=10000)
                    time.sleep(1)
                    caixa_nota = page.locator("textarea[name='message'], textarea#custom-message").first
                    caixa_nota.fill(mensagem[:300])
                    time.sleep(1)
                    print("📝 Nota preenchida (300 chars). Clique em ENVIAR no navegador e pressione ENTER aqui para registrar.")
                    input()
                    if not via_cdp:
                        context.close()
                    return True
                else:
                    print("⚠️ Sem opção de nota. Envie o convite manualmente e pressione ENTER.")
                    input()
                    if not via_cdp:
                        context.close()
                    return True

            print("⚠️ Nenhum botão de mensagem/conexão encontrado. Envie manualmente.")
            input("Pressione ENTER após finalizar no navegador...")
            if not via_cdp:
                context.close()
            return False
        except Exception as e:
            print(f"⚠️ Não foi possível enviar automaticamente ({e}). Cole manualmente no navegador.")
            input("Pressione ENTER após finalizar no navegador...")
            if not via_cdp:
                context.close()
            return False


# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def carregar_log() -> list:
    if LOG_JSON.exists():
        try:
            with open(LOG_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def salvar_log(registros: list) -> None:
    with open(LOG_JSON, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)


def registrar_no_obsidian(registro: dict) -> None:
    cabecalho = "# Log de Candidaturas — LinkedIn\n\n| Data | Empresa | Cargo | Recrutador | Status | Link |\n|---|---|---|---|---|---|\n"
    if not LOG_OBSIDIAN.exists():
        LOG_OBSIDIAN.write_text(cabecalho, encoding="utf-8")

    linha = (
        f"| {registro['data']} | {registro['empresa']} | {registro['cargo']} | "
        f"{registro.get('recrutador', '-')} | {registro['status']} | {registro.get('url', '-')} |\n"
    )
    with open(LOG_OBSIDIAN, "a", encoding="utf-8") as f:
        f.write(linha)


# ==============================================================================
# GERAÇÃO DE CONTEÚDO PERSONALIZADO (NADA GENÉRICO)
# ==============================================================================
def identificar_pontos_fortes(requisitos_vaga: str) -> str:
    req_lower = requisitos_vaga.lower()
    matches = []

    mapa_skills = {
        "python": "projetos práticos em Python e Flask (FinanceTracker e BrutalFit Expo)",
        "sql": "modelagem relacional e consultas em MySQL",
        "mysql": "experiência prática com MySQL e integridade relacional",
        "suporte": "conhecimentos em Windows, redes (IP, DNS, Wi-Fi) e experiência em atendimento/backoffice",
        "redes": "base sólida em redes (IP, DNS, Wi-Fi) e infraestrutura Windows/Linux",
        "dados": "lógica analítica (medalhista CUCO/USP e OBMEP) e SQL/Excel",
        "git": "versionamento com Git e GitHub",
        "atendimento": "experiência atual em backoffice e cumprimento de SLA na Sercom/Claro",
    }

    for chave, descricao in mapa_skills.items():
        if chave in req_lower:
            matches.append(descricao)

    if not matches:
        matches.append("projetos práticos em Python/MySQL e experiência atual em backoffice na Sercom/Claro")

    return "; ".join(matches[:3])


def gerar_mensagem_recrutador(recrutador: str, cargo: str, empresa: str, requisitos: str) -> str:
    nome = recrutador.strip() if recrutador.strip() else "tudo bem"
    saudacao = f"Olá {nome}," if recrutador.strip() else "Olá,"
    pontos_fortes = identificar_pontos_fortes(requisitos)
    req_lower = requisitos.lower()

    # Escolhe um gancho específico conforme a área da vaga
    if any(k in req_lower for k in ["suporte", "infra", "redes", "helpdesk", "service desk"]):
        gancho = (
            f"Hoje atuo com backoffice e atendimento na Sercom (Claro), lidando diariamente com SLA e resolução de demandas, "
            f"e estou buscando minha transição para {cargo} na {empresa}. Tenho base em {pontos_fortes}."
        )
    elif any(k in req_lower for k in ["dados", "bi", "sql", "analytics", "excel"]):
        gancho = (
            f"Como medalhista de ouro na CUCO/USP e na OBMEP, tenho forte perfil analítico e venho aplicando isso em {pontos_fortes}. "
            f"Acompanho o trabalho da {empresa} e quero muito contribuir no time de {cargo}."
        )
    else:
        gancho = (
            f"Venho construindo aplicações reais no GitHub — como o FinanceTracker e o BrutalFit Expo — focando em {pontos_fortes}. "
            f"Vi a oportunidade de {cargo} na {empresa} e achei o desafio super alinhado ao meu momento em ADS (UNIFECAF)."
        )

    fechamentos = [
        f"Se fizer sentido para o time da {empresa}, adoraria conversar rápido sobre como posso somar. Meu GitHub: {PERFIL_LUCAS['github']}",
        f"Posso te enviar meu currículo por aqui ou agendar um papo breve? Deixo meu GitHub caso queira ver os códigos: {PERFIL_LUCAS['github']}",
        f"Fico à disposição para bater um papo sobre a vaga! Segue meu GitHub com os projetos: {PERFIL_LUCAS['github']}",
    ]

    return f"{saudacao} tudo bem? {gancho} {random.choice(fechamentos)}"


def gerar_dados_formulario(cargo: str, empresa: str, requisitos: str) -> dict:
    pontos_fortes = identificar_pontos_fortes(requisitos)
    resumo_adaptado = (
        f"Estudante de ADS (UNIFECAF, 2º semestre) buscando oportunidade de {cargo} na {empresa}. "
        f"Destaques alinhados à vaga: {pontos_fortes}. "
        f"Experiência atual com atendimento e backoffice (Sercom/Claro) e medalhista em olimpíadas científicas (CUCO/USP, OBMEP)."
    )
    return {
        "nome_completo": PERFIL_LUCAS["nome"],
        "email": PERFIL_LUCAS["email"],
        "telefone": PERFIL_LUCAS["telefone"],
        "cidade": PERFIL_LUCAS["localizacao"],
        "linkedin": PERFIL_LUCAS["linkedin"],
        "github": PERFIL_LUCAS["github"],
        "resumo_apresentacao": resumo_adaptado,
    }


# ==============================================================================
# AUTOMAÇÃO REAL NO LINKEDIN (PLAYWRIGHT)
# ==============================================================================
# (função movida para cima, com suporte a CDP)


# ==============================================================================
# FLUXO PRINCIPAL COM GATE DE APROVAÇÃO
# ==============================================================================
def carregar_ultimo_envio() -> dict:
    if ARQUIVO_ULTIMO_ENVIO.exists():
        try:
            return json.loads(ARQUIVO_ULTIMO_ENVIO.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def salvar_ultimo_envio() -> None:
    data = datetime.now().strftime("%Y-%m-%d")
    info = carregar_ultimo_envio()
    if info.get("data") != data:
        info = {"data": data, "count": 0}
    info["count"] = info.get("count", 0) + 1
    info["ultimo"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    ARQUIVO_ULTIMO_ENVIO.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


def pode_enviar_hoje() -> tuple:
    info = carregar_ultimo_envio()
    hoje = datetime.now().strftime("%Y-%m-%d")
    if info.get("data") != hoje:
        return True, LIMITE_DIARIO
    restante = LIMITE_DIARIO - info.get("count", 0)
    return restante > 0, max(restante, 0)
def buscar_recrutadores_google(empresa: str) -> list:
    try:
        import requests
        from bs4 import BeautifulSoup
        import urllib.parse
    except ImportError:
        print("⚠️ Instale requests e beautifulsoup4: pip install requests beautifulsoup4")
        return []

    query = f"recrutador {empresa} site:linkedin.com/in"
    url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"⚠️ Erro na busca: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    resultados = []
    seen = set()
    for a in soup.select("a.result__url, a.result__a"):
        href = a.get("href", "")
        if "linkedin.com/in/" in href:
            if "uddg=" in href:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                href = parsed.get("uddg", [href])[0]
            if href not in seen:
                seen.add(href)
                titulo = a.get_text(strip=True)
                resultados.append({"url": href, "titulo": titulo})
        if len(resultados) >= 8:
            break
    return resultados


def buscar_vagas_google(empresa: str) -> list:
    try:
        import requests
        from bs4 import BeautifulSoup
        import urllib.parse
    except ImportError:
        print("⚠️ Instale requests e beautifulsoup4: pip install requests beautifulsoup4")
        return []

    query = f'site:linkedin.com/jobs "{empresa}" estágio'
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num=10"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"⚠️ Erro na busca Google: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    resultados = []
    seen = set()
    for a in soup.select("a"):
        href = a.get("href", "")
        if "linkedin.com/jobs/view" in href or "linkedin.com/jobs/search" in href:
            if href.startswith("/url?q="):
                href = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("q", [href])[0]
            if href in seen:
                continue
            seen.add(href)
            titulo = a.get_text(strip=True)
            if titulo:
                resultados.append({"url": href, "titulo": titulo})
            if len(resultados) >= 8:
                break
    return resultados
    print("=" * 60)
    print("🤖 MINI-AGENTE LINKEDIN — LUCAS BARBOSA PEDRO")
    print("=" * 60)

    empresa = input("Empresa: ").strip()
    cargo = input("Cargo da vaga: ").strip()
    url = input("URL da vaga (opcional): ").strip()
    if not url:
        busca = input("🔍 Buscar vagas de {} no Google/LinkedIn? (s/N): ".format(empresa)).strip().lower()
        if busca == "s":
            print("🔎 Buscando...")
            res = buscar_vagas_google(empresa)
            if res:
                print("\nVagas encontradas:")
                for i, r in enumerate(res, 1):
                    print(f"  [{i}] {r['titulo']}")
                    print(f"      {r['url']}")
                escolha = input("Escolha o número da vaga (ou Enter para pular): ").strip()
                if escolha.isdigit() and 1 <= int(escolha) <= len(res):
                    url = res[int(escolha) - 1]["url"]
                    print(f"✅ Vaga selecionada: {url}")
            else:
                print("Nenhuma vaga encontrada.")
    recrutador = input("Nome do recrutador (opcional): ").strip()
    perfil_recrutador_url = input("URL do perfil do recrutador no LinkedIn (opcional, para envio direto): ").strip()
    if not perfil_recrutador_url:
        busca = input("🔍 Buscar recrutadores de {} no Google? (s/N): ".format(empresa)).strip().lower()
        if busca == "s":
            print("🔎 Buscando...")
            res = buscar_recrutadores_google(empresa)
            if res:
                print("\nResultados encontrados:")
                for i, r in enumerate(res, 1):
                    print(f"  [{i}] {r['titulo']}")
                    print(f"      {r['url']}")
                escolha = input("Escolha o número (ou Enter para pular): ").strip()
                if escolha.isdigit() and 1 <= int(escolha) <= len(res):
                    perfil_recrutador_url = res[int(escolha) - 1]["url"]
                    print(f"✅ Selecionado: {perfil_recrutador_url}")
            else:
                print("Nenhum resultado encontrado.")
    requisitos = input("Principais requisitos/stack da vaga: ").strip()

    if not empresa or not cargo:
        print("❌ Erro: Empresa e Cargo são obrigatórios.")
        return

    mensagem = gerar_mensagem_recrutador(recrutador, cargo, empresa, requisitos)
    dados_form = gerar_dados_formulario(cargo, empresa, requisitos)

    print("\n" + "-" * 60)
    print("📋 PREVIEW — DADOS PARA FORMULÁRIO")
    print("-" * 60)
    for k, v in dados_form.items():
        print(f"  {k}: {v}")

    print("\n" + "-" * 60)
    print("💬 PREVIEW — MENSAGEM PERSONALIZADA PARA O RECRUTADOR")
    print("-" * 60)
    print(mensagem)
    print("-" * 60)

    # Gate de aprovação explícita
    confirmacao = input("\n✅ Aprovar envio/registro? (s/N): ").strip().lower()
    if confirmacao != "s":
        print("⏸️ Operação cancelada pelo usuário (Gate de aprovação). Nada foi enviado ou salvo.")
        return

    pode, restante = pode_enviar_hoje()
    enviado_real = False
    if not pode:
        print(f"⚠️ Limite diário atingido ({LIMITE_DIARIO}/dia). Salvando para envio manual (sem enviar).")
    elif perfil_recrutador_url and perfil_recrutador_url != "-":
        enviado_real = enviar_mensagem_linkedin_playwright(perfil_recrutador_url, mensagem)
        if enviado_real:
            salvar_ultimo_envio()
    else:
        print("💾 Sem URL do recrutador — salvando mensagem para envio manual...")
        time.sleep(1)

    registro = {
        "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "empresa": empresa,
        "cargo": cargo,
        "recrutador": recrutador or "-",
        "url": url or "-",
        "perfil_recrutador_url": perfil_recrutador_url or "-",
        "mensagem_enviada": mensagem,
        "dados_formulario": dados_form,
        "status": "Enviado no LinkedIn" if enviado_real else "Pronta para envio (copiar no celular)",
    }

    registros = carregar_log()
    registros.append(registro)
    salvar_log(registros)
    registrar_no_obsidian(registro)
    salvar_mensagem_para_envio(registro)

    if enviado_real:
        print("✅ Mensagem enviada e registrada!")
    else:
        print("✅ Mensagem salva para envio manual!")

    print("🚀 Candidatura registrada com sucesso!")
    print(f"   - JSON: {LOG_JSON.name}")
    print(f"   - Obsidian: {LOG_OBSIDIAN.name}")


import argparse
import csv


def carregar_vagas_arquivo(caminho: str) -> list:
    p = Path(caminho)
    if not p.exists():
        print(f"❌ Arquivo não encontrado: {caminho}")
        return []
    if p.suffix.lower() == ".json":
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    if p.suffix.lower() == ".csv":
        with open(p, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    print("❌ Formato não suportado. Use .json ou .csv")
    return []


def executar_mini_agente_auto(caminho_vagas: str, auto_aprovar: bool = False):
    vagas = carregar_vagas_arquivo(caminho_vagas)
    if not vagas:
        return
    print(f"🤖 MODO AUTOMÁTICO — {len(vagas)} vagas carregadas de {caminho_vagas}")
    for i, v in enumerate(vagas, 1):
        pode, restante = pode_enviar_hoje()
        if not pode:
            print(f"\n⚠️ Limite diário atingido ({LIMITE_DIARIO}/dia). Parando. Restante para amanhã.")
            break
        print(f"   (Restam {restante} envios hoje)")
        empresa = v.get("empresa", "").strip()
        cargo = v.get("cargo", "").strip()
        url = v.get("url", "").strip()
        recrutador = v.get("recrutador", "").strip()
        perfil_url = v.get("perfil_recrutador_url", "").strip()
        requisitos = v.get("requisitos", "").strip()

        if not empresa or not cargo:
            print(f"[{i}] ⏭️ Pulando (sem empresa/cargo).")
            continue

        mensagem = gerar_mensagem_recrutador(recrutador, cargo, empresa, requisitos)
        dados_form = gerar_dados_formulario(cargo, empresa, requisitos)

        print("\n" + "=" * 60)
        print(f"[{i}/{len(vagas)}] {empresa} — {cargo}")
        print(mensagem)

        if not auto_aprovar:
            conf = input("✅ Aprovar esta vaga? (s/N/p=parar): ").strip().lower()
            if conf == "p":
                print("⏸️ Parando o processamento.")
                break
            if conf != "s":
                print("⏭️ Pulada.")
                continue

        enviado_real = False
        if not pode_enviar_hoje()[0]:
            print("⚠️ Limite diário atingido — salvando para envio manual.")
        elif perfil_url and perfil_url != "-":
            enviado_real = enviar_mensagem_linkedin_playwright(perfil_url, mensagem)
            if enviado_real:
                salvar_ultimo_envio()
                print(f"⏳ Aguardando {DELAY_ENTRE_ENVIOS_SEG}s (segurança)...")
                time.sleep(DELAY_ENTRE_ENVIOS_SEG)
        else:
            print("💾 Sem URL do recrutador — salvando para envio manual...")
            time.sleep(1)

        registro = {
            "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "empresa": empresa,
            "cargo": cargo,
            "recrutador": recrutador or "-",
            "url": url or "-",
            "perfil_recrutador_url": perfil_url or "-",
            "mensagem_enviada": mensagem,
            "dados_formulario": dados_form,
            "status": "Enviado no LinkedIn" if enviado_real else "Pronta para envio (copiar no celular)",
        }
        registros = carregar_log()
        registros.append(registro)
        salvar_log(registros)
        registrar_no_obsidian(registro)
        salvar_mensagem_para_envio(registro)
        if enviado_real:
            print("✅ Enviada e registrada.")
        else:
            print("✅ Salva para envio manual.")

        time.sleep(3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mini-Agente LinkedIn — Lucas Barbosa Pedro")
    parser.add_argument("--auto", metavar="ARQUIVO", help="Processa vagas de um .json/.csv em lote")
    parser.add_argument("--yes", action="store_true", help="Aprova automaticamente todas (sem gate por vaga)")
    args = parser.parse_args()

    if args.auto:
        executar_mini_agente_auto(args.auto, auto_aprovar=args.yes)
    else:
        executar_mini_agente()

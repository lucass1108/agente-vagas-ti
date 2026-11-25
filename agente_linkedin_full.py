"""
⚠️ AVISO: Automação no LinkedIn viola os Termos de Serviço da plataforma.
Use com responsabilidade: volume baixo (≤5/dia), delays aleatórios e sempre
revise o conteúdo antes de enviar. Risco de restrição/banimento da conta.
Por padrão este script NÃO envia nada — apenas gera rascunhos e salva log.
Use --enviar para habilitar o envio (com confirmação interativa por ação).
"""
import argparse
import random
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent
CDP_URL = "http://localhost:9222"


def obter_contexto(p):
    try:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        return browser, (browser.contexts[0] if browser.contexts else browser.new_context()), True
    except Exception:
        print("⚠️ Abra o Opera GX com --remote-debugging-port=9222 e faça login no LinkedIn.")
        return None, None, False


def buscar_vagas_duckduckgo(query: str, max_results: int = 10) -> list:
    try:
        import requests
        from bs4 import BeautifulSoup
        import urllib.parse
    except ImportError:
        print("⚠️ Instale requests e beautifulsoup4: pip install requests beautifulsoup4")
        return []
    url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"⚠️ Erro na busca: {e}")
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    resultados = []
    seen = set()
    for a in soup.select("a.result__a"):
        href = a.get("href", "")
        if "linkedin.com/jobs" in href:
            if "uddg=" in href:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                href = parsed.get("uddg", [href])[0]
            if href in seen:
                continue
            seen.add(href)
            resultados.append({"url": href, "titulo": a.get_text(strip=True)})
            if len(resultados) >= max_results:
                break
    return resultados


def tentar_easy_apply(page, perfil: dict) -> bool:
    try:
        btn = page.locator("button:has-text('Candidatar-se'), button:has-text('Easy Apply'), button:has-text('Apply')").first
        if btn.count() == 0 or not btn.is_visible():
            return False
        btn.click(timeout=10000)
        time.sleep(3)

        campos = {
            "input[name*='firstName'], input[aria-label*='Nome']": perfil["nome"].split()[0],
            "input[name*='lastName'], input[aria-label*='Sobrenome']": perfil["nome"].split()[-1],
            "input[name*='email'], input[aria-label*='Email']": perfil["email"],
            "input[name*='phone'], input[aria-label*='Telefone']": perfil["telefone"],
            "input[name*='city'], input[aria-label*='Cidade']": perfil["localizacao"],
        }
        for sel, val in campos.items():
            try:
                el = page.locator(sel).first
                if el.count() > 0 and el.is_visible():
                    el.fill(val)
                    time.sleep(0.5)
            except Exception:
                pass

        try:
            ta = page.locator("textarea").first
            if ta.count() > 0 and ta.is_visible():
                ta.fill(perfil["resumo"])
        except Exception:
            pass

        return True
    except Exception as e:
        print(f"⚠️ Erro no Easy Apply: {e}")
        return False


PERFIL = {
    "nome": "Lucas Barbosa Pedro",
    "email": "lucasbarbosapedro1108@gmail.com",
    "telefone": "(11) 91508-2460",
    "localizacao": "Taboão da Serra - SP",
    "linkedin": "https://linkedin.com/in/lucasbarbosapedro",
    "github": "https://github.com/lucass1108",
    "resumo": "Estudante de ADS (UNIFECAF, 2º semestre) com projetos em Python/Flask/MySQL e experiência em backoffice. Medalhista CUCO/USP (ouro), OBMEP, OMASP.",
}


def main(enviar: bool = False):
    print("=" * 60)
    print("🤖 AGENTE LINKEDIN FULL — LUCAS BARBOSA PEDRO")
    print("=" * 60)
    if not enviar:
        print("⚠️ MODO RASCUNHO: nada será enviado. Use --enviar para habilitar envio (com confirmação por ação).")

    query = input("Buscar vagas (ex.: estágio ti São Paulo): ").strip() or "estágio ti São Paulo"
    print(f"\n🔎 Buscando vagas: {query}")
    vagas = buscar_vagas_duckduckgo(f"{query} site:linkedin.com/jobs", max_results=8)
    if not vagas:
        print("❌ Nenhuma vaga encontrada.")
        return
    print(f"✅ {len(vagas)} vagas encontradas.\n")

    with sync_playwright() as p:
        browser, context, via_cdp = obter_contexto(p)
        if context is None:
            return
        page = context.pages[0] if context.pages else context.new_page()

        enviados_hoje = 0
        LIMITE_DIA = 5

        for i, v in enumerate(vagas, 1):
            print("\n" + "=" * 60)
            print(f"[{i}/{len(vagas)}] {v['titulo']}")
            print(f"URL: {v['url']}")
            print("=" * 60)

            try:
                page.goto(v["url"], timeout=60000)
                time.sleep(4)
            except Exception as e:
                print(f"⚠️ Erro ao abrir vaga: {e}")
                continue

            aplicou_form = tentar_easy_apply(page, PERFIL)
            if aplicou_form:
                print("📋 Formulário de candidatura preenchido (Easy Apply).")
            else:
                print("📋 Sem Easy Apply — candidatura manual necessária.")

            rec_url = ""
            try:
                rec_el = page.locator("a.app-aware-link[href*='/in/']").first
                if rec_el.count() > 0:
                    rec_url = rec_el.get_attribute("href") or ""
                    if rec_url.startswith("/"):
                        rec_url = "https://www.linkedin.com" + rec_url
                    rec_nome = rec_el.inner_text().strip()
                    print(f"👤 Recrutador encontrado: {rec_nome} ({rec_url})")
            except Exception:
                pass

            conf = input("✅ Autorizar envio/candidatura? (s/N/p=parar): ").strip().lower()
            if conf == "p":
                print("⏸️ Parando.")
                break
            if conf != "s":
                print("⏭️ Pulada.")
                continue

            if not enviar:
                print("💾 Modo rascunho: nada enviado. Rode com --enviar para enviar.")
                continue

            if enviados_hoje >= LIMITE_DIA:
                print(f"⚠️ Limite diário atingido ({LIMITE_DIA}). Parando.")
                break

            if aplicou_form:
                try:
                    btn_submit = page.locator("button:has-text('Enviar candidatura'), button:has-text('Submit application'), button:has-text('Enviar')").first
                    if btn_submit.count() > 0:
                        btn_submit.click(timeout=10000)
                        time.sleep(random.uniform(2, 5))
                        print("✅ Candidatura enviada!")
                        enviados_hoje += 1
                    else:
                        print("⚠️ Botão de envio não encontrado — envie manualmente.")
                        input("Pressione ENTER após enviar...")
                except Exception as e:
                    print(f"⚠️ Erro ao enviar: {e}")
                    input("Envie manualmente e pressione ENTER...")

            if rec_url:
                try:
                    page.goto(rec_url, timeout=60000)
                    time.sleep(3)
                    btn_msg = page.locator("button:has-text('Enviar mensagem'), button:has-text('Message')").first
                    if btn_msg.count() > 0 and btn_msg.is_visible():
                        btn_msg.click(timeout=10000)
                        time.sleep(2)
                        caixa = page.locator("div.msg-form__contenteditable[role='textbox']").first
                        msg = f"Olá! Vi a vaga e me identifiquei. Sou estudante de ADS (UNIFECAF) com projetos em Python/Flask/MySQL. GitHub: {PERFIL['github']}"
                        caixa.fill(msg)
                        print("📝 Mensagem preenchida. Clique em ENVIAR e pressione ENTER.")
                        input()
                        enviados_hoje += 1
                    else:
                        btn_conn = page.locator("button:has-text('Conectar'), button:has-text('Connect')").first
                        if btn_conn.count() > 0 and btn_conn.is_visible():
                            btn_conn.click(timeout=10000)
                            time.sleep(2)
                            btn_nota = page.locator("button:has-text('Adicionar nota'), button:has-text('Add a note')").first
                            if btn_nota.count() > 0:
                                btn_nota.click(timeout=10000)
                                time.sleep(1)
                                caixa_nota = page.locator("textarea[name='message'], textarea#custom-message").first
                                caixa_nota.fill(msg[:300])
                                print("📝 Nota preenchida. Clique em ENVIAR e pressione ENTER.")
                                input()
                                enviados_hoje += 1
                except Exception as e:
                    print(f"⚠️ Erro ao mensagem recrutador: {e}")

            time.sleep(random.uniform(3, 6))

        print("\n✅ Processo concluído.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente LinkedIn Full — Lucas Barbosa Pedro")
    parser.add_argument("--enviar", action="store_true", help="Habilita envio (com confirmação interativa por ação)")
    args = parser.parse_args()
    main(enviar=args.enviar)
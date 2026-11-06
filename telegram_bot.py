#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Telegram — Agente Vagas TI
==============================
Permite se comunicar com o agente de vagas pelo Telegram no celular.

Comandos:
  /start       - Inicia o bot
  /buscar      - Busca vagas agora
  /novas       - Mostra vagas novas
  /candidaturas - Lista candidaturas
  /stats       - Estatísticas
  /entrevista <vaga> - Prep de entrevista
  /curriculo <vaga>  - Currículo personalizado
  /status <vaga> <status> - Atualizar status
  /ajuda       - Lista de comandos

Configuração:
  1. Crie um bot no @BotFather (Telegram)
  2. Obtenha o token
  3. Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env ou variáveis de ambiente
  4. Rode: python telegram_bot.py
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime

# Adiciona o diretório do agente ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vagas_agent import (
    CONFIG, run_agent, list_applications, get_application_stats,
    generate_interview_prep, generate_tailored_resume, track_application,
    load_applications, APPLICATION_STATUSES, get_followup_reminders,
)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", CONFIG.get("telegram_bot_token", ""))
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", CONFIG.get("telegram_chat_id", ""))

if not BOT_TOKEN:
    print("ERRO: Configure TELEGRAM_BOT_TOKEN (via @BotFather no Telegram)")
    sys.exit(1)

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ============================================================
# FUNÇÕES DO BOT
# ============================================================
def send_message(chat_id, text, parse_mode="Markdown"):
    """Envia mensagem via Telegram."""
    try:
        url = f"{API_URL}/sendMessage"
        data = json.dumps({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[ERRO] Telegram: {e}")

def get_updates(offset=0):
    """Busca novas mensagens do Telegram."""
    try:
        url = f"{API_URL}/getUpdates?offset={offset}&timeout=30"
        resp = urllib.request.urlopen(url, timeout=35)
        return json.loads(resp.read())
    except Exception as e:
        print(f"[ERRO] getUpdates: {e}")
        return {"result": []}

def handle_command(chat_id, text):
    """Processa comandos do usuário."""
    parts = text.strip().split()
    cmd = parts[0].lower() if parts else ""
    args = " ".join(parts[1:]) if len(parts) > 1 else ""

    if cmd == "/start":
        send_message(chat_id, (
            "🤖 *Agente Vagas TI — Lucas*\n\n"
            "Olá! Sou seu agente de vagas. Use /ajuda para ver os comandos.\n\n"
            "Comandos rápidos:\n"
            "• /buscar — Busca vagas agora\n"
            "• /novas — Vagas novas\n"
            "• /candidaturas — Suas candidaturas\n"
            "• /stats — Estatísticas\n"
            "• /ajuda — Lista completa"
        ))

    elif cmd == "/ajuda":
        send_message(chat_id, (
            "📋 *Comandos disponíveis:*\n\n"
            "🔍 *Busca:*\n"
            "  /buscar — Busca vagas agora\n"
            "  /novas — Vagas novas desde última busca\n\n"
            "📋 *Candidaturas:*\n"
            "  /candidaturas — Lista todas\n"
            "  /stats — Estatísticas\n"
            "  /status <vaga> <status> — Atualizar status\n"
            "    Status: candidatado, em_analise, entrevista, rejeitado, aprovado\n\n"
            "🎯 *Preparação:*\n"
            "  /entrevista <vaga> — Prep de entrevista\n"
            "  /curriculo <vaga> — Currículo personalizado\n\n"
            "⏰ *Outros:*\n"
            "  /followup — Lembretes de follow-up\n"
            "  /salario <vaga>:<valor> — Registrar salário\n"
        ))

    elif cmd == "/buscar":
        send_message(chat_id, "🔍 Buscando vagas... Aguarde.")
        # Roda o agente (captura output)
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_agent(send_email_flag=False, send_telegram_flag=False)
        output = buf.getvalue()
        # Envia resumo
        top_lines = [l for l in output.split("\n") if l.strip().startswith("[")]
        summary = "✅ Busca concluída!\n\n" + "\n".join(top_lines[:10])
        send_message(chat_id, summary)

    elif cmd == "/novas":
        apps = load_applications()
        send_message(chat_id, f"📋 *Candidaturas:* {len(apps)}\nUse /candidaturas para detalhes.")

    elif cmd == "/candidaturas":
        apps = load_applications()
        if not apps:
            send_message(chat_id, "Nenhuma candidatura registrada.\nUse: /status <vaga> candidatado")
            return
        msg = "📋 *Candidaturas:*\n\n"
        for i, app in enumerate(apps, 1):
            st = APPLICATION_STATUSES.get(app["status"], APPLICATION_STATUSES["nao_candidatado"])
            msg += f"{i}. {st['icon']} *{app['vaga'][:40]}*\n"
            msg += f"   {app.get('empresa', 'N/A')} | {st['label']} | {app.get('data_candidatura', 'N/A')}\n\n"
        send_message(chat_id, msg)

    elif cmd == "/stats":
        stats = get_application_stats()
        msg = (
            f"📊 *Estatísticas:*\n\n"
            f"Total: {stats['total']}\n"
            f"Taxa de resposta: {stats['taxa_resposta']}%\n"
            f"Taxa de entrevista: {stats['taxa_entrevista']}%\n\n"
        )
        for st_key, st_info in APPLICATION_STATUSES.items():
            if stats[st_key] > 0:
                msg += f"{st_info['icon']} {st_info['label']}: {stats[st_key]}\n"
        send_message(chat_id, msg)

    elif cmd == "/status":
        if len(parts) < 3:
            send_message(chat_id, "Uso: /status <vaga> <status>\nStatus: candidatado, em_analise, entrevista, rejeitado, aprovado")
            return
        vaga = parts[1]
        status = parts[2]
        if status not in APPLICATION_STATUSES:
            send_message(chat_id, f"Status inválido. Use: {', '.join(APPLICATION_STATUSES.keys())}")
            return
        track_application(title=vaga, status=status)
        st = APPLICATION_STATUSES[status]
        send_message(chat_id, f"✅ Atualizado: {vaga} → {st['icon']} {st['label']}")

    elif cmd == "/entrevista":
        if not args:
            send_message(chat_id, "Uso: /entrevista <nome da vaga>")
            return
        vaga = args
        # Encontra a vaga
        app = None
        for a in load_applications():
            if vaga.lower() in a["vaga"].lower():
                app = a
                break
        if not app:
            send_message(chat_id, f"Vaga '{vaga}' não encontrada nas candidaturas.")
            return
        send_message(chat_id, f"🎯 Gerando prep de entrevista para {app['vaga']}...")
        content = generate_interview_prep(app["vaga"])
        # Envia resumo (limitado a 4096 chars do Telegram)
        if len(content) > 4000:
            content = content[:4000] + "\n\n... (truncado)"
        send_message(chat_id, content)

    elif cmd == "/curriculo":
        if not args:
            send_message(chat_id, "Uso: /curriculo <nome da vaga>")
            return
        vaga = args
        app = None
        for a in load_applications():
            if vaga.lower() in a["vaga"].lower():
                app = a
                break
        if not app:
            send_message(chat_id, f"Vaga '{vaga}' não encontrada nas candidaturas.")
            return
        send_message(chat_id, f"📄 Gerando currículo para {app['vaga']}...")
        content = generate_tailored_resume(app["vaga"])
        if len(content) > 4000:
            content = content[:4000] + "\n\n... (truncado)"
        send_message(chat_id, content)

    elif cmd == "/followup":
        reminders = get_followup_reminders()
        if not reminders:
            send_message(chat_id, "✅ Nenhum follow-up pendente!")
            return
        msg = "⏰ *Follow-ups pendentes:*\n\n"
        for app, days in reminders:
            msg += f"- {app['vaga']} ({days} dias sem resposta)\n"
        send_message(chat_id, msg)

    elif cmd == "/salario":
        if not args or ":" not in args:
            send_message(chat_id, "Uso: /salario <vaga>:<valor>\nEx: /salario Cogna:R$1500-R$2000")
            return
        parts = args.split(":")
        vaga = parts[0].strip()
        sal_range = parts[1].strip()
        import re
        m = re.search(r'R?\$?\s*([\d.,]+)\s*[-–aà]+\s*R?\$?\s*([\d.,]+)', sal_range)
        if m:
            sals = []
            sal_path = os.path.join(CONFIG["vault_path"], "salarios.json")
            if os.path.exists(sal_path):
                with open(sal_path) as f:
                    sals = json.load(f).get("salarios", [])
            sals.append({"vaga": vaga, "min": m.group(1), "max": m.group(2), "data": datetime.now().strftime("%Y-%m-%d")})
            with open(sal_path, "w") as f:
                json.dump({"salarios": sals}, f, indent=2)
            send_message(chat_id, f"✅ Salário registrado: {vaga} → R$ {m.group(1)} a R$ {m.group(2)}")
        else:
            send_message(chat_id, "Formato inválido. Use: /salario Vaga:R$1000-R$2000")

    else:
        send_message(chat_id, f"Comando '{cmd}' não reconhecido. Use /ajuda para ver os comandos.")

def main():
    print("🤖 Bot Telegram iniciado!")
    print(f"Token: {BOT_TOKEN[:10]}...")
    if CHAT_ID:
        print(f"Chat ID: {CHAT_ID}")
        send_message(CHAT_ID, "🤖 Bot Agente Vagas TI iniciado! Use /ajuda para ver os comandos.")
    else:
        print("AVISO: CHAT_ID não configurado. O bot responderá a qualquer mensagem.")

    offset = 0
    while True:
        try:
            updates = get_updates(offset)
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")
                if chat_id and text:
                    # Se CHAT_ID configurado, só responde a esse chat
                    if CHAT_ID and str(chat_id) != str(CHAT_ID):
                        continue
                    handle_command(chat_id, text)
        except KeyboardInterrupt:
            print("\nBot encerrado.")
            break
        except Exception as e:
            print(f"[ERRO] Loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()

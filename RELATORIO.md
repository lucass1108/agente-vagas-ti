# Relatório do Projeto — Agente de Vagas TI

## 📋 Visão Geral

O projeto "agente-vagas-ti" é um sistema automatizado de busca de vagas de Jovem Aprendiz e Estágio em TI, que busca vagas em múltiplas fontes, ranqueia por compatibilidade com o currículo, gera relatórios e envia notificações.

---

## 🏗️ Arquitetura — Mini-Agentes Independentes

O projeto foi refatorado em **mini-agentes independentes**, cada um com uma responsabilidade específica. Todos compartilham dados via arquivos JSON.

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ agente_busca.py │────▶│ ultimas_vagas.json│────▶│ agente_email.py     │
│ (busca vagas)   │     │ (dados compart.) │     │ (envia email)       │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
        │                        │
        │                        ├──▶ agente_candidaturas.py
        │                        ├──▶ agente_entrevista.py
        │                        ├──▶ agente_curriculo.py
        │                        └──▶ agente_dashboard.py
        │
        └── vagas_agent.py (orquestrador principal)
```

---

## 📁 Arquivos do Projeto

### Mini-Agentes (novos)
| Arquivo | Função | Comando |
|---|---|---|
| `agente_busca.py` | Busca vagas e salva em `ultimas_vagas.json` | `python agente_busca.py` |
| `agente_email.py` | Lê `ultimas_vagas.json` e envia email HTML | `python agente_email.py` |
| `agente_candidaturas.py` | Gerencia candidaturas (registrar, listar, stats) | `python agente_candidaturas.py --listar` |
| `agente_entrevista.py` | Gera prep de entrevista | `python agente_entrevista.py "Vaga X"` |
| `agente_curriculo.py` | Gera currículo personalizado | `python agente_curriculo.py "Vaga X"` |
| `agente_dashboard.py` | Gera dashboard Obsidian Base | `python agente_dashboard.py` |

### Arquivos principais
| Arquivo | Descrição |
|---|---|
| `vagas_agent.py` | Orquestrador principal (v6.2) — contém toda a lógica |
| `streamlit_app.py` | App web (Streamlit Cloud) |
| `telegram_bot.py` | Bot Telegram |
| `requirements.txt` | Dependências |
| `README.md` | Documentação |
| `.github/workflows/vagas.yml` | GitHub Actions (seg-sex 8h BRT) |
| `.gitignore` | Proteção de arquivos |

### Arquivos de dados (gerados automaticamente)
| Arquivo | Descrição |
|---|---|
| `ultimas_vagas.json` | Últimas vagas encontradas (com score, motivos, etc.) |
| `historico_vagas.json` | Histórico de URLs vistas (deduplicação) |
| `candidaturas.json` | Candidaturas registradas (status, notas, etc.) |
| `preview.html` | Preview do email (gerado pelo --dry-run) |

---

## 🔧 Funcionalidades

### Busca de vagas
- **Fontes:** Gupy API, Adzuna API, Bing (scraping)
- **Filtros:** Apenas TI, apenas São Paulo/remoto, score ≥ 30
- **Deduplicação:** Por URL e por (título, empresa)
- **Validação:** Título >5 chars, URL começa com http
- **Prazo:** Descarta vagas com prazo de inscrição encerrado

### Scoring (0-100)
| Critério | Pontos | Descrição |
|---|---|---|
| Nível compatível | +25 | Estágio, aprendiz, trainee, júnior |
| Área TI | +20 | TI, tecnologia, software, sistemas, dados, etc. |
| Stack | +até 30 | Python(8), SQL(6), Flask(4), MySQL(4), etc. |
| Localização | +15 | SP ou remoto |
| Recente | +10 | Publicada há ≤7 dias |
| Penalidade (nível acima) | -50 | Sênior, pleno, especialista, etc. |
| Penalidade (fora da região) | -20 | Cidade não é SP |

### Email
- Formato HTML organizado (mobile-friendly)
- Top 10 vagas com score colorido
- Links diretos para cada vaga
- Estatísticas (total, top, médias, novas)
- Fontes consultadas

### Candidaturas
- 6 status: Não candidatado, Candidatado, Em análise, Entrevista, Não selecionado, Aprovado
- Lembretes de follow-up (7+ dias sem resposta)
- Estatísticas: total, taxa de resposta, taxa de entrevista

### Prep de Entrevista
- Perguntas gerais, técnicas, comportamentais
- Perguntas sobre projetos
- Dicas e perguntas para o entrevistador

### Currículo Personalizado
- Skills destacadas por vaga
- Sugestões de adaptação
- Prompt para IA (ChatGPT/Claude)

---

## 📊 Dados do Perfil (embutido no código)

```python
PERFIL = {
    "cidades": ["são paulo", "sao paulo", "taboão da serra", ...],
    "stack": {"python": 8, "sql": 6, "flask": 4, "mysql": 4, "git": 3, ...},
    "nivel": ["estágio", "estagio", "jovem aprendiz", "aprendiz", "trainee", "júnior", "junior"],
    "ti": ["ti", "tecnologia", "software", "desenvolv", "sistemas", "dados", ...],
    "evitar": ["sênior", "senior", "pleno", "especialista", ...],
}
```

---

## 🔧 Configuração

### Variáveis de ambiente:
| Variável | Descrição | Obrigatório? |
|---|---|---|
| `EMAIL_PASSWORD` | Senha de app do Gmail | ✅ (para email) |
| `ADZUNA_APP_ID` | ID do Adzuna | ❌ (opcional) |
| `ADZUNA_APP_KEY` | Key do Adzuna | ❌ (opcional) |
| `TELEGRAM_BOT_TOKEN` | Token do bot Telegram | ❌ (opcional) |
| `TELEGRAM_CHAT_ID` | ID do chat Telegram | ❌ (opcional) |
| `VAULT_PATH` | Caminho do vault Obsidian | ❌ (auto-detectado) |

### GitHub Secrets:
- `EMAIL_PASSWORD` = senha de app do Gmail
- `ADZUNA_APP_ID` = ID do Adzuna
- `ADZUNA_APP_KEY` = Key do Adzuna
- `TELEGRAM_BOT_TOKEN` = token do bot
- `TELEGRAM_CHAT_ID` = ID do chat

### Streamlit Cloud Secrets:
- `ADMIN_KEY` = chave de acesso admin
- `GEMINI_API_KEY` = chave do Gemini (gratuita)

---

## 📱 Como usar

### Busca de vagas:
```bash
python agente_busca.py
# ou
python vagas_agent.py --dry-run
```

### Envio de email:
```bash
python agente_email.py
# ou
python vagas_agent.py --email
```

### Candidaturas:
```bash
python agente_candidaturas.py --listar
python agente_candidaturas.py --stats
python agente_candidaturas.py --followup
python agente_candidaturas.py --registrar "Vaga X" --status candidatado --nota "Enviei CV"
```

### Prep de entrevista:
```bash
python agente_entrevista.py "Nome da vaga"
```

### Currículo personalizado:
```bash
python agente_curriculo.py "Nome da vaga"
```

### Dashboard:
```bash
python agente_dashboard.py
```

---

## 📊 Métricas da última execução:
- **52 vagas** encontradas (Gupy + Adzuna + Bing)
- **21 vagas** com score ≥ 60 (Top)
- **9 vagas** com score 40-59 (Médias)
- **9 vagas novas** desde a última execução
- **1 candidatura** registrada (Cogna - Estagiário Suporte TI)
- **1 follow-up** pendente

---

## 🔗 Links
- **GitHub:** https://github.com/lucass1108/agente-vagas-ti
- **Streamlit:** https://agente-vagas-ti-cylvmizosdkjxcsp8pskwh.streamlit.app
- **Email:** lucasbarbosapedro1108@gmail.com

---

## 📝 Notas
- O agente roda automaticamente seg-sex às 8h BRT via GitHub Actions
- O email é enviado com as vagas encontradas
- O histórico é salvo para detectar vagas novas
- O perfil é embutido no código (não depende de caminho local)
- Todos os segredos são via variáveis de ambiente (nunca no código)
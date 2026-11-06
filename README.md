# 🤖 Agente de Vagas TI — Lucas Barbosa Pedro

> Agente automatizado que busca vagas de **Jovem Aprendiz** e **Estágio** em TI compatíveis com o currículo de Lucas, ranqueia por compatibilidade e gera relatório no Obsidian + email.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

## 📋 Sobre

Este projeto é um **agente de IA** que automatiza a busca de vagas de emprego em TI. Ele:

- 🔍 Busca vagas em múltiplas fontes (Bing, Indeed, Vagas.com, Gupy, CIEE, NUBE)
- 📊 Ranqueia cada vaga de 0-100 com base na compatibilidade com o perfil do candidato
- 🆕 Detecta vagas novas desde a última execução
- 📝 Gera relatório em Markdown (Obsidian) com frontmatter YAML
- 📧 Envia relatório por email (opcional)
- 🔔 Envia notificação toast no Windows (opcional)
- ⏰ Pode rodar agendado (diariamente)

### Perfil do candidato

| Campo | Detalhe |
|---|---|
| Nome | Lucas Barbosa Pedro |
| Localização | Taboão da Serra - SP |
| Formação | ADS — UNIFECAF (2º semestre) |
| Skills | Python, SQL, Flask, MySQL, Git, HTML/CSS, Windows, Redes |
| Experiência | Backoffice/Atendimento (Sercom/Claro) |
| Diferenciais | Medalhista CUCO/USP (ouro), OBMEP, OMASP |

## 🚀 Como usar

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar

Edite a seção `CONFIG` no arquivo `vagas_agent.py`:

```python
CONFIG = {
    "vault_path": "caminho/do/seu/vault",
    "email_enabled": True,           # ativar email
    "email_from": "seu@gmail.com",
    "email_password": "senha_de_app",  # senha de app do Gmail
    "email_to": "destino@gmail.com",
    "toast_enabled": True,
}
```

### 3. Rodar

```bash
# Busca e gera nota
python vagas_agent.py

# Busca + email
python vagas_agent.py --email

# Modo agendado (diário)
python vagas_agent.py --schedule
```

## 📁 Estrutura do projeto

```
agente-vagas-ti/
├── vagas_agent.py          # Script principal
├── requirements.txt        # Dependências
├── .gitignore              # Arquivos ignorados
├── LICENSE                 # Licença MIT
├── README.md               # Este arquivo
├── Vagas TI - Agente Lucas.md  # Especificação do agente
└── .github/
    └── workflows/
        └── vagas.yml       # GitHub Actions (automação)
```

## ⚙️ Automação (GitHub Actions)

O projeto inclui um workflow que roda automaticamente de segunda a sexta às 8h (BRT):

```yaml
# .github/workflows/vagas.yml
name: Agente Vagas TI
on:
  schedule:
    - cron: '0 11 * * 1-5'
  workflow_dispatch:
jobs:
  buscar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python vagas_agent.py --email
```

## 📱 Uso no iPhone

- **GitHub App**: visualize os resultados pelo app do GitHub no iPhone
- **Email**: receba o relatório por email (configurável)
- **GitHub Actions**: roda na nuvem, não precisa do PC ligado

## 🛠️ Tecnologias

- **Python 3.10+**
- **requests** — requisições HTTP
- **BeautifulSoup4** — parsing HTML
- **schedule** — agendamento
- **smtplib** — envio de email

## 📊 Sistema de Pontuação

Cada vaga recebe uma pontuação de 0-100:

| Critério | Peso | Descrição |
|---|---|---|
| Área | 30 | Suporte, dados, dev, infra |
| Skills | 25 | Python, SQL, Flask, MySQL, Git... |
| Nível | 20 | JA, estágio, trainee |
| Localização | 15 | Taboão, SP capital, remoto |
| Carga horária | 10 | 6h/dia, 30h/sem |

Bônus e penalidades aplicados conforme compatibilidade.

## 📄 Licença

MIT License — veja [LICENSE](LICENSE) para detalhes.

## 👤 Autor

**Lucas Barbosa Pedro**
- GitHub: [@lucass1108](https://github.com/lucass1108)
- LinkedIn: [lucasbarbosapedro](https://linkedin.com/in/lucasbarbosapedro)
- Email: lucasbarbosapedro1108@gmail.com

---

> Projeto desenvolvido como parte dos estudos em Análise e Desenvolvimento de Sistemas (ADS) — UNIFECAF.

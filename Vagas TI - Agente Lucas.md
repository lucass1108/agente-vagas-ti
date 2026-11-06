# Agente de Vagas — Lucas Barbosa Pedro

> Agente que busca vagas de **Jovem Aprendiz** e **Estágio** em TI compatíveis com o currículo de Lucas, e entrega um relatório ranqueado no Obsidian.

## 🎯 Perfil-alvo (extraído do currículo)

- **Nome:** Lucas Barbosa Pedro
- **Localização base:** Taboão da Serra - SP (aceita São Paulo capital e remoto/híbrido)
- **Objetivo:** Jovem Aprendiz / Estágio em TI — suporte, dados ou desenvolvimento
- **Formação:** ADS (UNIFECAF) — 2º semestre (2026)
- **Experiência:** Backoffice/atendimento (Sercom/Claro) — jan/2026 → atual
- **Stack:** Python, SQL, HTML/CSS, Flask, MySQL, Git/GitHub, Windows, Office/Excel, redes básicas, Linux
- **Diferenciais:** medalhista CUCO/USP (ouro), OBMEP, OMASP; inglês intermediário

## 🔎 Fontes de busca

| Fonte | URL base | Observação |
|---|---|---|
| LinkedIn | linkedin.com/jobs | Filtro por "Jovem Aprendiz" + "Estágio" |
| Vagas.com | vagas.com.br | Busca por palavra-chave |
| Gupy | portal.gupy.io | Muitas empresas grandes |
| InfoJobs | infojobs.com.br | Vagas de estágio/JA |
| Indeed | br.indeed.com | Agregador |
| Catho | catho.com.br | Estágio/JA |
| CIEE | ciee.org.br | Portal de estágio/JA |
| NUBE | nube.com.br | Estágio/JA |
| C9 (99jobs) | 99jobs.com | Tech |

## 🔑 Palavras-chave de busca

**Primárias (alta prioridade):**
- "jovem aprendiz ti"
- "jovem aprendiz suporte"
- "estágio ti"
- "estágio suporte técnico"
- "estágio desenvolvimento"
- "estágio dados"
- "estágio programação python"
- "estágio back-end"
- "estágio help desk"
- "estágio analista de sistemas"

**Secundárias (média prioridade):**
- "estágio analista de dados"
- "estágio business intelligence"
- "estágio desenvolvedor web"
- "estágio infraestrutura"
- "estágio redes"
- "trainee ti"

**Filtros de localização:**
- Taboão da Serra
- São Paulo (capital)
- Remoto / Híbrido
- Grande São Paulo (Osasco, Embu, Cotia, Itapecerica, etc.)

## 📊 Critérios de pontuação (ranking)

Cada vaga recebe pontuação de 0 a 100:

| Critério | Peso | Descrição |
|---|---|---|
| Compatibilidade de área | 30 | Suporte/dados/dev = alto; outros TI = médio |
| Match de habilidades | 25 | Python, SQL, Flask, MySQL, Git, redes, Windows... |
| Nível (JA/estágio) | 20 | Jovem Aprendiz ou estágio = alto |
| Localização | 15 | Taboão/SP capital/remoto = alto |
| Carga horária compatível | 10 | Permite conciliar com faculdade (manhã/noite) |

**Bônus:**
- +5 se a empresa é tech ou tem programa estruturado de estágio
- +5 se menciona "primeira experiência" / "sem experiência"
- +3 se oferece capacitação/cursos

**Penalidades:**
- -20 se exige experiência prévia em TI
- -15 se exige inglês avançado (ele é intermediário)
- -10 se for presencial muito longe (>1h30 de Taboão)

## 📋 Formato de saída (nota no Obsidian)

Arquivo: `Vagas TI - Lucas.md` (atualizado a cada execução)

```markdown
---
tags: [vagas, ti, estagio, jovem-aprendiz]
updated: YYYY-MM-DD
---

# Vagas TI compatíveis — Lucas

## 🟢 Top Matches (score ≥ 70)
| # | Vaga | Empresa | Local | Tipo | Score | Link |
|---|---|---|---|---|---|---|
| 1 | ... | ... | ... | ... | 85 | [ver](url) |

### Detalhes
#### 1. Nome da vaga — Empresa
- **Local:** ...
- **Tipo:** Estágio / JA
- **Requisitos:** ...
- **Por que match:** ...
- **Link:** ...

## 🟡 Matches médios (score 40-69)
...

## 🔴 Baixa compatibilidade (score < 40)
...
```

## ⚙️ Fluxo de execução do agente

1. **Coleta:** buscar em todas as fontes com as palavras-chave primárias + secundárias
2. **Deduplicação:** remover vagas repetidas (mesmo título + empresa)
3. **Filtragem:** descartar vagas que exigem experiência prévia em TI ou inglês avançado
4. **Pontuação:** aplicar critérios de ranking
5. **Ordenação:** do maior score para o menor
6. **Geração:** criar/atualizar a nota `Vagas TI - Lucas.md` no vault
7. **Notificação:** (opcional) alertar o usuário das top 5 novas vagas

## 📅 Frequência sugerida

- **Diária:** segunda a sexta, 8h da manhã
- **Ou sob demanda:** quando o usuário pedir

## 🚀 Como implementar (próximos passos)

1. [ ] Criar a nota `Vagas TI - Lucas.md` no vault com o template acima
2. [ ] Configurar busca nas fontes (web search / scraping)
3. [ ] Implementar o scoring e deduplicação
4. [ ] Agendar execução (cron/task scheduler) ou rodar manualmente
5. [ ] Testar com uma rodada piloto e ajustar critérios

## 💡 Dicas extras

- **LinkedIn:** ativar alertas de vaga com as palavras-chave
- **Gupy:** criar conta e salvar buscas
- **CIEE/NUBE:** cadastro gratuito e envio de currículo
- **Networking:** participar de grupos de TI no Telegram/WhatsApp de SP
- **Projetos GitHub:** manter o FinanceTracker atualizado — é um grande diferencial pra estágio dev

---

## 🤖 System Prompt do Agente (Melhoria 10)

```
Você é um agente de busca de vagas de emprego especializado em
Jovem Aprendiz e Estágio na área de TI.

Perfil do candidato:
- Nome: Lucas Barbosa Pedro
- Localização: Taboão da Serra - SP
- Formação: ADS (2º semestre) - UNIFECAF
- Habilidades: Python, SQL, Flask, MySQL, Git, HTML/CSS, Windows, Redes, Linux
- Experiência: Backoffice/atendimento (Sercom/Claro) desde jan/2026
- Diferenciais: medalhista CUCO/USP (ouro), OBMEP, OMASP; inglês intermediário

Regras:
1. Busque apenas vagas de Jovem Aprendiz ou Estágio em TI
2. Priorize vagas em Taboão da Serra, São Paulo capital e remoto
3. Descarte vagas que exigem experiência prévia em TI
4. Pontue cada vaga de 0-100 com base na compatibilidade
5. Gere um relatório ranqueado no Obsidian
6. Destaque vagas novas desde a última execução
7. Inclua links diretos de candidatura quando possível
```

## 📋 Prompt de Análise de Vaga (Melhoria 11)

Para cada vaga encontrada, o agente deve analisar:

```
Analise esta vaga e responda:
1. É compatível com o perfil? (sim/não/parcial)
2. Quais habilidades do candidato são relevantes?
3. Quais requisitos o candidato não atende?
4. Score de 0-100 (justifique)
5. Recomendação: candidatar-se ou não?
6. Dica para a candidatura (se aplicável)
```

---

> Especificação atualizada v2.0 — melhorias 1, 4-14 implementadas (exceto 2 e 3).


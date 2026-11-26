import json, shutil, os
from pathlib import Path
import db

BASE = Path(__file__).parent
BACKUP = BASE / "backup"
BACKUP.mkdir(exist_ok=True)

# Backup dos JSONs
for f in ["historico_vagas.json", "candidaturas.json", "ultimas_vagas.json"]:
    p = BASE / f
    if p.exists():
        shutil.copy2(p, BACKUP / f)
        print(f"Backup: {f}")

db.init_db()

# Migrar histórico (URLs vistas)
hist_file = BASE / "historico_vagas.json"
if hist_file.exists():
    try:
        urls = json.loads(hist_file.read_text(encoding="utf-8"))
        if isinstance(urls, list):
            for u in urls:
                db.upsert_vaga({"titulo": "", "empresa": "", "fonte": "", "score": 0, "url": u})
            print(f"Migradas {len(urls)} URLs do histórico")
    except Exception as e:
        print(f"Erro ao migrar histórico: {e}")

# Migrar candidaturas
cand_file = Path(os.environ.get("VAULT_PATH", str(BASE / "dados_locais"))) / "candidaturas.json"
if cand_file.exists():
    try:
        data = json.loads(cand_file.read_text(encoding="utf-8"))
        apps = data.get("candidaturas", [])
        print(f"Encontradas {len(apps)} candidaturas para migração manual (mantidas no JSON)")
    except Exception as e:
        print(f"Erro: {e}")

print("Migração concluída. Backup em:", BACKUP)
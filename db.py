import hashlib, json, sqlite3
from datetime import datetime
from pathlib import Path

DB_FILE = Path(__file__).parent / "vagas.db"

def _conn():
    c = sqlite3.connect(str(DB_FILE))
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = _conn()
    c.execute("""CREATE TABLE IF NOT EXISTS vagas (
        id TEXT PRIMARY KEY,
        titulo TEXT,
        empresa TEXT,
        fonte TEXT,
        score INTEGER,
        url TEXT,
        primeira_vez TEXT,
        ultima_vez TEXT,
        status TEXT
    )""")
    c.commit()
    c.close()

def url_hash(url):
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:16]

def upsert_vaga(v):
    init_db()
    c = _conn()
    vid = url_hash(v["url"])
    agora = datetime.now().isoformat()
    cur = c.execute("SELECT id FROM vagas WHERE id=?", (vid,)).fetchone()
    if cur:
        c.execute("UPDATE vagas SET titulo=?, empresa=?, fonte=?, score=?, url=?, ultima_vez=? WHERE id=?",
                  (v["titulo"], v.get("empresa",""), v.get("fonte",""), v.get("score",0), v["url"], agora, vid))
        nova = False
    else:
        c.execute("INSERT INTO vagas (id, titulo, empresa, fonte, score, url, primeira_vez, ultima_vez, status) VALUES (?,?,?,?,?,?,?,?,?)",
                  (vid, v["titulo"], v.get("empresa",""), v.get("fonte",""), v.get("score",0), v["url"], agora, agora, "nova"))
        nova = True
    c.commit()
    c.close()
    return nova

def marcar_enviadas(urls):
    init_db()
    c = _conn()
    for u in urls:
        c.execute("UPDATE vagas SET status='enviada' WHERE id=?", (url_hash(u),))
    c.commit()
    c.close()

def listar_novas():
    init_db()
    c = _conn()
    rows = c.execute("SELECT * FROM vagas WHERE status='nova'").fetchall()
    c.close()
    return [dict(r) for r in rows]
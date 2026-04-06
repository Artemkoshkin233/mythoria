from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import json, os, time

app = FastAPI(title="Mythoria Forum API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── База данных ───────────────────────────────────────────
# Railway даёт переменную DATABASE_URL если подключить PostgreSQL.
# Если её нет — используем JSON-файл (работает и локально в Termux).

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # ── PostgreSQL через psycopg2 ──
    import psycopg2
    from psycopg2.extras import RealDictCursor

    def get_conn():
        return psycopg2.connect(DATABASE_URL, sslmode="require")

    def init_db():
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                type TEXT DEFAULT 'fanfic',
                fandom TEXT DEFAULT '',
                author TEXT DEFAULT 'Аноним',
                rating INTEGER DEFAULT 4,
                date TEXT DEFAULT 'Только что',
                views INTEGER DEFAULT 0,
                replies INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                hot BOOLEAN DEFAULT FALSE,
                created_at BIGINT DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS comments (
                id SERIAL PRIMARY KEY,
                post_id TEXT NOT NULL,
                author TEXT DEFAULT 'Аноним',
                av TEXT DEFAULT '👤',
                text TEXT NOT NULL,
                created_at BIGINT DEFAULT 0
            );
        """)
        conn.commit()
        cur.close()
        conn.close()

    def db_get_posts():
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM posts ORDER BY created_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows

    def db_add_post(post_dict):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO posts (id,title,content,type,fandom,author,rating,date,views,replies,likes,hot,created_at)
            VALUES (%(id)s,%(title)s,%(content)s,%(type)s,%(fandom)s,%(author)s,%(rating)s,
                    %(date)s,%(views)s,%(replies)s,%(likes)s,%(hot)s,%(created_at)s)
        """, post_dict)
        conn.commit(); cur.close(); conn.close()

    def db_get_comments(post_id):
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM comments WHERE post_id=%s ORDER BY created_at ASC", (post_id,))
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows

    def db_add_comment(post_id, author, av, text):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO comments (post_id,author,av,text,created_at) VALUES (%s,%s,%s,%s,%s)",
            (post_id, author, av, text, int(time.time()))
        )
        conn.commit(); cur.close(); conn.close()

    init_db()
    print("✅ Подключено к PostgreSQL")

else:
    # ── JSON-файл (Termux / локально) ──
    DB_FILE = "posts.json"
    CMT_FILE = "comments.json"

    def db_get_posts():
        if not os.path.exists(DB_FILE): return []
        return json.load(open(DB_FILE, encoding="utf-8"))

    def db_add_post(post_dict):
        posts = db_get_posts()
        posts.insert(0, post_dict)
        json.dump(posts, open(DB_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    def db_get_comments(post_id):
        if not os.path.exists(CMT_FILE): return []
        all_c = json.load(open(CMT_FILE, encoding="utf-8"))
        return [c for c in all_c if c.get("post_id") == post_id]

    def db_add_comment(post_id, author, av, text):
        all_c = []
        if os.path.exists(CMT_FILE):
            all_c = json.load(open(CMT_FILE, encoding="utf-8"))
        all_c.append({"post_id": post_id, "author": author, "av": av,
                       "text": text, "created_at": int(time.time())})
        json.dump(all_c, open(CMT_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("📁 Используется JSON-база (локальный режим)")


# ─── Модели ────────────────────────────────────────────────

class Post(BaseModel):
    title: str
    content: str
    type: str = "fanfic"
    fandom: str = ""
    author: str = "Аноним"
    rating: int = 4

class Comment(BaseModel):
    author: str = "Аноним"
    av: str = "👤"
    text: str


# ─── Роуты API ─────────────────────────────────────────────

@app.get("/api/posts")
def get_posts():
    return db_get_posts()

@app.post("/api/posts")
def add_post(post: Post):
    new = {
        "id": "srv-" + str(int(time.time() * 1000)),
        "title": post.title,
        "content": post.content,
        "type": post.type,
        "fandom": post.fandom,
        "author": post.author,
        "rating": post.rating,
        "date": "Только что",
        "views": 0,
        "replies": 0,
        "likes": 0,
        "hot": False,
        "created_at": int(time.time()),
    }
    db_add_post(new)
    return new

@app.get("/api/posts/{post_id}/comments")
def get_comments(post_id: str):
    return db_get_comments(post_id)

@app.post("/api/posts/{post_id}/comments")
def add_comment(post_id: str, comment: Comment):
    db_add_comment(post_id, comment.author, comment.av, comment.text)
    return {"ok": True}

@app.get("/api/health")
def health():
    return {"status": "ok", "db": "postgres" if DATABASE_URL else "json"}


# ─── Статика (HTML-файл) ───────────────────────────────────

if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
else:
    @app.get("/")
    def root():
        return {"message": "Mythoria API работает. Положи index.html в папку static/"}


# ─── Запуск ────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)

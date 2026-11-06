"""API da pizzaria: recebe pedidos, grava no PostgreSQL e publica na fila (Redis)."""
import os
import time
from contextlib import asynccontextmanager, contextmanager

import psycopg2
import redis
from fastapi import FastAPI, HTTPException
from psycopg2.pool import ThreadedConnectionPool
from pydantic import BaseModel

DB = dict(
    host=os.getenv("DB_HOST", "db"),
    dbname=os.getenv("DB_NAME", "pizzaria"),
    user=os.getenv("DB_USER", "pizzaria"),
    password=os.getenv("DB_PASSWORD", "secret"),
)
FILA = "fila_pedidos"
PREPARO = float(os.getenv("PREPARO_SEGUNDOS", "1"))

r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), decode_responses=True)
pool = None


@contextmanager
def cursor():
    conn = pool.getconn()
    try:
        with conn:  # commit/rollback automatico
            with conn.cursor() as cur:
                yield cur
    finally:
        pool.putconn(conn)


@asynccontextmanager
async def lifespan(app):
    global pool
    for _ in range(30):
        try:
            pool = ThreadedConnectionPool(1, 20, **DB)
            break
        except psycopg2.OperationalError:
            print("aguardando banco...", flush=True)
            time.sleep(1)
    with cursor() as cur:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS pedidos (
                id SERIAL PRIMARY KEY,
                cliente TEXT NOT NULL,
                sabor TEXT NOT NULL,
                status TEXT NOT NULL,
                worker TEXT,
                criado_em TIMESTAMPTZ DEFAULT now(),
                finalizado_em TIMESTAMPTZ
            )"""
        )
    yield


app = FastAPI(title="Pizzaria Distribuida", lifespan=lifespan)


class PedidoIn(BaseModel):
    cliente: str
    sabor: str


def _inserir(cur, p: PedidoIn, status: str) -> int:
    cur.execute(
        "INSERT INTO pedidos (cliente, sabor, status) VALUES (%s, %s, %s) RETURNING id",
        (p.cliente, p.sabor, status),
    )
    return cur.fetchone()[0]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/pedidos", status_code=202)
def criar_pedido(p: PedidoIn):
    """ASSINCRONO: grava, publica na fila e responde na hora."""
    with cursor() as cur:
        pid = _inserir(cur, p, "recebido")
    r.lpush(FILA, pid)
    print(f"pedido {pid} publicado na fila", flush=True)
    return {"id": pid, "status": "recebido"}


@app.post("/pedidos-sincrono")
def criar_pedido_sincrono(p: PedidoIn):
    """SINCRONO (para comparacao): a propria API prepara o pedido antes de responder."""
    with cursor() as cur:
        pid = _inserir(cur, p, "preparando")
    time.sleep(PREPARO)
    with cursor() as cur:
        cur.execute(
            "UPDATE pedidos SET status='pronto', worker='api', finalizado_em=now() WHERE id=%s",
            (pid,),
        )
    return {"id": pid, "status": "pronto"}


@app.get("/pedidos/{pid}")
def obter_pedido(pid: int):
    with cursor() as cur:
        cur.execute(
            "SELECT id, cliente, sabor, status, worker, criado_em, finalizado_em FROM pedidos WHERE id=%s",
            (pid,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "pedido nao encontrado")
    keys = ["id", "cliente", "sabor", "status", "worker", "criado_em", "finalizado_em"]
    return {k: (str(v) if v is not None and k.endswith("_em") else v) for k, v in zip(keys, row)}


@app.get("/metricas")
def metricas():
    with cursor() as cur:
        cur.execute("SELECT status, count(*) FROM pedidos GROUP BY status")
        por_status = {s: int(n) for s, n in cur.fetchall()}
        cur.execute(
            "SELECT worker, count(*) FROM pedidos WHERE worker IS NOT NULL GROUP BY worker ORDER BY worker"
        )
        por_worker = {w: int(n) for w, n in cur.fetchall()}
        cur.execute(
            "SELECT avg(extract(epoch FROM (finalizado_em - criado_em))) FROM pedidos WHERE finalizado_em IS NOT NULL"
        )
        media = cur.fetchone()[0]
    return {
        "por_status": por_status,
        "por_worker": por_worker,
        "fila_tamanho": r.llen(FILA),
        "tempo_medio_ate_pronto_s": round(float(media), 3) if media is not None else None,
    }


@app.post("/admin/reset")
def reset():
    """Limpa pedidos e fila (usado entre experimentos)."""
    with cursor() as cur:
        cur.execute("TRUNCATE pedidos RESTART IDENTITY")
    r.delete(FILA)
    return {"status": "limpo"}

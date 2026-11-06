"""Worker: consome pedidos da fila (Redis), 'prepara' a pizza e atualiza o status no PostgreSQL."""
import os
import socket
import time

import psycopg2
import redis

FILA = "fila_pedidos"
PREPARO = float(os.getenv("PREPARO_SEGUNDOS", "1"))
WORKER = socket.gethostname()  # id do contêiner

r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), decode_responses=True)


def log(msg):
    print(f"[{WORKER}] {msg}", flush=True)


def conectar_db():
    while True:
        try:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST", "db"),
                dbname=os.getenv("DB_NAME", "pizzaria"),
                user=os.getenv("DB_USER", "pizzaria"),
                password=os.getenv("DB_PASSWORD", "secret"),
            )
            conn.autocommit = True
            return conn
        except psycopg2.OperationalError:
            log("aguardando banco...")
            time.sleep(2)


def main():
    conn = conectar_db()
    log("iniciado, aguardando pedidos")
    while True:
        try:
            item = r.brpop(FILA, timeout=5)
            if not item:
                continue
            pid = int(item[1])
            with conn.cursor() as cur:
                cur.execute("UPDATE pedidos SET status='preparando', worker=%s WHERE id=%s", (WORKER, pid))
            log(f"preparando pedido {pid}")
            time.sleep(PREPARO)
            with conn.cursor() as cur:
                cur.execute("UPDATE pedidos SET status='pronto', finalizado_em=now() WHERE id=%s", (pid,))
            log(f"pedido {pid} pronto")
        except (redis.ConnectionError, psycopg2.Error) as e:
            log(f"erro de conexao: {e}; tentando de novo")
            time.sleep(2)
            if conn.closed:
                conn = conectar_db()


if __name__ == "__main__":
    main()

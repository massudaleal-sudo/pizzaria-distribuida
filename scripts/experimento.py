#!/usr/bin/env python3
"""Gera carga na API e mede latencia, tempo total e vazao. Usa so a biblioteca padrao.

Exemplos:
  python3 scripts/experimento.py --n 50 --rotulo async-1-worker
  python3 scripts/experimento.py --n 50 --modo sync --rotulo sync
"""
import argparse, csv, json, os, statistics, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = os.getenv("API_URL", "http://localhost:8000")


def chamar(metodo, caminho, corpo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    rq = urllib.request.Request(BASE + caminho, data=dados, method=metodo,
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(rq, timeout=300) as resp:
        return json.loads(resp.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50, help="numero de pedidos")
    ap.add_argument("--concorrencia", type=int, default=10, help="requisicoes simultaneas")
    ap.add_argument("--modo", choices=["async", "sync"], default="async")
    ap.add_argument("--sem-espera", action="store_true", help="nao espera o processamento terminar")
    ap.add_argument("--rotulo", default="teste")
    a = ap.parse_args()

    caminho = "/pedidos" if a.modo == "async" else "/pedidos-sincrono"
    chamar("POST", "/admin/reset")

    def enviar(i):
        t = time.time()
        chamar("POST", caminho, {"cliente": f"cliente{i}", "sabor": "calabresa"})
        return time.time() - t

    inicio = time.time()
    with ThreadPoolExecutor(max_workers=a.concorrencia) as ex:
        latencias = sorted(ex.map(enviar, range(a.n)))
    t_envio = time.time() - inicio

    t_total = t_envio
    if a.modo == "async" and not a.sem_espera:
        while time.time() - inicio < 600:
            if chamar("GET", "/metricas")["por_status"].get("pronto", 0) >= a.n:
                break
            time.sleep(0.2)
        t_total = time.time() - inicio

    m = chamar("GET", "/metricas")
    p95 = latencias[int(0.95 * (len(latencias) - 1))]
    res = {
        "rotulo": a.rotulo, "modo": a.modo, "pedidos": a.n, "concorrencia": a.concorrencia,
        "latencia_media_s": round(statistics.mean(latencias), 3),
        "latencia_p95_s": round(p95, 3),
        "tempo_envio_s": round(t_envio, 2),
        "tempo_total_s": round(t_total, 2),
        "vazao_pedidos_por_s": round(a.n / t_total, 2),
        "fila_restante": m["fila_tamanho"],
        "prontos": m["por_status"].get("pronto", 0),
        "por_worker": json.dumps(m["por_worker"]),
    }
    print(json.dumps(res, indent=2, ensure_ascii=False))

    os.makedirs("resultados", exist_ok=True)
    arq = "resultados/resultados.csv"
    novo = not os.path.exists(arq)
    with open(arq, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=res.keys())
        if novo:
            w.writeheader()
        w.writerow(res)


if __name__ == "__main__":
    main()

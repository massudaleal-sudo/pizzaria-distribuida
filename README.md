# Pizzaria Distribuída — Trabalho de Computação Distribuída (UFMS)

Sistema de pedidos de pizzaria dividido em serviços independentes que se comunicam por **fila**.

## Arquitetura

```
 cliente ──HTTP──▶ [ api (FastAPI) ] ──LPUSH id──▶ [ redis (fila) ] ──BRPOP──▶ [ worker (xN) ]
                          │                                                         │
                          └───────────── INSERT / SELECT ──▶ [ db (PostgreSQL) ] ◀──┘ UPDATE
```

| Componente | Tecnologia | Função |
|---|---|---|
| `api` | Python + FastAPI | Recebe pedidos, grava no banco e publica o id na fila |
| `worker` | Python | Consome a fila, "prepara" o pedido e atualiza o status (escalável) |
| `redis` | Redis 7 | Fila de mensagens (broker) |
| `db` | PostgreSQL 16 | Persistência (volume Docker `pgdata`) |

- **Comunicação:** HTTP/REST (cliente→api) e fila Redis (api→worker).
- **Processamento distribuído:** assíncrono e concorrente; vários workers consomem a mesma fila.
- **Persistência:** tabela `pedidos` no PostgreSQL, mantida no volume `pgdata`; api e worker acessam via `psycopg2`.

## Como executar

Requisitos: Docker + Docker Compose.

```bash
docker compose up -d --build
curl http://localhost:8000/health
# criar um pedido
curl -X POST http://localhost:8000/pedidos -H "Content-Type: application/json" \
     -d '{"cliente":"Ana","sabor":"calabresa"}'
curl http://localhost:8000/pedidos/1
curl http://localhost:8000/metricas
docker compose logs -f worker
```
Documentação interativa da API: http://localhost:8000/docs

## Experimentos (reproduzir)

Os resultados são acrescentados em `resultados/resultados.csv`. Cada pedido leva `PREPARO_SEGUNDOS=1` s para ser preparado.

**Experimento 1 (quantitativo): escalabilidade dos workers** — 50 pedidos, 1 vs 3 workers.
```bash
docker compose up -d --scale worker=1
python3 scripts/experimento.py --n 50 --rotulo async-1-worker
docker compose up -d --scale worker=3
python3 scripts/experimento.py --n 50 --rotulo async-3-workers
```
Esperado: tempo total ≈ 50 s com 1 worker e ≈ 17 s com 3; `por_worker` mostra a divisão de carga.

**Experimento 2 (quantitativo): síncrono vs assíncrono** — latência percebida pelo cliente.
```bash
python3 scripts/experimento.py --n 50 --modo sync  --rotulo sync
python3 scripts/experimento.py --n 50 --modo async --rotulo async
```
Esperado: no modo síncrono a resposta demora ≥ 1 s; no assíncrono responde em milissegundos e o trabalho segue em segundo plano.

**Experimento 3: falha de um componente (worker)**
```bash
./scripts/experimento_falha.sh | tee resultados/falha.log
```
Esperado: com o worker parado a API continua aceitando pedidos (ficam na fila); ao reiniciar, a fila é drenada. Variação opcional: `docker compose stop redis` ou `stop db` e observar o erro da API.

## Evidências
Guarde: saída dos scripts, `resultados/resultados.csv`, `resultados/falha.log`, `docker compose ps`, `docker compose logs worker` e capturas de tela do `/docs` e do terminal.

## Limitações / melhorias
- `BRPOP` remove o item da fila: se o worker cair no meio de um pedido, ele é perdido (melhoria: fila confiável com `LMOVE`/ack, ou RabbitMQ).
- Sem autenticação nem testes automatizados.
- Bônus possíveis: GitHub Actions, Prometheus/Grafana, Kubernetes (kind/minikube).

# Relatório Técnico — Pizzaria Distribuída
Disciplina: Computação Distribuída — UFMS | Grupo: (nomes) | Data:

## 1. Problema e objetivo
(Pedidos de pizzaria precisam ser aceitos rapidamente mesmo com a cozinha ocupada...)

## 2. Arquitetura e componentes
(Inserir diagrama e tabela do README. Justificar escolhas: FastAPI, Redis, PostgreSQL, Docker.)

## 3. Comunicação entre componentes
(REST cliente→api; fila Redis api→worker; por que fila e não chamada direta.)

## 4. Execução (Docker)
(Comandos de `docker compose up`, portas, serviços.)

## 5. Persistência
(Tabela `pedidos`, volume `pgdata`, quem lê/escreve.)

## 6. Experimento 1 — Escalabilidade de workers
- Objetivo / Método / Resultados (tabela do CSV) / Interpretação

## 7. Experimento 2 — Síncrono vs assíncrono
- Objetivo / Método / Resultados / Interpretação

## 8. Experimento de falha — Queda do worker
- Cenário / Comportamento observado / Interpretação (desacoplamento, tolerância a falhas)

## 9. Evidências
(Prints, logs, caminhos dos arquivos em `resultados/`.)

## 10. Limitações e melhorias

## 11. Gestão com Trello (opcional)
(Print do quadro: A Fazer / Em Andamento / Concluído.)

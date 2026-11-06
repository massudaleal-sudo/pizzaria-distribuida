#!/usr/bin/env bash
# Experimento de falha: derruba o worker, envia pedidos, restaura o worker e observa a fila drenar.
# Rode no Git Bash / WSL / Linux / macOS.  Registre a saida:  ./scripts/experimento_falha.sh | tee resultados/falha.log
API=${API_URL:-http://localhost:8000}

echo "== 1) Estado inicial =="
curl -s $API/metricas; echo

echo "== 2) Derrubando o worker =="
docker compose stop worker

echo "== 3) Enviando 20 pedidos com o worker FORA do ar =="
python3 scripts/experimento.py --n 20 --sem-espera --rotulo falha-worker-parado
echo "Metricas com worker parado (esperado: pedidos 'recebido' acumulados na fila):"
curl -s $API/metricas; echo

echo "== 4) Restaurando o worker =="
docker compose start worker

echo "== 5) Acompanhando a fila ser drenada =="
for i in $(seq 1 12); do
  sleep 2
  echo "t+$((i*2))s: $(curl -s $API/metricas)"
done
echo "== Fim =="

#!/bin/sh
set -eu

BOOTSTRAP="kafka:19092"

echo "Configurando topicos Kafka..."

# Criar os topicos caso ainda nao existam.
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --create --if-not-exists --topic pedidos.criado --partitions 3 --replication-factor 1

/opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --create --if-not-exists --topic pedidos.criado.dlq --partitions 1 --replication-factor 1

# Aumentar as particoes do topico principal se necessario.
CURRENT_PARTITIONS=$(/opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --describe --topic pedidos.criado | sed -n '1s/.*PartitionCount: *\([0-9][0-9]*\).*/\1/p')

if [ -z "$CURRENT_PARTITIONS" ]; then
    echo "Nao foi possivel consultar as particoes de pedidos.criado."
    exit 1
fi

if [ "$CURRENT_PARTITIONS" -lt 3 ]; then
    /opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --alter --topic pedidos.criado --partitions 3
fi

# Retencao de 3 dias para pedidos e 30 dias para a DLQ.
/opt/kafka/bin/kafka-configs.sh --bootstrap-server "$BOOTSTRAP" --entity-type topics --entity-name pedidos.criado --alter --add-config retention.ms=259200000

/opt/kafka/bin/kafka-configs.sh --bootstrap-server "$BOOTSTRAP" --entity-type topics --entity-name pedidos.criado.dlq --alter --add-config retention.ms=2592000000

# Topicos do fluxo de pagamento e notificacao.
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --create --if-not-exists --topic pagamentos.solicitados --partitions 3 --replication-factor 1
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --create --if-not-exists --topic pagamentos.solicitados.dlq --partitions 3 --replication-factor 1
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --create --if-not-exists --topic pagamentos.processados --partitions 3 --replication-factor 1
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --create --if-not-exists --topic pagamentos.processados.dlq --partitions 3 --replication-factor 1
/opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --create --if-not-exists --topic notificacoes.enviadas --partitions 3 --replication-factor 1
echo "Configuracao dos topicos concluida."

/opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --describe --topic pedidos.criado

/opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP" --describe --topic pedidos.criado.dlq

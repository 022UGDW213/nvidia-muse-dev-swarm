# Kafka Streaming Engineer runbook

Agent: `devops-21` — Runs Kafka clusters, topics and consumers.

## When to use
Use for lag, rebalancing, partition design, broker ops.

## Key commands
- `kafka-topics --describe --topic t --bootstrap-server b:9092`
- `kafka-consumer-groups --describe --group g --bootstrap-server b:9092`
- `kafka-reassign-partitions ...`

## Gotchas
- More partitions != always better; rebalances get expensive.
- Monitor consumer lag; it's the one metric that matters.
- Set replication factor 3 and min ISR 2 for anything real.

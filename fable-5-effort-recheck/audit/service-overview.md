# Meridian — Service Overview

Meridian is the event-ingestion pipeline owned by the Data Platform team. It accepts
telemetry from product surfaces, validates and enriches each event, and lands the
results in the analytics lake. This document describes the architecture as running
in production today.

## Ingress

Producers send events over HTTPS to the ingest gateway on port 8443. The gateway
terminates TLS, authenticates the tenant token, and applies per-tenant rate limiting
at 1200 requests per minute. Requests over the limit receive HTTP 429 with a
Retry-After header.

The gateway runs in the primary region, eu-west-1, with a warm standby deployment
in eu-central-1. Failover is DNS-based and takes under four minutes end to end.

## Event flow

Accepted events are published to the Kafka topic `meridian.events.v2`. The consumer
fleet subscribes through the consumer group `meridian-cg-prod`. Each worker validates
the event against the schema registry, enriches it with tenant metadata, and writes
the result to the lake in Parquet.

Workers are horizontally scaled by the platform autoscaler. Ordering is guaranteed
only within a partition key, never across tenants. Malformed events are routed to
the dead-letter topic `meridian.events.dlq` with the validation error attached.

## State and storage

Pipeline state — offsets, enrichment caches, and tenant configuration — lives in
PostgreSQL 16, provisioned through the shared RDS platform. The state schema is
migrated with Flyway as part of the deploy pipeline; workers refuse to start on a
schema-version mismatch.

Enriched output lands in the analytics lake under `s3://acme-lake/meridian/v2/`.
Raw telemetry is retained for 35 days, after which a lifecycle policy deletes it.
Aggregates derived downstream are owned by the Analytics team and are out of scope
for this document.

During normal operation each worker commits its progress in small increments: as it
drains a batch it updates its enrichment cache in place, emits per-batch metrics to
the statsd sidecar, and checkpoints its consumer offsets every 30 seconds so that a
crash never replays more than a few batches worth of events.

## Reliability

The service targets a 99.9% availability SLA, measured at the ingest gateway.
Synthetic probes run from three regions every minute. Alerting pages the on-call
through the `#meridian-oncall` Slack channel and PagerDuty.

Backpressure is handled at two levels: the gateway sheds load above the rate limit,
and consumers pause partition fetches when lake write latency degrades. Replays are
initiated by resetting the consumer group to an earlier offset; because enrichment
is idempotent, replays are safe by design.

## Deployment

Meridian ships as the `meridian-2.x` Helm chart on the platform Kubernetes cluster.
Rollouts are canary-based: 5% of traffic for the first hour, then a full ramp. The
deploy pipeline blocks on schema migrations, contract tests against the schema
registry, and a smoke suite executed against the canary.

For step-by-step operational procedures, see the deploy runbook maintained by the
same team.

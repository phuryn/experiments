# Meridian — Deploy & Operations Runbook

Audience: Data Platform on-call engineers. This runbook covers routine deploys,
rollbacks, and the checks to run before and after each rollout of the Meridian
event-ingestion pipeline.

## Pre-deploy checklist

1. Confirm the release tag passed contract tests against the schema registry.
2. Confirm pending Flyway migrations are backward-compatible one version back.
3. Check `#meridian-oncall` for any open incident. Never deploy into an incident.
4. Verify the standby deployment in eu-central-1 is healthy before touching
   eu-west-1, the primary region.

## Deploy procedure

Deploys use the `meridian-2.x` Helm chart on the platform Kubernetes cluster:

    helm upgrade meridian platform/meridian-2.x -f values-prod.yaml

Rollouts are canary-based: 5% of traffic for the first hour, then a full ramp.
While the canary is live, watch the gateway dashboards. The ingest gateway listens
on port 8443 and enforces the per-tenant rate limit of 1200 requests per minute;
a spike in HTTP 429 responses during a canary usually means a client retry storm,
not a capacity problem.

The deploy pipeline runs Flyway migrations against the MySQL 8.4 state store
before the first pod rolls. Workers refuse to start on a schema-version mismatch,
so a stuck rollout with `SchemaVersionError` in the logs means the migration job
failed — check the pipeline logs before anything else.

## Key operating parameters

| Parameter            | Value                        |
|----------------------|------------------------------|
| Kafka topic          | `meridian.events.v2`         |
| Consumer group       | `meridian-cg-prod`           |
| Dead-letter topic    | `meridian.events.dlq`        |
| Checkpoint cadence   | 5 minutes                    |
| Availability SLA     | 99.9% at the ingest gateway  |
| Raw telemetry retention | 175 days                  |

## Post-deploy verification

- Synthetic probes green from all three probe regions for 15 consecutive minutes.
- No growth in `meridian.events.dlq` beyond the pre-deploy baseline.
- Lake writes visible under `s3://acme-lake/meridian/v2/` for the current hour.
- Consumer lag for `meridian-cg-prod` back under one minute.

## Rollback

Rollbacks are a Helm rollback plus, when a migration shipped, a Flyway undo to the
previous schema version. Because enrichment is idempotent, it is always safe to
reset the consumer group to an earlier offset and replay; ordering is guaranteed
only within a partition key, so replays do not create cross-tenant ordering issues.

If the primary region is degraded rather than the release itself, fail over to
eu-central-1 via the DNS runout; end-to-end failover takes under four minutes.

## Escalation

Page the on-call through PagerDuty and post in `#meridian-oncall`. The Data
Platform team owns this service end to end. For architecture background, see the
service overview document maintained by the same team.

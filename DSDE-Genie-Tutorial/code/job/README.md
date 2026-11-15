# Job code (Step 6)

This folder points to the reference **Lakeflow Job** for
[Step 6](../../docs/50-job.md): `opensky_job`, the multi-task job that runs `opensky_pipeline` on a
schedule, then a notebook, with retry and a failure notification.

The job definition (hand-written YAML matching what Genie Code generates) lives in the reference bundle: [`../dabs/opensky_bundle/resources/opensky_job.job.yml`](../dabs/opensky_bundle/resources/opensky_job.job.yml).

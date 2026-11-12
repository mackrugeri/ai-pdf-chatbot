# Capacity and Load-Test Plan: AI PDF Chatbot

Status: sizing framework and release targets; no capacity measured
Version: 1.0
Date: 2026-11-13

## 1. Confirmed requirement and unknowns

The user requests **1,000–5,000 requests per second**, not merely that many registered or concurrent users. The architecture retains Python, Ollama, Qwen3 4B, LlamaIndex, ChromaDB, FastAPI, Streamlit, and PostgreSQL, with the supporting services in [TECH_STACK.md](TECH_STACK.md).

The endpoint mix, active browser sessions, prompt/output distributions, corpus size, upload size/rate, latency SLOs, and infrastructure budget are unresolved. Therefore no server count, GPU count, monthly cost, or achieved throughput can honestly be specified yet. A developer Mac is a functional development environment, not evidence of this production capacity. The old 15-day roadmap is not a schedule commitment for this system.

## 2. Keep measurements distinct

Report all of the following, not a single aggregate success number:

- Offered RPS from the load generator, accepted RPS, intentional rejections, transport/server failures, and completed operations/second.
- HTTP submission latency versus queue wait versus complete-answer latency.
- Upload initialization/completion requests versus transferred bytes/second and PDFs/pages/chunks indexed per second.
- Retrieval QPS versus answer QPS, prompt tokens/second, output tokens/second, and useful supported answers/second.
- Browser/WebSocket session counts and UI performance versus backend API-only measurements.
- Broker deliveries versus unique durable jobs completed; duplicate retries are not new useful work.

`202 Accepted` proves acceptance, not a generated answer. `429` proves overload protection, not full successful capacity. A cache hit is reported separately from fresh inference. Health/status-only tests cannot certify document/chat throughput.

## 3. Workload profiles

Build a configurable workload file and agree on the exact production mix before signoff. Initially test these separately at 1,000, 2,500, and 5,000 offered RPS:

| Profile | Purpose | Required reporting |
| --- | --- | --- |
| Metadata/control | Authenticated listing, detail, and job reads with representative pagination and data sizes | DB pool use, cache hit/miss, authorization costs, p95/p99 latency. |
| Fresh chat | Every request submits a unique authorized question; no answer cache | Accepted and completed answer QPS, queue age/growth, token throughput, quality, deadlines. |
| Upload/ingestion | Representative bounded files, plus completion/retry requests | Actual byte/page/chunk rates, parser memory, embedding QPS, object/vector writes. |
| Agreed mixed traffic | Realistic explicitly stated route mix | Weighted throughput plus each route's latency/error distribution. |
| Browser/UI | Realistic Streamlit sessions, uploads, reruns, polling, reconnect, and login | Session capacity, WebSocket behavior, affinity, memory, ingress/API traffic amplification. |

A full 5,000-RPS chatbot claim requires the fresh-chat profile to sustain that rate within its agreed answer SLO; a mixed-profile result must be labeled with its mix. The session count cannot be derived from RPS alone. Never silently lower generation frequency or output length merely to make a test pass.

## 4. First-order sizing calculations

These calculations illustrate demand; they are not benchmarks.

Let `lambda` be successful fresh-answer requests/second, `T` mean end-to-end seconds in a stable system, `I` mean input tokens/request, and `O` mean output tokens/request.

```text
Mean in-flight answer requests = lambda * T
Required prompt throughput    = lambda * I
Required output throughput    = lambda * O
Minimum measured replica count = ceil(lambda / (q_replica * u))
```

`q_replica` is measured completed requests/second for one replica under the actual token/corpus/batching profile. `u` is chosen safe operating utilization, below saturation, with extra failover and warmup headroom. Measure prefill/decode and tail latency together; a raw single-stream tokens/second number cannot determine request capacity.

Example only: if 5,000 requests/second are all new questions, each has 2,000 input and 400 output tokens, and mean answer latency is 30 seconds:

- Demand is 10 million input tokens/second and 2 million output tokens/second.
- Mean in-flight work is about 150,000 requests in a stable system.
- This says nothing about achievable GPU throughput or cost; those require hardware benchmarks.

If only 10% of the same aggregate 5,000 RPS were fresh chat, fresh-answer demand would instead be 500 requests/second. That 10% is an example, not an accepted workload assumption.

Also budget UI/identity traffic, polling, network egress, vector retrieval, query embeddings, ingestion embeddings, broker/outbox writes, result reads, object storage, and per-user quotas. For example, 10,000 pending jobs polled once every two seconds add 5,000 status reads/second by themselves; use backoff/jitter/conditional reads and count this overhead.

## 5. Component capacity tests

1. **FastAPI/ingress:** authenticated real validation and representative responses, then isolated stub-downstream tests to locate overhead. Report both; stubs do not certify end to end.
2. **Streamlit:** measure sessions, memory/session, rerun CPU, uploads, affinity, draining, and reconnect; prove the actual UI path rather than bypassing it. Selected UI stays a release gate.
3. **PostgreSQL:** benchmark ownership/list queries, job/results/outbox writes, indexes, pool limits, migrations, replication/failover, and cleanup under representative data volume.
4. **ChromaDB:** benchmark the chosen supported service/distributed topology with realistic owner filters, corpus/chunk counts, simultaneous writes, index sizes, and p95/p99 retrieval latency. Confirm licensing/availability and operating requirements; do not assume standalone pods become distributed by sharing a volume.
5. **Embedding/generation:** test model identity, tokenizer, quantization, lengths, concurrency, warm/cold behavior, memory/KV cache, GPU utilization, per-replica throughput, and failure recovery. Distinguish embedding from generation demand.
6. **Queues/admission:** prove durable publication, duplicate handling, fair quotas, bounded backlog, deadlines, recovery, and stable completion rate. Autoscaling must account for model-loading delay.
7. **Object/network tier:** prove upload byte throughput, parallel streams, private access, signed-URL behavior, and retention cleanup. HTTP request count does not size bandwidth.

## 6. Benchmark procedure and gates

Use a versioned open-loop k6 or Locust scenario on independent load generators that can themselves sustain the offered rate. Synchronize clocks and record exact image/model/index/config identities. Separate cold-cache/warm-cache and cold-model/warm-model results.

Suggested test sequence: functional smoke -> component saturation search -> 1,000-RPS sustained -> 2,500-RPS sustained -> 5,000-RPS sustained -> mixed soak -> burst/overload -> failure recovery. Initial sustained tests run at least 30 minutes after warmup, followed by a two-hour target-profile soak. Longer operational observation is still needed for availability claims.

Before executing certification, set p95/p99 API and complete-answer latency budgets, error/acceptance targets, maximum queue age, upload service budgets, corpus sizes, and allowed failure windows in the workload file. These are release-blocking decisions, not blanks to hide in a report. A successful run must meet those targets, maintain bounded/stable queues, complete the admitted workload, preserve authorization/citation correctness, and survive the defined failure test. Use enough generation time after an arrival burst to observe completion; never stop at admission.

Test worker/pod/node loss, model timeout, broker failover, database failover, Redis unavailability, object/vector errors, and deletion during retries. Verify no cross-owner exposure and no lost durable accepted jobs. Planned overload rejects count separately; report offered-to-completed ratios honestly.

## 7. Scaling and readiness decisions

Size each tier from its measured bottleneck. Use independently scaled API/UI/worker pools and GPU pools, connection budgets, durable queues, and shared storage. Scaling adds resources and operational cost; load balancing cannot manufacture model capacity. Maintain warm headroom and fair per-owner quotas; admission must reject excess rather than let tail latency grow without bound.

If Streamlit, the available Chroma deployment, or Ollama/Qwen3 serving cannot meet the agreed profile, record the component limitation, achieved results, resource estimates, and alternatives. Ask the project owner before replacing a selected main-stack technology. The release may be certified for a smaller explicitly labeled profile, but not advertised as 5,000 RPS without the required evidence.

## 8. Benchmark report template

Record date/commit; region/hardware/GPU/network; replica counts; exact versions/models; corpus; owner/session counts; endpoint mix; input/output distributions; offered/admitted/completed RPS; cache hits; errors/rejections; p50/p95/p99 timings; queue depth/age trend; token rates; database/vector/object metrics; resource utilization and observed cost; faults and recovery; quality/isolation results; pass/fail against predeclared budgets; remaining blockers.

References informing tests: [Streamlit replication](https://docs.streamlit.io/develop/concepts/architecture/architecture), [Chroma distributed architecture](https://docs.trychroma.com/reference/architecture/distributed), [Ollama concurrency and memory configuration](https://docs.ollama.com/faq), and [Kubernetes autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/). The sizing equations and examples above are derived workload calculations, not capacities stated by those projects.

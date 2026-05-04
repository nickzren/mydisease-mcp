# Agent Guide — mydisease-mcp

Brief for AI coding agents (Claude Code, Codex) working in this repo or routing biomedical questions through it.

## What this server is
MCP server wrapping the [MyDisease.info](https://mydisease.info/) API. Aggregates disease annotations from OMIM, Orphanet, DisGeNET, ClinVar, HPO, GWAS Catalog, CTD, KEGG, and UniProt.

## Run locally (stdio)
```bash
uv sync
uv run python -m mydisease_mcp.server            # stdio (default)
```

HTTP/SSE: append `--transport http --host 127.0.0.1 --port 8000`.

## Use this server for
- Disease search by name, ID, symptom, or any text field
- Gene–disease associations (DisGeNET-anchored)
- Variant-anchored disease associations and ClinVar annotations
- Phenotype mapping by HPO terms / clinical features
- Disease ontology navigation across MONDO/OMIM/Orphanet/MeSH/UMLS
- GWAS hits, pathway-level disease views, drug–disease relationships
- Epidemiology (prevalence, incidence, demographics)
- Batch processing (up to 1000 diseases per request)

Prefer over other servers when the question is **disease-centric annotation aggregation across many sources** — use opentargets-mcp for scored target-disease evidence and monarch-mcp for cross-species / phenotype-similarity diagnostics.

## Triage hints
- "What's known about disease X" multi-source dump → MyDisease.
- "Genes associated with disease X with confidence" → OpenTargets `get_disease_associated_targets`.
- "Phenotypes similar to this HPO profile" → Monarch.
- ClinVar variant-anchored disease lookup → MyDisease.

## Pitfalls
- Records are large and heterogeneous; ask for specific fields when possible.
- Some sources lag (OMIM updates infrequent vs DisGeNET); cite the source on synthesis.
- Epidemiology data is sparse and population-specific — never extrapolate without the source caveat.

## Source layout
- `src/mydisease_mcp/server.py` — FastMCP entrypoint
- `src/mydisease_mcp/client.py` — HTTP client to MyDisease.info
- `src/mydisease_mcp/tools/` — tool implementations

## Dev
```bash
uv run --extra test pytest tests/ -v
```

## When editing tools
1. Add HTTP call in `client.py` if a new endpoint is needed.
2. Wrap in a tool under `src/mydisease_mcp/tools/`; expose via the registry.
3. Add a unit test mocking the HTTP response.

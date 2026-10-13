# DNA Origami CAODNA Router

### [Open the Live Application →](https://abusuraihsakhri.github.io/dna-origami-caodna-router/)

A rule-based Python audit and telemetry demonstrator with a browser preview, command-line interfaces and an optional FastAPI service. It evaluates illustrative numeric thresholds and status keywords; it is **not** a caDNAno scaffold-routing engine.

**Scientific scope:** The current code does not generate scaffold paths, crossover arrangements, staple DNA sequences, melting-temperature predictions or experimentally validated DNA-origami designs. Thresholds are demonstration settings, not caDNAno, IUPAC or clinical reference limits. The enrichment modules likewise provide generic threshold assessments rather than molecular simulation.

## Browser preview

Open [web/index.html](web/index.html) in a browser, or serve the Python API locally and visit `http://127.0.0.1:8000/`. The **Browser preview** mode runs entirely on-device and uses the legacy worker rules (primary threshold 25; secondary threshold 12; configured anomaly keywords and critical flag). Results can be exported as JSON. The preview does not create an audit log or cryptographic signature, and it does not transmit values.

Select **Server audit** only when the FastAPI application is running. Server mode sends inputs to `/api/audit` and returns the actual Python dossier including an HMAC audit-chain hash. Do not use real patient identifiers.

## Python setup

Python 3.10 or later:

```bash
python -m pip install -e ".[api,dev]"
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
python -m pytest -q
python cli.py audit --task-id T-1 --target SYNTHETIC-01 --primary 29.4 --secondary 14.8
python cli.py serve --host 127.0.0.1 --port 8000
```

The packaged entry point `dna-origami-caodna-router` invokes the separate `dna_origami_router.cli` compatibility interface, which has a different illustrative secondary threshold (10) and no HMAC logging. The root `cli.py` and Docker service use `agents/` with secondary threshold 12. These implementations are retained for compatibility and should not be mistaken for a single validated scientific model.

### Root CLI commands

- `python cli.py audit --task-id T-1 --target SYNTHETIC-01 --primary 26 --secondary 13 --status NOMINAL`
- `python cli.py batch -i sample.csv -o results.csv`
- `python cli.py chat "status"` — deterministic mock response only
- `python cli.py verify-audit` — checks the current **in-memory** audit chain (not past processes)
- `python simulator.py 100` — synthetic throughput demonstration

## REST API

Start with `python cli.py serve`; the API provides `GET /` (web page), `GET /health`, `GET /metrics` (JSON), `POST /api/audit`, `POST /api/chat` (mock), and `GET /api/audit/logs`.

`AUDIT_SECRET_KEY` is required for signed evaluations and must contain at least 32 characters. Never commit a real key. The audit-chain ledger resides in memory and is lost on restart. Access to `/api/audit/logs` is **denied by default**; to enable it, set an independent `AUDIT_LOG_READ_TOKEN` of at least 32 characters and supply `Authorization: Bearer <token>`.

```bash
curl -sS -X POST http://127.0.0.1:8000/api/audit \
  -H 'Content-Type: application/json' \
  -d '{"task_id":"DEMO-1","target_identifier":"SYNTHETIC","primary_metric":26,"secondary_metric":13}'
```

The service uses regex-based identifier screening, which is **not** a complete PHI detection or HIPAA compliance guarantee. Do not expose the unauthenticated evaluation API to the public internet; put authentication, TLS and rate limiting in front of it if deployed.

## Docker

Create `.env` locally from `.env.example`, fill in the empty signing-key value with a unique random secret, then run:

```bash
docker compose up --build
```

The example Compose configuration binds port 8000 to localhost only. The container runs under a non-root user. Do not commit `.env`.

## Tests and technology

`python -m pytest -q` tests the two legacy rule interfaces, enrichment demonstration, audit chain, identifier screening and API behavior. GitHub Actions also builds Python distributions and checks embedded browser JavaScript syntax on Python 3.10, 3.11 and 3.12. The implementation uses Python, Pydantic v2, optional FastAPI/Uvicorn, and plain HTML/CSS/JavaScript; no runtime external LLM provider is implemented.

The browser preview targets modern desktop and mobile browsers with JavaScript enabled. It does not require Python or Pyodide. The GitHub Pages workflow publishes the static browser preview from the `web/` directory; it does not host the Python API.

## License

[MIT](LICENSE).

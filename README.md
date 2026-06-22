# sofascore-py

A small **Python (FastAPI + curl_cffi)** wrapper around the public SofaScore
**football (soccer)** v1 API, with interactive **Swagger** docs.

It mirrors the upstream endpoints 1:1 and transparently:

- impersonates a real browser's **TLS / JA3 fingerprint** with `curl_cffi`
  (this is the part the Go stdlib and plain `requests` can't do),
- attaches the rotating `X-Requested-With` token + `Sec-Fetch-*` headers
  SofaScore requires, and
- optionally routes DNS through **DNS-over-HTTPS (DoH)** (e.g. Cloudflare,
  Google) via `CurlOpt.DOH_URL`, bypassing the system/ISP resolver.

FastAPI generates the OpenAPI spec and Swagger UI for you — no hand-written spec.

## Install & run

```bash
cd sofascore-py
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt

uvicorn main:app --port 8080 --reload
# or simply:
python main.py
# If you use an Indonesian ISP, use this.
DOH_URL=https://dns.google/dns-query uvicorn main:app --port 8080 --reload
```

- Swagger UI:  http://localhost:8080/docs
- ReDoc:       http://localhost:8080/redoc
- OpenAPI:     http://localhost:8080/openapi.json
- Health/token: http://localhost:8080/healthz

## Endpoints Note

> `/team/{id}/events/next` and `/events/last` map to the upstream paginated
> paths `/events/next/0` and `/events/last/0` (page 0).

## How the bypass works

| Requirement | How it's handled |
|---|---|
| Browser TLS/JA3 fingerprint | `curl_cffi` `Session(impersonate="chrome")` |
| `X-Requested-With` token | `sha256(floor(unix/1800))[:6]`, rotates every 30 min |


## Configuration (env vars)

| Var | Default | Meaning |
|---|---|---|
| `PORT` | `8080` | Listen port (when run via `python main.py`) |
| `HOST` | `0.0.0.0` | Bind host |
| `IMPERSONATE` | `chrome` | curl_cffi target, e.g. `chrome131`, `firefox135` |
| `TIMEOUT` | `20` | Request timeout in seconds |
| `DOH_URL` | unset | DoH endpoint, e.g. `https://cloudflare-dns.com/dns-query` |
| `RELOAD` | unset | Set to any value to auto-reload |


## Layout

```
sofascore-py/
  main.py               FastAPI app + routes (auto Swagger at /docs)
  sofascore_client.py   curl_cffi client: TLS impersonation + token + DoH
  requirements.txt
  README.md
```

## Disclaimer

Unofficial wrapper of SofaScore's private API for educational use. Respect their
terms of service and rate limits.

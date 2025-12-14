# P11 DAST (OWASP ZAP baseline) — scan summary for PR

Target URL scanned: http://localhost:8000/ (CI uses `/health` to check readiness)

Summary of findings (from baseline run included in repo as example):

- High: 0
- Medium: 1
- Low: 2

Planned actions:

- Review the single Medium alert and decide whether to fix or accept as false positive.
- Low findings: accept as informational for now; track any actionable ones in issues.

Notes:

- The workflow `.github/workflows/ci-p11-dast.yml` starts the app on sqlite (DATABASE_URL=sqlite:///./zap_ci.db) with `AUTH_ENABLED=false` to allow baseline scanning in CI.
- CI run uploads the generated reports as workflow artifacts and writes them to `EVIDENCE/P11/` in the run workspace.

To reproduce locally:

```bash
python -m pip install -r requirements.txt
DATABASE_URL="sqlite:///./zap_ci.db" AUTH_ENABLED=false python -m uvicorn app.main:app --port 8000
# then run ZAP baseline against http://localhost:8000
```

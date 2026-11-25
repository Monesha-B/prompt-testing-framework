# Prompt Testing Framework
Compare baseline and candidate prompts on a fictional customer-support policy using automated phrase assertions, regression detection, latency and token metrics, and CSV/JSON exports.

## Run locally
```sh
conda create -n prompt-testing python=3.11 -y
conda activate prompt-testing
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```
Offline mode uses fixed fictional responses and simulated latency/word-based token estimates; it does not measure the effect of editing prompts. Live mode uses Gemini REST with actual usage metadata and measured request latency. Phrase checks are not semantic correctness guarantees. Failed calls are not scored. Live mode can consume quota; use a free-tier project and monitor limits. For deployment, keep live mode disabled by leaving the key unconfigured unless you accept public visitors consuming your quota.

Configure `GEMINI_API_KEY` as an environment variable or in Streamlit secrets (never commit the key). Select an available free-tier model. CI runs offline tests without credentials.

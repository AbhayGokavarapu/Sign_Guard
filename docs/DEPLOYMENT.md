# Streamlit Community Cloud

1. Open https://share.streamlit.io/ and sign in with the GitHub account that can access this repository.
2. Select Create app / Deploy a public app from GitHub.
3. Repository: `AbhayGokavarapu/Sign_Guard`.
4. Branch: `streamlit-deploy`.
5. Main file path: `streamlit_app.py`.
6. Advanced settings: choose Python **3.12**. No API keys or secrets are needed for the synthetic demo.
7. Choose an available app URL and click Deploy. Wait for dependency installation and app startup.
8. Test scenarios A–D and download a report. If startup fails, inspect Manage app → Logs and retain the actual exception.

Cloud deploys from GitHub; edits made only in a Codex workspace do not appear until committed and pushed. A public Streamlit URL is not `localhost`: localhost always refers to the computer running the browser.

The public entry point disables shared audit logging/history and the expensive benchmark regeneration button. It displays a server-side processing notice. Uploaded PDFs stay in the session/application memory while analysed; download reports before leaving. Do not upload sensitive PDFs to this public research demo. Hosted storage is ephemeral and must not be represented as permanent audit custody.

The worker uses a 2048 MiB virtual address-space limit for this entry point, plus the existing rendering/timeout limits. Virtual address space includes library mappings and is not physical memory. Available physical memory and platform quotas may still reject large PDFs. Resource controls are not a complete exploit sandbox. Certificate revocation and trusted timestamps remain unsupported.

For local development, use `launch.bat` or `sh launch.sh` for http://localhost:8502. To use the Python command directly:

```bash
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

The shared config intentionally does not force a port/address: Community Cloud supplies its own network settings. Dependencies are in `requirements.txt`; Python 3.12 is selected in the deployment UI.

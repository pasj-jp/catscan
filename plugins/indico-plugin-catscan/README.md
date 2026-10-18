# CatScan Indico Plugin (`indico-plugin-catscan`)

An official Indico plugin that seamlessly bridges **Indico Paper Editing** with **CatScan** automated paper formatting validation.

---

## Features

- **Automated Instant Review**: When an author submits a new paper manuscript (Word `.docx` or LaTeX `.tex`) or uploads a revision, the plugin automatically triggers CatScan to scan the paper.
- **Timeline Feedback**: CatScan validates formatting against publication guidelines (JACoW or PASJ) and posts diagnostic feedback and interactive report links directly to the Indico revision timeline.
- **Zero-Block Architecture**: Uses Celery asynchronous background tasks (with an automatic fallback to daemon threads) so that author uploads are never delayed.
- **Configurable Settings**: Provides a standard Indico Admin UI setting form to customize the CatScan API URL, toggle auto-scanning, or set optional auth tokens.

---

## Installation & Deployment

Inside the Indico virtual environment (e.g. `/opt/indico/.venv`):

```bash
# 1. Install plugin into Indico's virtual environment:
# Option A (Remote install directly from GitHub monorepo):
pip install "git+https://github.com/<owner>/catscan.git#subdirectory=plugins/indico-plugin-catscan"

# Option B (Local editable/development mode):
pip install -e /path/to/catscan/plugins/indico-plugin-catscan

# 2. Enable the plugin in /opt/indico/etc/indico.conf
# Add 'catscan' to PLUGINS set:
PLUGINS = {'catscan'}

# 3. Reload Indico uWSGI and Celery
touch ~/web/indico.wsgi
sudo systemctl restart indico-celery
```

---

## Configuration

In Indico:
1. Log in as an administrator.
2. Go to **Administration** -> **Plugins**.
3. Locate **CatScan** and click **Configure**.
4. Adjust settings:
   - **CatScan Internal API URL**: Default is `http://127.0.0.1:8000`.
   - **Auto-scan on manuscript upload**: Checkbox (default: `True`).
   - **CatScan API Token**: Optional bearer token.

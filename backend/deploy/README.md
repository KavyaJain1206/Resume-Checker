# Deploying to a Linux VPS

## 1. Postgres

```bash
sudo -u postgres psql -c "CREATE ROLE resume_app WITH LOGIN PASSWORD 'strong-password-here';"
sudo -u postgres psql -c "CREATE DATABASE resume_playbook OWNER resume_app;"
```

## 2. App user + code

```bash
sudo useradd --system --home /opt/resume-playbook-diagnostic --shell /usr/sbin/nologin resume_playbook
sudo mkdir -p /opt/resume-playbook-diagnostic
sudo chown resume_playbook:resume_playbook /opt/resume-playbook-diagnostic
# deploy the repo into /opt/resume-playbook-diagnostic (git clone / rsync / CI artifact)
```

## 3. Backend environment

```bash
cd /opt/resume-playbook-diagnostic/backend
sudo -u resume_playbook python3 -m venv .venv
sudo -u resume_playbook .venv/bin/pip install -r requirements.txt
sudo -u resume_playbook cp .env.example .env
# edit .env: DATABASE_URL, SECRET_KEY, ADMIN_PASSWORD, CORS_ORIGINS, ENVIRONMENT=production
```

## 4. Schema — migration-driven, never on app startup

```bash
sudo -u resume_playbook .venv/bin/alembic upgrade head
```

The systemd unit in `resume-playbook.service` also runs the same migration
command before each start, so a fresh pull lands on the latest schema before
the API accepts traffic.

If you're cutting over from an existing JSON-store deployment, import its data once:

```bash
sudo -u resume_playbook .venv/bin/python -m scripts.migrate_json_to_postgres
```

## 5. systemd

```bash
sudo cp deploy/resume-playbook.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now resume-playbook
sudo systemctl status resume-playbook
journalctl -u resume-playbook -f          # tail logs
```

## 6. Frontend

```bash
cd /opt/resume-playbook-diagnostic/frontend
npm ci
npm run build      # -> dist/, served by nginx (see deploy/nginx.conf.example)
```

## 7. nginx

```bash
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/resume-playbook
sudo ln -s /etc/nginx/sites-available/resume-playbook /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## Rolling out a schema change later

```bash
# after editing/adding a model:
.venv/bin/alembic revision --autogenerate -m "describe the change"
# review the generated file in migrations/versions/, then:
.venv/bin/alembic upgrade head
```

## Health check

`GET /api/health` returns `{"ok": true, ...}` only when the database is
actually reachable — point uptime monitoring / load balancer health checks
at this, not just a TCP check on port 8000.

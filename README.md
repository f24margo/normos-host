# NormOS Host

**Execution platform for NormOS** — hosted working place for territorial communities (hromadas).

| | |
|---|---|
| **Status** | MVP-v0.1-pre-alpha |
| **Architecture** | [ARCHITECTURE.md](./ARCHITECTURE.md) (HM-001) |
| **Host overview** | [HOST.md](./HOST.md) |
| **Analysis core** | separate repo / lab (`normos-lab`) — not duplicated here |

---

## What this is

NormOS Host gives **2–3 pilot hromadas** a browser workspace:

- login and roles;
- document text analysis (via NormOS core);
- data isolation per hromada (`tenant`);
- infrastructure run by the Host team — communities install nothing.

This is **not** a legal advice service, not a state register, and not an automated “lawful / unlawful” verdict.

---

## Repository layout

```text
normos-host/
├── ARCHITECTURE.md      # HM-001 — main architecture (source of truth)
├── HOST.md              # Host responsibilities (short)
├── README.md
├── requirements.txt
├── manage.py            # Django entrypoint
├── db.sqlite3           # local dev DB (not for production secrets)
├── host/                # Django project / app package
├── hostui/              # UI-related app (as implemented)
├── docs/                # extra notes
├── packages/            # reserved for future rule packages
└── tests/


Exact app names may evolve; behavioural contract is defined in ARCHITECTURE.md.

Principles (pilot)

Hosted-only — user needs a browser and an account.
Human-in-the-loop — hints only; humans decide.
Tenant isolation — hromada A never sees hromada B.
Thin host, smart core — analysis engine lives in lab/core; Host provides access and UI.
No AI agent / no public self-registration in v0.1.


Pilot scope

2–3 tenants (hromadas);
3–4 roles/users per tenant (e.g. secretary, lawyer, viewer, local admin);
Feature: login → paste/upload text → analysis result in plain language.

Scaling to ~10 hromadas keeps the same model (more tenants, same delivery).

Documentation

Doc                     Purpose
ARCHITECTURE.md Mission, components, tenant model, roadmap, non-goals
HOST.md                 What the Host provides

Grant / public project vitrine (e.g. GitHub Pages) is optional and separate from this application.

Development
Local setup will be described as the Django skeleton stabilises. Typical direction:

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

Do not commit secrets. Prefer environment variables for production.

Disclaimer
Output of the system is a support tool for reading municipal documents.
It is not legal advice and does not replace a lawyer, the council, or official procedures.

---

**Дальше по желанию (не обязательно сегодня):**  
коротко обновить `HOST.md` в 15–20 строк под тот же смысл — чтобы README / HOST / ARCHITECTURE не расходились.

Практически вы уже в режиме «документация + Django параллельно»: архитектура зафиксирована, README только отражает это снаружи.
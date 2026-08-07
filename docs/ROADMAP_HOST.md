# ROADMAP — NormOS Host (пилот)

**Status:** active  
**Scope:** v0.1 hosted cabinet for 2–3 hromadas (login, tenant, analyze)  
**Architecture:** [ARCHITECTURE.md](../ARCHITECTURE.md) (HM-001)  
**Out of scope for this roadmap:** AI agent, Wix, self-registration, full `msu_ua` law package, MCP  

This checklist is **ordered**, not calendar-bound.  
If work pauses, resume from the first unchecked item. Progress is measured by checkboxes, not by “two weeks elapsed.”

---

## Goal

- Runnable Host: login → tenant-scoped user → document text analysis  
- Docs (README / HOST / ARCHITECTURE) stay aligned  
- Same model later scales to ~10 hromadas without redesign  

---

## Days 1–14 (checklist)

| Day | Task | Done |
|-----|------|:----:|
| **1** | Update `README.md` to match HM-001; ensure §5 diagram (Browser → UI → API → core → DB) is in `ARCHITECTURE.md` | ☐ |
| **2** | Short `HOST.md` (one screen): responsibilities, non-goals, link to ARCHITECTURE | ☐ |
| **3** | Django apps for tenant + user profile (`Tenant`, `role` on user/profile); `migrate` | ☐ |
| **4** | Create superuser; create **1** tenant in Admin | ☐ |
| **5** | Login / logout (Django auth) works in browser | ☐ |
| **6** | Login-required empty workspace page (anonymous redirected) | ☐ |
| **7** | Form: paste text → submit → **stub** result page (e.g. length / echo) + disclaimer | ☐ |
| **8** | Enforce `tenant_id` (or equivalent) on any saved analysis data / queries | ☐ |
| **9** | Seed **2–3** test tenants and **3–4** users per tenant via Admin | ☐ |
| **10** | Wire analysis **core** from lab (`InferenceEngine` or agreed adapter); replace stub | ☐ |
| **11** | Result UI in plain language (no internal jargon: registry, modality, NKS) | ☐ |
| **12** | Optional: `Analysis` model (tenant, user, timestamp, summary/result JSON) + simple list | ☐ |
| **13** | `docs/PILOT.md`: how we issue access to a hromada (URL, logins, one-page user note) | ☐ |
| **14** | Acceptance run: two users from **different** tenants; confirm isolation + analyze works | ☐ |

---

## Acceptance criteria (end of checklist)

- [ ] Architecture docs consistent with running app  
- [ ] Login works  
- [ ] At least two tenants exist; users cannot see each other’s tenant data  
- [ ] Analyze returns core-based (or explicitly temporary stub noted in README)  
- [ ] Disclaimer visible on result  
- [ ] Operator can add a new tenant + users in Admin in ~10 minutes  

---

## Explicitly deferred (do not block the checklist)

| Item | When to revisit |
|------|-----------------|
| AI agent / LLM connector | After pilot UX is stable |
| Project vitrine (GitHub Pages / site) | Parallel, non-blocking |
| Postgres in production | Before external pilot server / VPS |
| `msu_ua` norms package | After user surveys |
| ~10 hromadas | After 2–3 tenant pilot acceptance |
| Event bus / package manager | Per HM-001 “later” |

---

## How to use after a pause

1. Open this file.  
2. Find the first row with ☐.  
3. Continue from there.  
4. If implementation taught something new, change **one** short note in `ARCHITECTURE.md` — do not rewrite the roadmap from scratch.

---

## Related

- [ARCHITECTURE.md](../ARCHITECTURE.md)  
- [HOST.md](../HOST.md)  
- [README.md](../README.md)  

---

*ROADMAP_HOST — ordered pilot checklist; duration may exceed two calendar weeks.*
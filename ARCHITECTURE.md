

### `ARCHITECTURE.md`

```markdown
# NormOS Host — Architecture

**Document ID:** HM-ARCH-001  
**Status:** Working (post demo-inspector)  
**Repo:** normos-host  
**Related:** packages/msu_ua, NKS-000…NKS-013 (lab), HOST.md

---

## 1. Purpose

NormOS Host — **execution layer** for normative analysis of local self-government (MSU) texts.

It does **not** invent legal conclusions. It:

1. finds normative actions (verbs) and modality markers in text;
2. links hits to **norm cards** from package `msu_ua`;
3. builds clause-level triplets ⟨Subject, Modality, Action⟩;
4. exposes an explainable UI (layers, inspector, dependency graph).

Legal responsibility stays with the human operator.

---

## 2. System split: Host vs Package vs Lab

| Layer | Location | Role |
|-------|----------|------|
| **Host** | this repo (`hostui/`, Django) | Auth surface, HTTP API, UI, orchestration |
| **Package `msu_ua`** | `packages/msu_ua/` | Norm cards, sources, lookup indices |
| **Lab / theory** | normos-lab-demo (separate) | NKS specs, verb alphabet research, alignment metrics |

Host **consumes** the package through `RegistryService`.  
Package content can evolve (new cards, index rebuild) without rewriting Host pipeline, as long as schemas stay compatible.

---

## 3. Runtime data flow

```
Browser (workspace)
    │  POST /api/analyze/  { text, layers[] }
    ▼
views.analyze_api
    ▼
services.normos.analyze_document
    ▼
services.markup.analyze_document_pipeline
    │
    ├─ RegistryService  ← packages/msu_ua/index/* + cards/*
    ├─ roles.find_agent_forms_in_text
    ├─ verb scan via by_verb index → matched_verbs_list (+ card_ids)
    ├─ modality markers (clause-local)
    ├─ triplets.build_clause_triplets  → ⟨S, M, A⟩ + cards[] + depends_on
    ├─ graph.build_norm_graph
    └─ recommender.generate_recommendations
    ▼
JSON: { text, spans, triplets, graph, metrics, oov, matched_cards_count }
    ▼
workspace.html
    ├─ renderHighlights (layers: verbs | modality | roles | msu)
    ├─ renderInspectorData (triplets + expanded norm cards)
    └─ vis-network graph modal
```

---

## 4. Package `msu_ua` contract

### 4.1 Layout

```
packages/msu_ua/
  package.json          # sources list, cards_count
  cards/N01.json … N51.json
  sources/              # act-level reference JSON
  index/
    by_verb.json        # verb_lemma_or_phrase → [card_id, …]
    by_agent.json       # agent phrase → [card_id, …]
    by_source.json      # source_id → [card_id, …]
```

Indices are **generated** by:

```bash
python manage.py build_msu_index
```

Host never hardcodes the verb→card map in Python.

### 4.2 Norm card (two on-disk shapes)

**NKS-013 object source (preferred):**

```json
{
  "id": "N01",
  "title": "…",
  "source": {
    "act_id": "EUR_CHARTER_LGS_1985",
    "article": "3",
    "paragraph": "1",
    "text_quote": "…"
  },
  "source_confidence": "verified | approximate",
  "verbs": ["…"],
  "agents": ["…"],
  "depends_on": ["N01"],
  "status": "draft | active",
  "default_modality": "OBL"
}
```

**Legacy flat source (still present, e.g. N06/N07):**

```json
{
  "id": "N06",
  "title": "…",
  "source": "CONSTITUTION_MSU",
  "article": "140, 143",
  "verbs": ["…"],
  "depends_on": ["N01"],
  "status": "active"
}
```

### 4.3 Pipeline normalization

In `triplets.build_clause_triplets`, card IDs are expanded to **API-stable objects**:

```json
{
  "id": "N06",
  "title": "…",
  "source": "CONSTITUTION_MSU",
  "article": "140, 143",
  "status": "active",
  "depends_on": ["N01"]
}
```

Object-shaped `source` is flattened to `act_id` + article/paragraph string so the UI never receives `[object Object]`.

---

## 5. Host modules (`hostui/services/`)

| Module | Responsibility |
|--------|----------------|
| `registry.py` | Load `by_verb` / `by_agent` / `cards_db` into memory |
| `parser.py` | Normalize text, split clauses |
| `roles.py` | Agent form detection, nominative subject selection |
| `markup.py` | Main pipeline: spans, modality, OOV metrics, orchestration |
| `triplets.py` | Clause triplets; card expansion; OOV action labeling |
| `graph.py` | Nodes/edges for inspector graph (`depends_on`, subject hubs, soft edges) |
| `recommender.py` | Lightweight post-hints for UI |
| `exporter.py` | Annotated export helpers |
| `normos.py` | Thin façade: `analyze_document` → pipeline |
| `gemini.py` | Optional AI chat (separate from rule pipeline) |

**Invariant:** matching rules live in data (package + markers), not scattered in views.

---

## 6. Analysis products

### 6.1 Spans (document layers)

| layer | Meaning |
|-------|---------|
| `roles` | Subject / role forms |
| `verbs` | Matched actions from index |
| `modality` | OBL / PERM / PROH markers |
| `msu` | Card-linked spans (`card_id`) |

### 6.2 Triplets

```text
⟨ subject | null , modality , action ⟩
+ clause_text
+ cards[]          # expanded norm cards
+ depends_on[]     # aggregated from cards
+ incomplete / oov_* for non-registry actions
```

### 6.3 Graph

Built from triplets:

- action / subject nodes;
- procedural edges from `depends_on`;
- optional subject-hub and context edges (UI toggles).

### 6.4 Metrics & OOV

- exact vs root-style coverage signals;
- OOV forms/lemmas for registry growth (queue path exists).

---

## 7. Frontend contract (`workspace.html`)

- Single-page Workspace: input → analyze → annotated text + inspector + graph.
- Layer checkboxes filter **spans only**; pipeline still may compute full set depending on request `layers`.
- Inspector renders:
  - linguistic triplet S → [M] → A;
  - under it: card id, title, source line, status (draft highlighted), `depends_on`.
- Clicking a triplet scrolls/highlights the clause in the document.

UI language: operator-facing Ukrainian. Internal NKS terms are not required in labels.

---

## 8. Engineering invariants

1. **Package is the source of legal linkage** — Host maps text to cards; cards map to acts.
2. **Explainability** — every shown card is reachable from a matched verb/index hit (or explicitly empty).
3. **Schema tolerance** — support both card source shapes until full migration to NKS-013.
4. **No silent legal verdict** — outputs are analytical aids + disclaimers, not “lawful / unlawful”.
5. **Index rebuild is explicit** — after card edits: `build_msu_index`, then restart or reload registry.
6. **Feature branch → main** — experimental work lands on feature branches; demo baseline merges to `main` when stable.

---

## 9. Known limitations (honest)

- Verb index keys may be single lemmas **or** multi-word phrases; phrase keys match only if the same string appears in text under current `\b` scan.
- Perfective/imperfective mismatches (e.g. `затвердити` vs `затверджувати`) reduce hit rate until forms are aligned in cards/index.
- `status: draft` cards still match if indexed; Host may show them with a draft badge (filter policy is product decision).
- International sources (e.g. European Charter) may appear without a parallel national article — content quality issue, not pipeline bug.
- Full Event Bus / multi-tenant isolation from early HOST drafts is not required for the current single-operator demo path.

---

## 10. Extension points

| Need | Where |
|------|--------|
| New norm | add/edit `cards/*.json` → `build_msu_index` |
| Better coverage | expand verbs/forms in cards or align with operational verb registry |
| Stricter demo | filter `status != active` in pipeline or UI |
| Dual citation | extend card `source` / secondary sources in package |
| Lab alignment score | optional bridge to normos-lab metrics (not required in Host MVP) |

---

## 11. Related files

- `HOST.md` — deployment, operator model, non-goals  
- `CHECKLIST.md` — smoke / regression  
- `packages/msu_ua/package.json` — package manifest  
- Lab: NKS-011 (verbs), NKS-012 (modality), NKS-013 (cards)

---

*HM-ARCH-001 — architecture of the working Host ↔ msu_ua linkage after inspector card expansion.*
```

---

### `HOST.md`

```markdown
# NormOS Host

**Document ID:** HM-HOST-001  
**Status:** Working  
**Repo:** normos-host  
**Companion:** ARCHITECTURE.md (pipeline & package contract)

---

## 1. What Host is

NormOS Host is a **browser workplace** for primary analysis of local self-government normative texts (regulations, draft decisions, session materials).

Stack (current):

- Python 3.13 + Django
- SQLite for local/pilot state (upgrade path: Postgres)
- Rule-based analysis core in `hostui/services/`
- Package `packages/msu_ua` for norm cards and indices
- Optional Gemini-backed chat (not part of the deterministic analyzer)

Host is an **execution environment**: login surface, analyze API, Workspace UI, document helpers.  
It is **not** a public legal registry and **not** a substitute for a legal department.

---

## 2. Operator model

| Actor | Expectation |
|-------|-------------|
| Secretary / lawyer (gromada) | Paste or upload text → read structured hints → decide themselves |
| Host operator (team) | Deploy, accounts, package updates, index rebuild |
| Lab researcher | Evolves theory/registry in lab repo; feeds improved data into package |

**Human-in-the-loop:** system suggests; human remains accountable.

Disclaimer (must stay visible in product messaging):

> Automatic analysis only. Does not certify legality. Does not replace council or legal counsel decisions.

---

## 3. What Host provides

### 3.1 Workspace (`/workspace/`)

- Text input / file load
- Analyze button → layered annotation:
  - actions (verbs)
  - modality
  - roles
  - MSU norm spans
- **Inspector:** triplets ⟨S, M, A⟩ + linked norm cards (id, title, source, status, depends_on)
- Interactive dependency graph (procedural links, optional subject clusters)
- HTML export of annotated document

### 3.2 API

| Endpoint | Role |
|----------|------|
| `POST /api/analyze/` | Body: `{ "text", "layers" }` → full analysis JSON |
| OOV propose (if enabled) | Queue unknown lemmas for registry work |
| Chat routes | Optional assistant; separate from rule pipeline |

### 3.3 Package tooling

```bash
python manage.py build_msu_index
```

Rebuilds `packages/msu_ua/index/{by_verb,by_agent,by_source}.json` from cards.

---

## 4. Repository layout (Host-centric)

```
normos-host/
  host/                 # Django project settings, urls
  hostui/
    views.py            # pages + analyze API
    templates/          # workspace, chat, documents, auth
    services/           # analysis pipeline modules
    management/commands/build_msu_index.py
  packages/msu_ua/      # norm package (cards, sources, index)
  data/                 # host-local dictionaries / OOV queue
  ARCHITECTURE.md       # engineering architecture
  HOST.md               # this file
  CHECKLIST.md          # smoke tests
```

---

## 5. Deployment notes (pilot)

| Item | Practice |
|------|----------|
| Process | Django `runserver` or WSGI behind reverse proxy |
| Access | LAN / Tailscale / VPS URL + login |
| Secrets | `.env` / environment (`GEMINI_API_KEY` if chat used) — never commit |
| DB | `db.sqlite3` local; do not treat as source of truth in git |
| Code line | Stable demos on `main`; experiments on feature branches |

After pull of new cards or Host code:

1. install deps if needed  
2. `migrate` if models changed  
3. `build_msu_index` if cards changed  
4. restart process  
5. hard-refresh browser

---

## 6. Configuration boundaries

| In Host | In package | Out of scope for Host MVP |
|---------|------------|---------------------------|
| HTTP, sessions, templates | Card texts, verbs, depends_on | Full national law database |
| Pipeline orchestration | Index generation inputs | Automated “legal / illegal” verdict |
| UI layer toggles | source_confidence content quality | Self-service tenant signup |
| OOV queue file | Act citations | Training external LLMs on tenant docs |

---

## 7. Quality & safety posture

1. **Deterministic path first** — verb/modality/card linkage must work without LLM.  
2. **Traceable citations** — inspector shows card id + source line when a match exists.  
3. **Draft awareness** — draft cards may appear in analysis; treat as non-final until `status: active` and confidence reviewed.  
4. **OOV honesty** — unknown actions labeled; do not invent card links.  
5. **Sensitive domains** (martial law, finance) — prefer `source_confidence: approximate` until freshly verified.

---

## 8. Relationship to lab NormOS

| Lab | Host |
|-----|------|
| Theory, NKS, verb alphabet experiments | Production-shaped workplace |
| Golden tests / alignment research | Operator UX + package execution |
| May use richer event model | Current demo path is request/response pipeline |

Host should stay a **thin execution shell** over package + services. Heavy research stays in lab until promoted into package data or Host modules deliberately.

---

## 9. Non-goals (current)

- Official publication of acts  
- Automatic compliance certificate  
- Replacing national legal information systems  
- Requiring every gromada to self-host infrastructure  
- Treating chat answers as formal legal opinions  

---

## 10. Operational checklist (short)

- [ ] `main` deployed / process restarted  
- [ ] `packages/msu_ua/index/` present and non-empty  
- [ ] Analyze sample text with known verbs (`затверджувати`, `приймати`, …)  
- [ ] Inspector shows card block (not only S–M–A)  
- [ ] Source line is human-readable (no `[object Object]`)  
- [ ] Graph opens; depends_on visible where data exists  
- [ ] Disclaimer still understood by operators  

See also `CHECKLIST.md`.

---

## 11. Document map

| File | Audience |
|------|----------|
| **ARCHITECTURE.md** | Engineers: pipeline, package contract, modules |
| **HOST.md** | Engineers/operators: role of Host, deploy, boundaries |
| **README.md** | (later) End-user oriented overview |

---

*HM-HOST-001 — Host as execution workplace for msu_ua-backed normative analysis.*
```

---

Кратко:

- **ARCHITECTURE.md** — связка Host ↔ `msu_ua`, поток данных, модули, нормализация карточек, инварианты.  
- **HOST.md** — зачем Host, оператор, деплой, границы, non-goals.

`README.md` можно позже сделать короче и «для секретаря/юриста», со ссылкой на эти два файла.
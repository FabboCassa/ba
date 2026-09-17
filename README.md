# ba — plugin Claude Code

Meno token, meno chiacchiere, codice verificato. Flusso: **idea → domande → spec → issue GitHub → branch/test reale/build/PR per ogni issue**.

## Installazione
```bash
# 1. pubblica questa cartella come repo GitHub (vedi "Pubblicare questo plugin")
# 2. in Claude Code:
/plugin marketplace add <tuo-utente>/ba
/plugin install ba@ba
# test locale senza pubblicare:
claude --plugin-dir /percorso/ba
```
Requisiti: `git`, `gh` autenticato (`gh auth login`), `bash` (su Windows: Git Bash, incluso in Git for Windows), `node` solo per progetti JS.

## Comandi
| Comando | Cosa fa |
|---|---|
| `/ba:spec <idea>` | Ti intervista (risposta consigliata sempre per prima) finché non c'è nulla di aperto. Scrive `docs/specs/<slug>.md`. |
| `/ba:issues docs/specs/x.md` | Spezza la spec in issue piccole con dipendenze e criteri di accettazione testabili. Crea le issue con `gh`. |
| `/ba:implement <n>` | Branch `feat/<n>-slug` → test prima → codice → **prova red→green** → build+lint+test → review → commit `Closes #n` → PR. Max 3 tentativi; ogni fallimento: causa scritta in `.ba/runs/<n>.md` e commento sull'issue. Dopo 3: label `blocked`. |
| `/ba:auto [spec.md] [merge] [max=N]` | **Autonomo**: fa tutte le issue aperte (o crea le issue dalla spec approvata) senza chiedere nulla finché non ha finito. Uno scrive (`implementer`), altri due controllano (`verifier`, `reviewer`) senza vedere il ragionamento di chi scrive. Issue fallite 3 volte → `blocked` e passa alla successiva. Riprende da dove era rimasto (`.ba/auto.json`). |
| `/ba:ship [n...] [merge]` | Esegue `implement` su tutte le issue in ordine di dipendenza (PR impilate se serve). Non fa merge se non lo chiedi. |

## Esempio completo, passo passo

Scenario: API Node/TypeScript per una todo list; il repo esiste già su GitHub (`fabio/todo-api`).

### 0. Preparazione (una volta sola)
```bash
gh auth login                      # login a GitHub
cd todo-api && claude              # apri Claude Code nel repo
/plugin marketplace add fabio/ba   # oppure: claude --plugin-dir ../ba
/plugin install ba@ba
```
All'avvio della sessione il plugin carica le regole di sintesi: da qui in poi niente preamboli, niente riepiloghi lunghi, commenti solo sul perché.

### 1. `/ba:spec` — dall'idea alla spec
```
/ba:spec voglio aggiungere le todo con scadenza e un endpoint che restituisce quelle scadute
```
Cosa succede:
1. Claude legge da solo il repo (remote, README, comandi di build/test rilevati) e non ti chiede cose che può scoprire.
2. Ti fa domande a gruppi di max 4, con la risposta consigliata per prima. Esempio:
   ```
   Formato della scadenza?
     › ISO 8601 con timezone (Consigliato)
       Solo data (YYYY-MM-DD)
   Una todo senza scadenza è valida?
     › Sì, campo opzionale (Consigliato)
       No, obbligatorio
   Dove vive "scaduta"?
     › GET /todos/overdue (Consigliato)
       GET /todos?overdue=true
   ```
3. Continua a fare round finché ogni requisito ha un criterio di accettazione verificabile.
4. Scrive `docs/specs/todo-due-dates.md` e ti mostra 5 righe di riepilogo: `Approvi? (sì / modifiche)`.

Rispondi `sì` → la spec passa a `Status: approved`.

### 2. `/ba:issues` — dalla spec alle issue GitHub
```
/ba:issues docs/specs/todo-due-dates.md
```
Claude propone la scomposizione e aspetta il tuo OK:
```
| # | Titolo                                   | Dipende da | Req    |
|---|------------------------------------------|------------|--------|
| 1 | Add dueDate field + validation           | -          | R1, R2 |
| 2 | Persist dueDate in repository            | 1          | R1     |
| 3 | GET /todos/overdue endpoint              | 2          | R3     |
```
Dopo l'OK:
- crea le label `ba` e `blocked`;
- crea le issue `#14 #15 #16`, ognuna con criteri di accettazione come checklist e dipendenze;
- scrive `.ba/plan.json`, aggiorna la tabella nella spec, fa commit `docs: spec + plan for todo-due-dates`.

### 3a. `/ba:implement` — una issue alla volta
```
/ba:implement 14
```
Cosa succede, in ordine:
| Passo | Chi | Cosa |
|---|---|---|
| Preflight | skill | issue aperta? dipendenze chiuse? working tree pulito? crea `feat/14-add-duedate-field` da `origin/main`, lancia `gate.sh`: se la base è già rotta si ferma |
| Test prima | agente `implementer` | scrive `src/todo.test.ts` (un test per ogni criterio), verifica che fallisca |
| Codice | agente `implementer` | implementazione minima, poi build + lint + tutti i test |
| Prova | agente `verifier` | `prove-test.sh`: senza implementazione il test **deve fallire**, con implementazione **deve passare**; poi `gate.sh`; poi controlla che ogni criterio abbia un'asserzione e che nessun test sia saltato |
| Review | agente `reviewer` | solo problemi bloccanti: bug, sicurezza, modifiche fuori scope, commenti inutili |
| Ship | skill | commit `feat(todo): add dueDate field and validation` + `Closes #14`, push, PR |

Output finale (3 righe):
```
PR: https://github.com/fabio/todo-api/pull/21
Tests: src/todo.test.ts (4)
Attempts: 2
```

**Se un tentativo fallisce**, in `.ba/runs/14.md` e come commento sull'issue trovi:
```
## Attempt 1 - FAIL
Why: il test "rejects past dates" passa anche senza implementazione:
     confronta con new Date() senza fissare il clock, quindi è sempre vero.
Evidence: FAKE TEST: tests pass WITHOUT the implementation. Reverted files: src/todo.ts
Next: fissare il tempo con vi.useFakeTimers() e asserire l'errore di validazione.
```
Il tentativo 2 riparte da queste note. Dopo 3 fallimenti l'issue prende la label `blocked` e Claude ti riporta i 3 motivi.

### 3b. `/ba:ship` — tutte le issue
```
/ba:ship              # tutte le issue aperte del piano, in ordine di dipendenza
/ba:ship 15 16        # solo alcune
/ba:ship merge        # e fa anche il merge delle PR verdi
```
Se #15 dipende da #14 e la PR di #14 non è ancora mergiata, #15 parte dal branch di #14 (PR impilata). Risultato finale:
```
#14 | PR #21 | ✓
#15 | PR #22 | ✓ (stacked on #21)
#16 | -      | blocked: DB schema migration missing, see .ba/runs/16.md
```

### 3c. `/ba:auto` — modalità autonoma
Claude non ti chiede nulla, ma Claude Code chiede comunque i **permessi** per i comandi. Per farlo andare da solo scegli una di queste:

**A. Modalità auto** (un classificatore approva le azioni sicure e blocca quelle rischiose):
```powershell
cd E:\Progetti\MioProgetto
claude --permission-mode auto "/ba:auto merge"
```

**B. Allowlist + nessuna domanda** (più controllo): copia `templates/settings.auto.json` del plugin in `.claude/settings.local.json` del progetto, poi:
```powershell
claude --permission-mode dontAsk "/ba:auto merge"
```
Quello che non è in allowlist viene rifiutato senza chiedere (force push, reset --hard, `.env` sono sempre negati).

**C. Senza interfaccia** (lo lanci e te ne vai; l'output finale va nel file):
```powershell
claude -p "/ba:auto merge" --permission-mode auto > ba-auto.log
```

Varianti:
```
/ba:auto                                   # tutte le issue aperte, PR impilate, nessun merge
/ba:auto merge                             # fa merge (squash) di ogni PR verde prima di passare alla successiva
/ba:auto docs/specs/classifica.md merge    # crea le issue dalla spec approvata e le fa tutte
/ba:auto max=3                             # solo le prime 3
```
**Non si ferma a metà**: un hook `Stop` (stessa idea del plugin ufficiale Anthropic *ralph-loop*) impedisce a Claude di chiudere il turno finché esiste `.ba/auto.lock`. Valvola di sicurezza: max 40 ripartenze (`BA_AUTO_MAX_CONTINUES`). Per fermarlo tu: `Esc`/`Ctrl+C` e cancella `.ba/auto.lock`.

Durante il lavoro: decisioni prese al posto tuo in `.ba/auto.md`, stato in `.ba/auto.json`, motivi dei fallimenti in `.ba/runs/<n>.md` e come commento sull'issue. Se lo interrompi, rilancia lo stesso comando: salta le issue già fatte.

Report finale:
```
ba:auto — 4/5 done, 1 blocked, 0 skipped
#14 | PR #21 | ✓ 1 att
#15 | PR #22 | ✓ 3 att
#16 | -      | blocked: migrazione DB mancante (.ba/runs/16.md)
Decisions: 2 logged in .ba/auto.md
```

### Comandi di build/test personalizzati
Se il rilevamento automatico non basta, crea `.ba/commands.env` nel repo:
```
BUILD=pnpm -r build
TEST=pnpm vitest run
LINT=pnpm eslint .
```

### File che il flusso crea nel tuo repo
```
docs/specs/<slug>.md   spec approvata + tabella issue
.ba/plan.json          issue e dipendenze
.ba/runs/<n>.md        motivi dei tentativi falliti
.ba/auto.json|auto.md  stato e decisioni di /ba:auto
.ba/logs/              log build/test (in .gitignore)
```

## Pubblicare questo plugin su GitHub
```bash
cd ba
git init && git add -A && git commit -m "feat: ba plugin"
gh repo create ba --public --source . --push
# poi, in qualsiasi progetto:
/plugin marketplace add <tuo-utente>/ba
/plugin install ba@ba
```

## Cosa rende i test "veri"
`scripts/prove-test.sh` ripristina i file di implementazione a HEAD e lancia i nuovi test: **devono fallire**. Poi rimette l'implementazione: **devono passare**. Un test che passa senza codice = `FAKE TEST` → tentativo fallito. Il `verifier` (agente separato, non può modificare codice) controlla anche che ogni criterio di accettazione abbia un'asserzione e che nessun test sia stato skippato.

## Build sempre
`scripts/gate.sh` rileva build/lint/test (npm/pnpm/yarn/bun, dotnet, cargo, go, gradle, maven, python, make) e stampa solo le ultime 40 righe degli errori. Override: `.ba/commands.env`
```
BUILD=dotnet build -v q
TEST=dotnet test -v q
LINT=
```

## Risparmio token
- Hook `SessionStart` inietta `templates/terse-rules.md` (~350 token): niente preamboli/riepiloghi, commenti solo sul *perché*, letture mirate, log troncati.
- Implementer/verifier/reviewer girano come subagenti (`sonnet`): il contesto principale tiene solo i risultati (3 righe per issue).
- Script bash deterministici per detect/gate/prova test: zero token LLM.

Nota onesta (dai benchmark di claude-token-efficient e caveman): le regole di stile tagliano l'**output**, non input né ragionamento. Il guadagno reale viene soprattutto da subagenti + log troncati.

## Struttura
```
.claude-plugin/{plugin,marketplace}.json
skills/{spec,issues,implement,ship,auto,terse}/SKILL.md
agents/{implementer,verifier,reviewer}.md
scripts/{detect,gate,prove-test,auto-guard}.sh
hooks/hooks.json   templates/{terse-rules,spec,settings.auto.json}
```

## Ispirazione (repo verificate, nessun codice copiato)
| Repo | ★ | Licenza | Idea presa |
|---|---|---|---|
| obra/superpowers | ~287k | MIT | brainstorming → plan → TDD → verification-before-completion |
| mattpocock/skills | ~264k | MIT | grill-me / to-spec / to-tickets / tdd |
| anthropics/skills | ~169k | Apache-2.0 | formato SKILL.md ufficiale |
| github/spec-kit | ~134k | MIT | specify → plan → tasks → implement |
| JuliusBrussee/caveman | ~103k | MIT (skill) / BSL (proxy) | output compresso |
| gsd-build/get-shit-done | ~65k | MIT (archiviato → open-gsd) | commit atomici per task |
| wshobson/agents | ~40k | MIT | subagenti specializzati |
| anthropics/claude-plugins-official | ~36k | Apache-2.0 | struttura plugin, commit-commands |
| automazeio/ccpm | ~8k | MIT | PRD → epic → GitHub Issues, script deterministici |
| drona23/claude-token-efficient | ~6k | MIT | CLAUDE.md terse, benchmark onesti |

### Modalità autonoma: progetti simili valutati
| Repo | ★ | Nota |
|---|---|---|
| anthropics/claude-plugins-official → `ralph-loop` | ufficiale | Hook Stop che ripete il prompt finché non è finito. Idea ripresa in `auto-guard.sh`. |
| obra/superpowers → `subagent-driven-development` | ~287k | Agente nuovo per ogni task + review in due fasi. Idea ripresa (writer ≠ checker). |
| AnandChowdhary/continuous-claude | ~1.4k | Loop PR → CI → merge con file di memoria condiviso. Idea ripresa (`.ba/auto.md`). |
| fabioneves/autoloop | 0 | Ben progettato (reviewer read-only, merge umano di default) ma nessuna adozione: non installare, solo spunto. |
| MHutatah/agent-loop, troykelly/claude-skills | 0-11 | Troppo giovani/poco usati. Evitare. |

Evitare: fork/cloni con stesso nome e poche stelle (es. `Stars1233/agents`, `ashanuoc/get-shit-done`), marketplace di skill non curati (Snyk "ToxicSkills": payload malevoli in skill pubblicate). Leggi sempre `hooks` e `scripts` prima di installare un plugin.

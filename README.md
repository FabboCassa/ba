# ba — plugin Claude Code

Meno token, meno chiacchiere, codice verificato. Flusso: **idea → domande → spec → issue GitHub → branch/test reale/build/PR per ogni issue**. In più due audit, **ottimizzazione** e **sicurezza**, che trasformano i problemi trovati in issue e passano dallo stesso flusso.

## Installazione
```bash
# 1. pubblica questa cartella come repo GitHub (vedi "Pubblicare questo plugin")
# 2. in Claude Code:
/plugin marketplace add <tuo-utente>/ba
/plugin install ba@ba
# test locale senza pubblicare:
claude --plugin-dir /percorso/ba
```
Requisiti: `git`, `gh` autenticato (`gh auth login`), `bash` (su Windows: Git Bash, incluso in Git for Windows), `node` solo per progetti JS, `python3` per `/ba:optimize` (lettura dei report dei test).
Consigliati per `/ba:secure` (se mancano il comando lo dice e segna "non controllato"): `gitleaks`, `osv-scanner`, `semgrep`, `jq`.

## Comandi
| Comando | Cosa fa |
|---|---|
| `/ba:spec <idea>` | Ti intervista (risposta consigliata sempre per prima) finché non c'è nulla di aperto. Scrive `docs/specs/<slug>.md`. |
| `/ba:issues <spec o audit>` | Spezza la spec (o un audit approvato) in issue piccole con dipendenze, criteri di accettazione testabili e **Kind** (come verrà provata). Crea le issue con `gh`. |
| `/ba:implement <n>` | Branch → test prima → codice → **prova** (red→green, oppure nessuna regressione per refactor/perf, oppure scanner pulito per dipendenze/segreti) → build+lint+test → review → commit `Closes #n` → PR. Max 3 tentativi; ogni fallimento: causa scritta in `.ba/runs/<n>.md` e commento sull'issue. Dopo 3: label `blocked`. |
| `/ba:auto [spec.md] [merge] [max=N]` | **Autonomo**: fa tutte le issue aperte (o crea le issue dalla spec approvata) senza chiedere nulla finché non ha finito. Uno scrive (`implementer`), altri due controllano (`verifier`, `reviewer`) senza vedere il ragionamento di chi scrive. Issue fallite 3 volte → `blocked` e passa alla successiva. Riprende da dove era rimasto (`.ba/auto.json`). |
| `/ba:ship [n...] [merge]` | Esegue `implement` su tutte le issue in ordine di dipendenza (PR impilate se serve). Non fa merge se non lo chiedi. |
| `/ba:optimize [tests\|arch\|code\|perf] [slow=60] [auto]` | **Audit ottimizzazione**: test troppo lunghi (con proposta di spezzettamento), architettura (la intuisce e te la fa confermare), codice inutile/duplicato, performance. Report → scegli cosa correggere → issue → `ship`/`auto`. |
| `/ba:secure [secrets\|code\|deps\|platform] [web=yes\|no] [auto]` | **Audit sicurezza**: segreti in chiaro (anche nella storia git e in quello che pubblichi), vulnerabilità nel codice, librerie con criticità note, requisiti ufficiali della piattaforma (web, Android, iOS…) cercati online solo su siti ufficiali. Report → scegli → issue → `ship`/`auto`. |

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
| # | Titolo                                   | Kind    | Dipende da | Req    |
|---|------------------------------------------|---------|------------|--------|
| 1 | Add dueDate field + validation           | feature | -          | R1, R2 |
| 2 | Persist dueDate in repository            | feature | 1          | R1     |
| 3 | GET /todos/overdue endpoint              | feature | 2          | R3     |
```
Dopo l'OK:
- crea le label `ba`, `blocked`, `needs-human`, `optimize`, `security`;
- crea le issue `#14 #15 #16`, ognuna con criteri di accettazione come checklist e dipendenze;
- scrive `.ba/plan.json`, aggiorna la tabella nella spec, fa commit `docs: plan for todo-due-dates`.

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

**Parallelo e worktree (dalla 0.4.0)**: ogni issue lavora in una copia separata del repo creata con `git worktree` in `../<repo>-ba/<n>`, fuori dalla cartella di lavoro. Visual Studio e il tuo index non vengono mai toccati, e le issue **indipendenti** (deps già fatte) partono insieme, 3 alla volta. Il merge resta uno alla volta, in ordine: se una PR non entra più pulita, la sua copia viene ribasata e ricontrollata. Le copie vengono rimosse dopo il merge; restano solo quelle delle issue bloccate. Le issue che misurano tempi (`perf`, `test-split`) girano sempre da sole, per non falsare le misure.

Varianti:
```
/ba:auto                                   # tutte le issue aperte, PR impilate, nessun merge
/ba:auto merge                             # fa merge (squash) di ogni PR verde prima di passare alla successiva
/ba:auto docs/specs/classifica.md merge    # crea le issue dalla spec approvata e le fa tutte
/ba:auto max=3                             # solo le prime 3
/ba:auto par=1                             # una issue alla volta (default: par=3, max 4)
/ba:auto no-worktree                       # lavora nella cartella corrente, sequenziale
```
**Non si ferma a metà**: un hook `Stop` (stessa idea del plugin ufficiale Anthropic *ralph-loop*) impedisce a Claude di chiudere il turno finché esiste `.ba/auto.lock`. Valvola di sicurezza: max 40 ripartenze (`BA_AUTO_MAX_CONTINUES`). Per fermarlo tu: `Esc`/`Ctrl+C` e cancella `.ba/auto.lock`.

**Se finisce il contesto o si interrompe**: Claude Code compatta la conversazione e continua; `/ba:auto` non si fida della memoria ma di `.ba/auto.json`, aggiornato a ogni passo (branch, tentativo, check, PR, merge). Dopo una compattazione l'hook gli fa rileggere istruzioni + stato. Se la sessione muore (crash, Ctrl+C, PC spento) rilancia lo stesso comando: l'issue a metà riparte dal suo branch, prima ricontrolla quello che c'è già e poi continua dal tentativo successivo, senza aprire PR doppie. Al massimo si perde il passo in corso.

Durante il lavoro: decisioni prese al posto tuo in `.ba/auto.md`, stato in `.ba/auto.json`, motivi dei fallimenti in `.ba/runs/<n>.md` e come commento sull'issue. Se lo interrompi, rilancia lo stesso comando: salta le issue già fatte. Le issue `needs-human` (es. ruotare una password) non le tocca: te le elenca alla fine.

Report finale:
```
ba:auto — 4/5 done, 1 blocked, 0 skipped
#14 | PR #21 | ✓ 1 att
#15 | PR #22 | ✓ 3 att
#16 | -      | blocked: migrazione DB mancante (.ba/runs/16.md)
Needs you: #17 ruota la password del DB
Decisions: 2 logged in .ba/auto.md
```

### 4. `/ba:optimize` — ottimizzazione (dalla 0.7.0)
```
/ba:optimize                 # tutto: test, architettura, codice, performance
/ba:optimize tests slow=120  # solo i test, lento = più di 2 minuti
/ba:optimize auto            # niente domande: crea le issue (impatto ≥ medio) e lancia /ba:auto
```
Cosa controlla:
| Area | Come | Proposte tipiche |
|---|---|---|
| **Test lenti** | `test-times.sh` legge i report (JUnit, `.trx`, go json, jest) già presenti o quelli dell'ultima CI (`gh run download`); se non ci sono lancia la suite una volta con i report attivi (se sembra lunga te lo chiede prima). Soglie: test > `slow` s, file/classe > 5×`slow`. | un test che fa 40 scenari → 40 test; DB ricreato a ogni test → fixture condivisa; `sleep` → clock finto; casi pesanti → livello `slow` che gira di notte in CI (niente viene perso) |
| **Architettura** | la intuisce da cartelle, progetti e dipendenze (Clean, Layered/MVC, MVVM, Hexagonal, vertical slice…) e **te la fa confermare** (una volta: poi è scritta in `docs/architecture.md`) | prima un **test di architettura** (NetArchTest, dependency-cruiser, ArchUnit, import-linter…) che fallisce sulle violazioni attuali, poi le correzioni |
| **Codice inutile** | knip, vulture, analizzatori .NET, staticcheck, jscpd… + verifica a mano (DI/reflection non sono "codice morto") | rimozione codice/dipendenze non usate, duplicati, semplificazioni |
| **Performance** | N+1, query in loop, I/O sincrono, O(n²), paginazione mancante, bundle pesanti | se non misurato: prima una issue che aggiunge il benchmark, poi l'ottimizzazione con obiettivo (`Target: 30%`) |

Report in `docs/audits/optimize-<data>.md`, ti mostra solo la tabella:
```
| ID | Area  | Impatto | Kind       | Problema (prova)                                   | Proposta |
| O1 | tests | alto    | test-split | OrdersIT.FullFlow 3412s: 40 scenari, DB rifatto    | 1 test/scenario, fixture DB, 3 casi in slow |
| O2 | arch  | medio   | refactor   | Api/OrdersController.cs:88 usa DbContext diretto   | passare da IOrderService |
Quali trasformo in issue? (tutte / O1 O3 … / nessuna)
```
Come si prova una issue di ottimizzazione (non c'è nuovo comportamento, quindi niente red→green): `prove-refactor.sh` lancia la suite sulla base e sul branch e fallisce se un test è sparito, se qualcosa è rosso, se (per `test-split`) il test più lento supera ancora la soglia o il totale peggiora, se (per `perf`) il benchmark non migliora almeno del `Target` (mediana di 3 esecuzioni).

### 5. `/ba:secure` — sicurezza (dalla 0.7.0)
```
/ba:secure              # tutto
/ba:secure secrets      # solo segreti
/ba:secure web=yes      # dai il permesso alle ricerche online (viene ricordato in .ba/config.json)
/ba:secure auto         # niente domande: issue per critical/high/medium e /ba:auto
```
Cosa controlla:
| Area | Come |
|---|---|
| **Segreti** | gitleaks su file **e tutta la storia git**; file che non dovrebbero essere tracciati (`.env`, `.pem`, `.jks`, `.pfx`, `local.settings.json`…); `.gitignore`/`.dockerignore`/`.npmignore`; chiavi finite nel front-end o nell'app mobile (che sono pubbliche); contenuto reale di quello che pubblichi (`npm pack --dry-run`, `dotnet pack`…); workflow GitHub che espongono segreti. I valori non vengono **mai** stampati: `****a9f2`. |
| **Codice** | semgrep, bandit, gosec, analizzatori di sicurezza .NET, alert GitHub; poi un agente legge i punti di ingresso secondo OWASP Top 10 (web/API) e MASVS (mobile). |
| **Librerie** | osv-scanner + `npm audit`/`pip-audit`/`dotnet list package --vulnerable`/`govulncheck`/`cargo audit` + alert Dependabot; controlla se la funzione vulnerabile è davvero usata; con ricerca online anche CISA KEV (sfruttate attivamente → critiche) e fine supporto del runtime. |
| **Piattaforma** | rileva il target (web, Android, iOS, MAUI/Flutter/RN, estensione browser, pacchetto npm/NuGet/PyPI, container) e te lo conferma. Con il tuo permesso cerca i requisiti **attuali** solo su siti ufficiali (developer.android.com, Google Play Console Help, developer.apple.com, learn.microsoft.com, owasp.org, nvd.nist.gov, cisa.gov, osv.dev, GitHub Advisories, sito ufficiale di ogni framework). Salva requisito + URL + data in `.ba/security/requirements-<piattaforma>.md` e lo riusa per 30 giorni, poi aggiorna da solo. |

Il report sta in `.ba/security/` (mai committato). Se il repo è **pubblico**, le issue hanno titoli neutri e i dettagli restano solo in locale (o in una Security Advisory privata di GitHub). Se trova un segreto vero ti mostra subito un blocco **AZIONE URGENTE**: la chiave va ruotata sul provider (issue `needs-human`), poi il codice viene sistemato con una issue normale. La storia git non viene mai riscritta senza il tuo "sì" esplicito.

Come si prova una fix di sicurezza:
| Kind | Prova |
|---|---|
| `security` | un test che **fa l'attacco** (input malevolo, richiesta non autorizzata, path traversal): rosso prima, verde dopo |
| `dep-upgrade` | `sec-scan.sh deps --id GHSA-…` non la riporta più + build/test verdi |
| `secret` | scansione pulita, file ignorato, il valore arriva da env/secret store (test) |
| `config` | un test o comando che controlla l'impostazione (header, manifest…) e fallisce sulla base |

**Protezioni sempre attive** (dalla 0.7.0)
- **Hook `secret-guard`**: prima di ogni `git commit`, `git push`, `npm publish`, `dotnet nuget push`, `twine upload`, `cargo publish`, `docker push`, `gh release create`, `fastlane`… fatto da Claude, scansiona quello che sta per uscire. Se trova segreti o file sensibili **blocca** e spiega cosa fare. Falso positivo → `.gitleaksignore` o una regex di percorso in `.ba/secret-allow`.
- **Anche per i tuoi commit**: `/ba:secure` propone di installare lo stesso controllo come hook git `pre-commit`/`pre-push` (`bash scripts/secret-guard.sh --install-git-hooks`; gli hook già presenti vengono mantenuti in catena).
- **Scansione settimanale**: `templates/security.yml` → `.github/workflows/ba-security.yml` (proposto come issue, passa da PR). Gitleaks + osv-scanner ogni lunedì e a ogni push su main; se trova qualcosa apre (o aggiorna) una sola issue `security`. Zero token.

### Comandi di build/test personalizzati
Se il rilevamento automatico non basta, crea `.ba/commands.env` nel repo:
```
BUILD=pnpm -r build
TEST=pnpm vitest run
LINT=pnpm eslint .
```

### File che il flusso crea nel tuo repo
```
docs/specs/<slug>.md          spec approvata + tabella issue
docs/architecture.md          architettura confermata + regole (da /ba:optimize)
docs/audits/optimize-*.md     audit di ottimizzazione
.ba/plan.json                 issue, dipendenze, kind
.ba/runs/<n>.md               motivi dei tentativi falliti
.ba/auto.json|auto.md         stato e decisioni di /ba:auto
.ba/config.json               piattaforme e permesso ricerche online
.ba/security/                 report sicurezza, requisiti e fonti (in .gitignore, mai committato)
.ba/logs/  .ba/cache/         log, report test, tempi della base (in .gitignore)
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
Per i cambi senza nuovo comportamento `scripts/prove-refactor.sh` confronta la suite sulla base (in una copia temporanea fuori dal repo, risultato messo in cache per commit) con quella del branch: nessun test perso, tutto verde, e l'obiettivo del Kind raggiunto.

## Build sempre
`scripts/gate.sh` rileva build/lint/test (npm/pnpm/yarn/bun, dotnet, cargo, go, gradle, maven, python, make) e stampa solo le ultime 40 righe degli errori. Override: `.ba/commands.env`
```
BUILD=dotnet build -v q
TEST=dotnet test -v q
LINT=
```

## Risparmio token
- Hook `SessionStart` inietta `templates/terse-rules.md` (~350 token): niente preamboli/riepiloghi, commenti solo sul *perché*, letture mirate, log troncati.
- Implementer/verifier/reviewer/auditor girano come subagenti (`sonnet`): il contesto principale tiene solo i risultati (3 righe per issue, una tabella per audit).
- Script bash deterministici per detect/gate/prova test/tempi test/scanner/segreti: zero token LLM.

Nota onesta (dai benchmark di claude-token-efficient e caveman): le regole di stile tagliano l'**output**, non input né ragionamento. Il guadagno reale viene soprattutto da subagenti + log troncati.

## Struttura
```
.claude-plugin/{plugin,marketplace}.json
skills/{spec,issues,implement,ship,auto,optimize,secure,terse}/SKILL.md
agents/{implementer,verifier,reviewer,auditor}.md
scripts/{detect,gate,prove-test,prove-refactor,test-times,sec-scan,secret-guard,auto-guard}.sh
hooks/hooks.json   templates/{terse-rules,spec,architecture,settings.auto.json,security.yml}
```
Hook da aggiungere in `hooks/hooks.json` (accanto a `SessionStart` e `Stop` già presenti):
```json
"PreToolUse": [
  { "matcher": "Bash",
    "hooks": [ { "type": "command", "command": "bash \"${CLAUDE_PLUGIN_ROOT}/scripts/secret-guard.sh\"", "timeout": 60 } ] }
]
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

Strumenti esterni usati da `optimize`/`secure` (se installati, nessuno è obbligatorio): gitleaks, osv-scanner, semgrep, bandit, gosec, govulncheck, cargo-audit, pip-audit, knip, jscpd, vulture, staticcheck, dependency-cruiser, NetArchTest/ArchUnit/import-linter.

### Modalità autonoma: progetti simili valutati
| Repo | ★ | Nota |
|---|---|---|
| anthropics/claude-plugins-official → `ralph-loop` | ufficiale | Hook Stop che ripete il prompt finché non è finito. Idea ripresa in `auto-guard.sh`. |
| obra/superpowers → `subagent-driven-development` | ~287k | Agente nuovo per ogni task + review in due fasi. Idea ripresa (writer ≠ checker). |
| AnandChowdhary/continuous-claude | ~1.4k | Loop PR → CI → merge con file di memoria condiviso. Idea ripresa (`.ba/auto.md`). |
| fabioneves/autoloop | 0 | Ben progettato (reviewer read-only, merge umano di default) ma nessuna adozione: non installare, solo spunto. |
| MHutatah/agent-loop, troykelly/claude-skills | 0-11 | Troppo giovani/poco usati. Evitare. |

Evitare: fork/cloni con stesso nome e poche stelle (es. `Stars1233/agents`, `ashanuoc/get-shit-done`), marketplace di skill non curati (Snyk "ToxicSkills": payload malevoli in skill pubblicate). Leggi sempre `hooks` e `scripts` prima di installare un plugin.

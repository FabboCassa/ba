# Issue #1: Universal Multi-AI Architecture (Gemini, DeepSeek, Qwen, OpenAI, Claude)

GitHub Issue: https://github.com/FabboCassa/ba/issues/1  
Source: `README.md`  
Refs: `ARCH-UNIVERSAL-01`  
Kind: `feature`  
Status: `open`  

## Contesto & Motivazione
Attualmente, `ba` è confezionato esclusivamente come plugin proprietario per Claude Code:
- Cartella `.claude-plugin/` con schema Claude
- Hook `SessionStart`, `Stop`, `PreToolUse` in `hooks/hooks.json` dipendenti da variabili Claude (`${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_SESSION_ID}`)
- YAML frontmatter in `agents/*.md` con modello fisso `sonnet` e set di tool proprietario
- `skills/*/SKILL.md` con percorsi `${CLAUDE_SKILL_DIR}` e comandi specifici Claude (`AskUserQuestion`, `Agent ba:...`)
- Script deterministici che si appoggiano a variabili di sessione Claude

Tuttavia, il vero valore di `ba` (il flusso TDD rigoroso con separazione Scrittore/Controllore, il test reale RED->GREEN con `prove-test.sh`, il gate deterministico con `gate.sh`, gli audit di ottimizzazione e sicurezza a token zero) è intrinsecamente indipendente dal modello LLM sottostante.

Questa issue definisce e traccia l'apertura e la standardizzazione di `ba` per **tutti i modelli e gli agenti AI**:
- **Gemini & Google Antigravity** (Gemini 1.5/2.0 Pro/Flash, Antigravity Customizations, `.gemini/rules/`, `GEMINI.md`)
- **DeepSeek & Qwen** (DeepSeek-V3, DeepSeek-R1, Qwen-2.5-Coder 32B/70B via Roo Code, Cline, Continue.dev, OpenCode, Aider)
- **OpenAI & GitHub Copilot** (GPT-4o, o1, o3-mini, Codex, Cursor `.cursorrules`, Windsurf `.windsurfrules`, `.github/copilot-instructions.md`)
- **Claude Code** (mantenuto al 100% come plugin nativo di prima classe)

---

## Architettura Multi-Tier Proposta

### Tier 1: Core Engine & CLI Portabile (`bin/ba` o `scripts/ba.sh`)
- Una CLI portabile invocabile da qualsiasi terminale (Bash, Git Bash su Windows, Zsh, PowerShell).
- Comandi chiari:
  - `ba detect [dir]`
  - `ba gate [dir] [--only build|test|lint]`
  - `ba prove-test <test-cmd> <test-files...>`
  - `ba prove-refactor <base-ref> <kind> [--slow N] [--bench CMD --target PCT]`
  - `ba scan secrets|code|deps`
  - `ba test-times [--run] [--slow N]`
  - `ba init <platform>` (genera le configurazioni per la piattaforma scelta)

### Tier 2: Model Context Protocol (MCP) Server (`ba-mcp`)
- Server MCP standard (conforme alle specifiche Model Context Protocol supportate da Claude Desktop/Code, Google Antigravity, Cursor, Windsurf, Roo Code, Cline).
- Espone come tool MCP deterministici:
  - `ba_detect`: rileva lo stack del progetto
  - `ba_gate`: esegue build/lint/test compatto
  - `ba_prove_test`: esegue la prova red->green
  - `ba_prove_refactor`: esegue la prova di non-regressione
  - `ba_security_scan`: esegue scansione segreti/vulnerabilità/dipendenze
  - `ba_test_times`: analizza i report dei tempi di esecuzione test

### Tier 3: Standard `AGENTS.md` & Specifiche Skill Universali
- File radice `AGENTS.md` aderente agli standard di Agentic Coding della Linux Foundation / OpenAI / Anthropic / Google.
- Qualsiasi assistente AI che legge la cartella comprende immediatamente:
  - Regole di sintesi e risparmio token (Terse rules)
  - Separazione dei ruoli (Scrittore `implementer` vs Controllori `verifier` e `reviewer`)
  - Vincolo di verifica reale con test RED->GREEN prima di considerare un task completato.
- Skills standardizzate compatibili con il formato Agent Skills (agentskills.org) e Google Antigravity.

### Tier 4: Adattatori per Piattaforme Specifiche (`templates/adapters/`)
- `gemini/`: `GEMINI.md` e configurazione regole per Antigravity/Gemini.
- `cline-roo/`: `.clinerules` e `.roomodes` per configurare i 4 subagenti (`implementer`, `verifier`, `reviewer`, `auditor`) con DeepSeek o Qwen.
- `cursor/`: `.cursorrules` e `.cursor/rules/ba-workflow.mdc`.
- `windsurf/`: `.windsurfrules` e workflows.
- `copilot/`: `.github/copilot-instructions.md`.
- `claude/`: Mantieni l'attuale `.claude-plugin/` e `hooks/hooks.json`.

---

## Acceptance Criteria (Criteri di Accettazione Verificabili)

- [ ] **CLI Core Standalone**: Lo script `scripts/ba.sh` (o `bin/ba`) permette di eseguire `detect`, `gate`, `prove-test`, `prove-refactor`, `scan` e `test-times` senza dipendere da variabili di ambiente `CLAUDE_*`.
- [ ] **Standard AGENTS.md**: Presente nella root del repository un file `AGENTS.md` universale, valido per tutti i modelli (Gemini, DeepSeek, Qwen, GPT-4o, Claude).
- [ ] **Adapter Google Antigravity & Gemini**: Creata la configurazione `GEMINI.md` e la documentazione/regole per l'integrazione con l'ecosistema Gemini e Google Antigravity.
- [ ] **Adapter DeepSeek & Qwen (Cline / Roo Code)**: Creati i file template `.clinerules` e `.roomodes` che abilitano i ruoli `implementer`, `verifier`, `reviewer` e `auditor` su Cline/Roo Code.
- [ ] **Adapter Cursor & Windsurf & Copilot**: Creati i template `.cursorrules`, `.windsurfrules` e `.github/copilot-instructions.md`.
- [ ] **Server MCP (`mcp/`)**: Implementato un server MCP standard che espone le verifiche deterministiche di `ba` per qualsiasi client AI abilitato a MCP.
- [ ] **Zero Regressioni Claude Code**: Il plugin Claude Code esistente continua a funzionare perfettamente tramite `.claude-plugin/` e `hooks/hooks.json`.
- [ ] **Documentazione Aggiornata**: Il `README.md` include una matrice di compatibilità e guide di avvio rapido per ogni assistente supportato.

---

## Notes & Note Operative
- `scripts/auto-guard.sh` e `scripts/secret-guard.sh`: mantenere il supporto hook Claude, ma aggiungere fallback o modalità standard agnostiche quando invocati fuori da Claude Code.
- Non duplicare la logica deterministica: gli script di prova (`prove-test.sh`, `prove-refactor.sh`, `gate.sh`) rimangono l'unica fonte di verità per la verifica del codice, condivisi da tutti gli agenti.
- Gli agenti in `agents/` devono mantenere il prompt di sistema ma rendere `model:` configurabile o rimosso per gli ambienti multi-modello.

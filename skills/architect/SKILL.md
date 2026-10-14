---
name: architect
description: Interactive total system architecture & design for a new software project. Interviews you on requirements, proposes complete architecture, tech stack, data models, hosting & cloud topology (Docker/K8s/Terraform/Aspire), and generates C4 Mermaid diagrams (Context, Container, Component, Deployment, ERD, Sequence), saving docs/architecture/* and MVP specs for /ba:issues.
disable-model-invocation: true
argument-hint: <what you want to build or system description>
allowed-tools: Read Grep Glob Write Edit AskUserQuestion WebSearch WebFetch Bash(git *) Bash(gh *) Bash(bash *)
---

Request: $ARGUMENTS

Scripts: `S=${CLAUDE_SKILL_DIR}/../../scripts`

# Principles
- Complete coverage: architecture, application design, data models, hosting topology, orchestration, IaC, security, and observability.
- Concrete and executable: every diagram is valid Mermaid (rendered directly on GitHub and IDEs); every rule is checkable.
- Integrates seamlessly with the BetterAI pipeline: writes `docs/architecture/system-architecture.md`, updates `docs/architecture.md` (the confirmed contract for `ba:verifier` and `ba:optimize`), and writes `docs/specs/<slug>-mvp.md` for `/ba:issues`.

---

# 0. Context & Setup (silent)
1. `mkdir -p docs/architecture docs/specs .ba`
2. Check existing workspace: `git ls-files | head -200`, README head, `bash $S/detect.sh .` if code exists.
3. **Online research permission** (`.ba/config.json` -> `"web":"allow"|"deny"`):
   - If not set: ask once with AskUserQuestion: "Posso cercare online, solo su siti ufficiali dei provider (Azure, AWS, GCP, Cloudflare, Docker, K8s, Aspire, Terraform), documentazione e costi aggiornati? La risposta viene salvata." (Consigliato: sì).
   - If allowed: lookups must stick strictly to official documentation and pricing pages (learn.microsoft.com, docs.aws.amazon.com, cloud.google.com, docs.docker.com, kubernetes.io, developer.hashicorp.com, vercel.com/docs, supabase.com/docs, cloudflare.com).

---

# 1. Interactive Structured Interview
Interview the user with `AskUserQuestion`, max 3-4 questions per round.
**Every question must have a recommended option first, labelled "(Consigliato)"**, tailored to the user's initial prompt and context. Skip questions already answered.

### Round 1: Vision, Domain & Scale
- **System Domain & Multi-tenancy**: B2B SaaS multi-tenant / B2C consumer application / Internal enterprise platform / Marketplace.
- **Scale & Load Profile**: Initial MVP (1k-5k DAU) / Medium growth (50k DAU, ~100 req/s) / High throughput (event-driven, stream processing).
- **Non-functional SLA & Latency**: Standard web (p95 < 200ms, SLA 99.9%) / Low-latency (< 50ms) / Offline-first synchronization.

### Round 2: Application Stack & Client Platforms
- **Clients & Frontend**: Web SPA/SSR (Next.js / React / Blazor) + Mobile App (Flutter / React Native / .NET MAUI / Native iOS & Android) / Headless API only.
- **Backend Runtime & Language**: .NET 9 (C#) / Node.js (TypeScript) / Python (FastAPI) / Go / Java (Spring Boot) / Rust.
- **Architectural Style**: Modular Monolith with Clean Architecture (Domain, Application, Infrastructure, Presentation) / Event-Driven Microservices / Vertical Slice Architecture.

### Round 3: Data, Storage & Messaging
- **Primary Database**: PostgreSQL (relational standard) / SQL Server (enterprise/Azure) / MySQL.
- **Caching & Secondary Storage**: Redis / Dragonfly (session, token, cache) + NoSQL / Document DB (MongoDB, CosmosDB) + Search (Meilisearch, Elasticsearch).
- **Asynchronous Messaging**: RabbitMQ (standard AMQP) / Azure Service Bus or AWS SQS (cloud-managed) / Apache Kafka or Redpanda (streaming event log).

### Round 4: Hosting, Cloud Topology & DevOps (TUTTO)
- **Cloud Provider**: Microsoft Azure / AWS / Google Cloud / Hetzner Cloud (cost-efficient EU) / Vercel + Supabase.
- **Local Dev & Orchestration**:
  - .NET Aspire (`Aspire.Hosting` + built-in OpenTelemetry dashboard) + Docker containers.
  - Docker Compose (polyglot multi-container environment).
- **Production Compute & Orchestration**:
  - Container Apps / Serverless Containers (Azure Container Apps / AWS ECS Fargate / Cloud Run).
  - Managed Kubernetes (AKS / EKS / GKE).
  - Lightweight K3s or single VM + Docker Compose + Caddy.
- **Infrastructure as Code (IaC) & CI/CD**:
  - Terraform / OpenTofu + GitHub Actions.
  - Azure Bicep + GitHub Actions.
  - Docker Compose + GitHub Actions.

---

# 2. Architecture & Design Generation
Read `${CLAUDE_SKILL_DIR}/references/c4-mermaid-templates.md` and `${CLAUDE_SKILL_DIR}/references/hosting-matrix.md`.
Generate the complete architectural blueprint across 3 files:

### File 1: `docs/architecture/system-architecture.md`
Follow `${CLAUDE_SKILL_DIR}/../../templates/system-architecture.md` layout:
1. **Executive Summary & Drivers**: Business goal, users, quality attributes.
2. **C4 Level 1: System Context Diagram** (Mermaid: User, System boundary, External systems).
3. **C4 Level 2: Container Diagram** (Mermaid: Clients, API Gateway/BFF, Backend Services, Background Worker, Database, Cache, Queue).
4. **C4 Level 3: Component Diagram** (Mermaid: Clean Architecture layers inside core backend service).
5. **Data Architecture & ERD** (Mermaid `erDiagram`: Core entities, primary/foreign keys, cardinality).
6. **Core Dynamic Flow: Sequence Diagram** (Mermaid `sequenceDiagram`: End-to-end critical flow with numbered steps).
7. **Infrastructure, Hosting & Cloud Topology** (Mermaid `flowchart TD`: Ingress, VPC, Subnets, Compute clusters, Managed DB, Cache, Blob storage, Secrets store, CDN).
8. **Sizing, HA & Disaster Recovery**: CPU/RAM specs, auto-scaling thresholds, Multi-AZ failover, RPO/RTO.
9. **DevOps & IaC Plan**: Folder structure for Docker / Aspire / Terraform / Bicep / GitHub Actions.
10. **Security & Observability**: OAuth2/OIDC, zero-trust network, secrets manager, OpenTelemetry metrics/logs/traces.
11. **Architectural Decision Records (ADRs)**: 2-3 key ADRs explaining why the stack, database, and hosting were chosen.
12. **MVP Module Breakdown**: Ordered roadmap of initial modules.

### File 2: `docs/architecture.md` (Root Contract)
Follow `${CLAUDE_SKILL_DIR}/../../templates/architecture.md` layout, set `Status: confirmed`:
- Style (e.g. Clean Architecture / Modular Monolith).
- Layers / modules table (Domain, Application, Infrastructure, Presentation) with concrete paths.
- Enforceable rules (R1-R4) checkable by tools (e.g. NetArchTest, dependency-cruiser, ArchUnit, import-linter).
- Enforcement tool and command.

### File 3: `docs/specs/<slug>-mvp.md` (First Executable Spec)
Follow `${CLAUDE_SKILL_DIR}/../../templates/spec.md` layout, set `Status: approved`:
- First shippable MVP module (e.g. core entity domain, authentication & health baseline).
- Concrete requirements (R1..Rn) with observable, testable acceptance criteria.
- Ready for immediate issue decomposition via `/ba:issues`.

---

# 3. User Approval & Next Steps
Show the user a concise summary table:
```
Architecture Blueprint Generated:
- Style: <Architecture Style>
- Tech Stack: <Frontend> + <Backend> + <Database> + <Queue/Cache>
- Hosting & Topology: <Cloud Provider> + <Container Orchestration> (<Production Sizing>)
- IaC & DevOps: <IaC Tool> + <Local Dev Orchestrator (Aspire/Docker)>
- Files:
  - docs/architecture/system-architecture.md (C4 diagrams, ERD, sequences, cloud topology, ADRs)
  - docs/architecture.md (enforceable layer rules for ba:verifier and ba:optimize)
  - docs/specs/<slug>-mvp.md (first MVP module ready for implementation)

Approvi l'architettura proposta? (sì / modifiche)
```

On user approval ("sì"):
- Commit the documents: `git add docs/ && git commit -m "docs: define complete system architecture and MVP specification"`
- Announce next steps:
  - Run `/ba:issues docs/specs/<slug>-mvp.md` to break the MVP into small, verifiable GitHub issues.
  - Or run `/ba:auto docs/specs/<slug>-mvp.md merge` to implement the foundation autonomously.

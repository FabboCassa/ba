# System Architecture: <System Name>

Status: draft | confirmed        Confirmed by: <user> on <date>
Project: <System Name>          Target Scale: <e.g. 10k users, 500 req/sec>

---

## 1. Executive Summary & Problem Space
- **Business Goal**: <what problem this software solves and expected outcome>
- **Core Users & Stakeholders**: <actors interacting with the system>
- **Key Architectural Drivers**: <throughput, latency, availability 99.9%, security, compliance>

---

## 2. System Context (C4 Level 1)
Shows users, our system boundary, and external system integrations.

```mermaid
flowchart TD
    classDef person fill:#08427B,stroke:#073B6F,color:#fff
    classDef system fill:#1168BD,stroke:#0B4884,color:#fff
    classDef external fill:#999999,stroke:#666666,color:#fff

    User["<User Person><br/>[Person]<br/><description>"]:::person
    System["<System Name><br/>[Software System]<br/><main capability>"]:::system
    ExtService["<External Service><br/>[External System]<br/><integration purpose>"]:::external

    User -->|"Uses via HTTPS"| System
    System -->|"Calls REST / gRPC API"| ExtService
```

---

## 3. Container Architecture (C4 Level 2)
Deployable applications, databases, caches, and queues.

```mermaid
flowchart TD
    classDef client fill:#0078D4,stroke:#005A9E,color:#fff
    classDef api fill:#107C41,stroke:#0B5A2F,color:#fff
    classDef db fill:#D83B01,stroke:#A80000,color:#fff
    classDef queue fill:#8764B8,stroke:#5C2D91,color:#fff

    subgraph Clients["Clients"]
        Web["Web Frontend<br/>[Next.js / React / Blazor]"]:::client
        Mobile["Mobile App<br/>[Flutter / MAUI / React Native]"]:::client
    end

    subgraph API["Backend Services"]
        Gateway["API Gateway / Ingress<br/>[Reverse Proxy / Envoy]"]:::api
        CoreApi["Main API Backend<br/>[.NET / Node / Go / Python]"]:::api
        Worker["Background Worker<br/>[Worker / Queue Consumer]"]:::api
    end

    subgraph Persistence["Storage & Queues"]
        DB[("Database<br/>[PostgreSQL / SQL Server]")]:::db
        Cache[("Cache<br/>[Redis / Dragonfly]")]:::db
        Bus["Message Broker<br/>[RabbitMQ / Service Bus / Kafka]"]:::queue
    end

    Web --> Gateway
    Mobile --> Gateway
    Gateway --> CoreApi
    CoreApi --> DB
    CoreApi --> Cache
    CoreApi --> Bus
    Bus --> Worker
    Worker --> DB
```

---

## 4. Component Architecture (C4 Level 3)
Layering and module decomposition inside the primary service.

```mermaid
flowchart TD
    subgraph Presentation["Presentation Layer (API / Endpoints)"]
        Endpoints["Controllers / Minimal API Endpoints"]
        AuthMiddleware["Auth & Rate Limiting Middleware"]
    end

    subgraph Application["Application Layer (Use Cases)"]
        Commands["Command & Query Handlers"]
        Ports["Service & Repository Interfaces"]
    end

    subgraph Domain["Domain Layer (Entities & Rules)"]
        Entities["Domain Aggregates & Value Objects"]
        Events["Domain Events"]
    end

    subgraph Infrastructure["Infrastructure Layer (Adapters)"]
        Adapters["ORM Repositories & External API Clients"]
    end

    Endpoints --> AuthMiddleware --> Commands
    Commands --> Ports
    Commands --> Entities
    Entities --> Events
    Adapters -.->|"Implements"| Ports
```

---

## 5. Data Architecture & ERD
Entity relationships, keys, and storage partitioning.

```mermaid
erDiagram
    TENANT ||--o{ USER : contains
    USER ||--o{ ENTITY : owns

    TENANT {
        uuid id PK
        string name
        datetime created_at
    }

    USER {
        uuid id PK
        uuid tenant_id FK
        string email
        string role
    }

    ENTITY {
        uuid id PK
        uuid user_id FK
        string status
        decimal amount
    }
```

---

## 6. Core Flow: Sequence Diagram
Step-by-step trace of the critical user interaction.

```mermaid
sequenceDiagram
    autonumber
    actor Client as User
    participant GW as API Gateway
    participant API as Core Backend
    participant DB as Database
    participant Bus as Message Bus

    Client->>GW: POST /api/v1/resource (Auth token)
    GW->>API: Forward authenticated request
    API->>DB: Validate & persist entity
    DB-->>API: Persisted entity (ID=xyz)
    API->>Bus: Publish DomainEvent
    API-->>Client: 201 Created (Resource payload)
```

---

## 7. Infrastructure, Hosting & Cloud Topology
- **Cloud Provider**: <Azure | AWS | GCP | Hetzner | Vercel | Hybrid>
- **Container Strategy**: <.NET Aspire (Local dev) + Docker / Azure Container Apps / Kubernetes (Prod)>
- **Infrastructure as Code**: <Terraform / Bicep / Docker Compose>

```mermaid
flowchart TD
    subgraph Internet["Public Zone"]
        CDN["CDN & DNS (Cloudflare / Azure Front Door)"]
    end

    subgraph Cloud["VPC / Virtual Network"]
        subgraph IngressSubnet["Public Subnet"]
            LB["Application Load Balancer / Ingress Controller"]
        end

        subgraph ComputeSubnet["Private Compute Subnet"]
            App1["Container Instance A"]
            App2["Container Instance B"]
            WorkerApp["Worker Container"]
        end

        subgraph DataSubnet["Private Data Subnet"]
            ManagedDB[("Primary Database (Multi-AZ)")]
            ManagedCache[("Redis Cache")]
            Broker["Managed Message Queue"]
        end
    end

    CDN --> LB
    LB --> App1 & App2
    App1 & App2 --> ManagedDB & ManagedCache & Broker
    WorkerApp --> Broker & ManagedDB
```

---

## 8. Sizing, High Availability & Disaster Recovery
- **Target Scale**: <DAU, peak RPS, storage per month>
- **Compute Sizing**: <e.g. 2 instances, 1 vCPU, 2GB RAM with auto-scaling to 6>
- **Database Sizing**: <e.g. 2 vCPU, 8GB RAM, auto-growth storage>
- **High Availability**: <Multi-AZ redundancy, health-check probes>
- **Disaster Recovery**: <RPO: 5 min (PITR), RTO: 30 min, daily geo-replicated backups>

---

## 9. Security, Governance & Observability
- **Authentication & Authorization**: <OAuth2 / OIDC with JWT, RBAC / Claims>
- **Secrets Management**: <Azure Key Vault / AWS Secrets Manager / HashiCorp Vault>
- **Network Isolation**: <Private endpoints for DB and storage, zero public access to data tier>
- **Observability**: <OpenTelemetry SDK exporting traces and metrics to Prometheus/Grafana or AppInsights>

---

## 10. Architectural Decision Records (ADRs)
- **ADR-001**: <Decision, e.g., Choosing PostgreSQL over MongoDB, context and rationale>
- **ADR-002**: <Decision, e.g., Choosing Azure Container Apps + Aspire over full Kubernetes, context and rationale>

---

## 11. Initial MVP Implementation Modules
1. **Module 1**: <Core Auth & Tenant Onboarding> (`docs/specs/01-auth-tenants.md`)
2. **Module 2**: <Core Domain CRUD & Business Logic> (`docs/specs/02-core-domain.md`)
3. **Module 3**: <Async Worker & Integrations> (`docs/specs/03-workers-integrations.md`)

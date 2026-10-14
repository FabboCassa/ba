# C4 and Mermaid Diagram Patterns for Software Architecture

Mermaid diagrams must be clean, valid, and fully compatible with GitHub markdown rendering and IDE previews.
Always quote node labels that contain punctuation or parentheses, e.g., `id["Label (Description)"]`.

---

## 1. C4 Level 1: System Context Diagram
Shows the system in its environment, including human users and external systems.

```mermaid
flowchart TD
    classDef person fill:#08427B,stroke:#073B6F,color:#fff
    classDef system fill:#1168BD,stroke:#0B4884,color:#fff
    classDef external fill:#999999,stroke:#666666,color:#fff

    User["Customer / User<br/>[Person]<br/>Browses and purchases products"]:::person
    Admin["Operations Admin<br/>[Person]<br/>Manages catalog and orders"]:::person

    System["Core Platform<br/>[Software System]<br/>Provides shopping, orders, and fulfillment"]:::system

    PaymentGateway["Stripe / Payment Gateway<br/>[External System]<br/>Processes credit cards and webhooks"]:::external
    ShippingProvider["Logistics API<br/>[External System]<br/>Calculates rates and generates tracking"]:::external
    EmailService["SendGrid / SES<br/>[External System]<br/>Sends transactional emails"]:::external

    User -->|"Uses HTTPS"| System
    Admin -->|"Uses HTTPS/VPN"| System
    System -->|"Processes payments via REST"| PaymentGateway
    System -->|"Queries rates & labels"| ShippingProvider
    System -->|"Sends notifications"| EmailService
```

---

## 2. C4 Level 2: Container Diagram
Decomposes the system into deployable units (Web apps, Mobile apps, APIs, Background Workers, Databases, Queues).

```mermaid
flowchart TD
    classDef client fill:#0078D4,stroke:#005A9E,color:#fff
    classDef api fill:#107C41,stroke:#0B5A2F,color:#fff
    classDef db fill:#D83B01,stroke:#A80000,color:#fff
    classDef queue fill:#8764B8,stroke:#5C2D91,color:#fff
    classDef ext fill:#737373,stroke:#5A5A5A,color:#fff

    subgraph Clients["Client Layer"]
        Web["Web Application<br/>[Next.js / React]<br/>Responsive storefront and customer portal"]:::client
        Mobile["Mobile App<br/>[Flutter / React Native]<br/>iOS and Android mobile client"]:::client
    end

    subgraph Ingress["Gateway & Load Balancing"]
        Gateway["API Gateway / YARP / Ingress<br/>[Reverse Proxy / Envoy]<br/>Routing, TLS termination, Rate limiting"]:::api
    end

    subgraph Services["Application Services"]
        CoreApi["Backend API Service<br/>[.NET / Node / Go / Python]<br/>Handles business logic, auth, REST/gRPC"]:::api
        Worker["Async Background Worker<br/>[Worker Service / Celery / BullMQ]<br/>Processes async jobs, reports, sync"]:::api
    end

    subgraph Data["Persistence & Messaging"]
        DB[("Primary Database<br/>[PostgreSQL / SQL Server]<br/>Transactional relational data")]:::db
        Cache[("In-Memory Cache<br/>[Redis / Dragonfly]<br/>Session store, token cache, query cache")]:::db
        Broker["Message Broker<br/>[RabbitMQ / Azure Service Bus / Kafka]<br/>Pub/sub events and reliable queues"]:::queue
    end

    subgraph External["External Services"]
        ExtPayment["Payment Provider"]:::ext
    end

    Web -->|"HTTPS / JSON"| Gateway
    Mobile -->|"HTTPS / JSON"| Gateway
    Gateway -->|"Internal HTTP"| CoreApi

    CoreApi -->|"Read / Write (ORM)"| DB
    CoreApi -->|"Get / Set / TTL"| Cache
    CoreApi -->|"Publish domain events"| Broker
    CoreApi -->|"Process payments"| ExtPayment

    Broker -->|"Consume events"| Worker
    Worker -->|"Update state"| DB
    Worker -->|"Read / Write"| Cache
```

---

## 3. C4 Level 3: Component Diagram (Inside Backend API)
Breaks down the core service into logical layers (Clean / Hexagonal architecture).

```mermaid
flowchart TD
    subgraph Presentation["Presentation Layer (API / Controllers)"]
        Ctrl["Controllers / Minimal API Endpoints"]
        AuthMiddleware["JWT Authentication Middleware"]
        ValidationFilter["FluentValidation / Schema Filter"]
    end

    subgraph Application["Application Layer (Use Cases / CQRS)"]
        Commands["Command Handlers (CreateOrder, CancelOrder)"]
        Queries["Query Handlers (GetOrderById, ListOrders)"]
        Interfaces["Repository & Service Interfaces (Ports)"]
    end

    subgraph Domain["Domain Layer (Enterprise Business Rules)"]
        Entities["Domain Entities & Aggregates (Order, LineItem)"]
        ValueObjects["Value Objects (Money, Address)"]
        DomainEvents["Domain Events (OrderPlaced, PaymentFailed)"]
    end

    subgraph Infrastructure["Infrastructure Layer (Adapters)"]
        RepoImpl["EF Core / Dapper / Prisma Repositories"]
        MsgPublisher["RabbitMQ / ServiceBus Message Publisher"]
        ExtClient["HTTP Client to External APIs"]
    end

    Ctrl --> AuthMiddleware --> ValidationFilter --> Commands & Queries
    Commands & Queries --> Interfaces
    Commands & Queries --> Entities & ValueObjects
    Entities --> DomainEvents

    RepoImpl -.->|"Implements"| Interfaces
    MsgPublisher -.->|"Implements"| Interfaces
    ExtClient -.->|"Implements"| Interfaces
```

---

## 4. Data Model: Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    TENANT ||--o{ USER : contains
    TENANT ||--o{ ORDER : owns
    USER ||--o{ ORDER : places
    ORDER ||--|{ ORDER_ITEM : includes
    PRODUCT ||--o{ ORDER_ITEM : ordered_in

    TENANT {
        uuid id PK
        string name
        string plan
        datetime created_at
    }

    USER {
        uuid id PK
        uuid tenant_id FK
        string email
        string password_hash
        string role
        datetime created_at
    }

    ORDER {
        uuid id PK
        uuid tenant_id FK
        uuid user_id FK
        string status
        decimal total_amount
        string currency
        datetime created_at
    }

    ORDER_ITEM {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        int quantity
        decimal unit_price
    }

    PRODUCT {
        uuid id PK
        uuid tenant_id FK
        string sku
        string title
        decimal price
        int stock_qty
    }
```

---

## 5. Core Dynamic Flow: Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Client as User / Web Client
    participant GW as API Gateway
    participant API as Backend API
    participant Cache as Redis Cache
    participant DB as PostgreSQL DB
    participant Bus as Message Broker
    participant Ext as Stripe Payment

    Client->>GW: POST /api/v1/orders (Bearer JWT)
    GW->>API: Forward validated request
    API->>Cache: Check idempotency key
    Cache-->>API: Key not found (proceed)
    API->>DB: Begin transaction & persist draft order
    DB-->>API: Draft order created (ID=123)
    API->>Ext: Create PaymentIntent (amount, currency)
    Ext-->>API: PaymentIntent authorized
    API->>DB: Commit order status = "Confirmed"
    API->>Cache: Save idempotency key (TTL 24h)
    API->>Bus: Publish "OrderConfirmedEvent"
    API-->>Client: 201 Created (Order Details & Tracking)
```

---

## 6. Infrastructure & Deployment Topology Diagram

```mermaid
flowchart TD
    subgraph Internet["Public Internet"]
        DNS["DNS / Cloudflare CDN & DDoS Protection"]
    end

    subgraph Cloud["Cloud Provider (Azure / AWS / GCP / Hetzner)"]
        subgraph PublicSubnet["Public Subnet / DMZ"]
            LB["Ingress Load Balancer (ALB / App Gateway / NGINX)"]
        end

        subgraph PrivateSubnetApp["Private Application Subnet"]
            subgraph Cluster["Container Cluster (Kubernetes / ECS / Aspire Host)"]
                Pod1["API Container Replica 1"]
                Pod2["API Container Replica 2"]
                WorkerPod["Background Worker Replica"]
            end
        end

        subgraph PrivateSubnetData["Private Data Subnet"]
            DBPrimary[("Primary DB (Managed PostgreSQL / RDS)")]
            DBReplica[("Read Replica DB")]
            RedisCluster[("Managed Redis Cache")]
            QueueService["Managed Message Queue (Service Bus / SQS)"]
        end

        subgraph StorageAndSec["Storage & Secrets"]
            BlobStore[("Object Storage (S3 / Azure Blob)")]
            SecretStore["Secret Store (Key Vault / Secrets Manager)"]
        end
    end

    DNS --> LB
    LB --> Pod1 & Pod2
    Pod1 & Pod2 --> DBPrimary
    DBPrimary -.->|"Replication"| DBReplica
    Pod1 & Pod2 --> RedisCluster
    Pod1 & Pod2 --> QueueService
    WorkerPod --> QueueService
    WorkerPod --> DBPrimary

    Cluster -.->|"Read secrets at startup"| SecretStore
    Cluster -.->|"Upload / Download assets"| BlobStore
```

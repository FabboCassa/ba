# Hosting, Cloud & DevOps Decision Matrix

Comparison guide for hosting, container orchestration, and Infrastructure as Code (IaC) across tech stacks.

---

## 1. Cloud & Hosting Providers

| Provider | Best For | Typical Use Cases | Trade-offs |
|---|---|---|---|
| **Microsoft Azure** | Enterprise, .NET ecosystems, Microsoft Entra ID | Azure Container Apps, AKS, Azure SQL, Blob Storage | Enterprise pricing; UI complexity |
| **AWS (Amazon Web Services)** | Mature global cloud, extensive managed services | ECS Fargate, EKS, RDS PostgreSQL, S3, SQS | Steep learning curve, permission complexity (IAM) |
| **Google Cloud (GCP)** | Data, AI/ML, Kubernetes native | Google Kubernetes Engine (GKE), Cloud Run, BigQuery | Less popular for traditional enterprise backends |
| **Hetzner / OVH (Dedicated / Cloud)** | High compute per $, cost efficiency, EU compliance | Self-hosted K3s, Docker Swarm, PostgreSQL on bare metal | Less managed PaaS; requires more operational maintenance |
| **Vercel / Cloudflare** | Frontend SPAs, Next.js, Edge functions, CDN | Static assets, Edge API Gateway, Global caching | Vendor lock-in for backend logic; cold starts for heavy apps |
| **Supabase / Neon** | Rapid MVP, Serverless PostgreSQL | Managed DB, Auth, Realtime, Vector embeddings | Resource limits on free/low tiers |

---

## 2. Containerization & Orchestration

### A. Local Orchestration: .NET Aspire vs Docker Compose

| Dimension | .NET Aspire (`Aspire.Hosting`) | Docker Compose (`docker-compose.yml`) |
|---|---|---|
| **Ecosystem** | .NET 8/9 native, polyglot containers supported | Universal, language-agnostic |
| **Dashboard** | Built-in OpenTelemetry dashboard (traces, metrics, logs) | Requires third-party tools (Portainer, Dozzle) |
| **Service Discovery** | Automated connection strings and dependency injection | Manual environment variables & network names |
| **Cloud Deployment** | Compiles to Azure Container Apps or K8s via `azd` | Requires compose-to-k8s or Docker Swarm |

### B. Production Orchestration

| Platform | Best Scale | Complexity | Maintenance Overhead |
|---|---|---|---|
| **Container Apps / Cloud Run / ECS Fargate** | Small to High (Serverless containers) | Low-Medium | Very Low (No cluster management, auto-scaling to zero) |
| **Managed Kubernetes (AKS / EKS / GKE)** | High to Massive (Multi-service microservices) | High | Medium (Cluster upgrades, ingress controllers, node pools) |
| **Lightweight K8s (K3s / MicroK8s)** | Single-server / Small cluster on Hetzner | Medium | High (Backups, TLS, disk management handled by team) |
| **Single VM + Docker Compose + Caddy** | MVP / Early Stage (< 10k users) | Very Low | Low (Requires automated off-site backups) |

---

## 3. Infrastructure as Code (IaC)

| Tool | Language | Best Fit | Multi-Cloud? |
|---|---|---|---|
| **Terraform / OpenTofu** | HCL | Universal standard for AWS, Azure, GCP, Cloudflare, Hetzner | Yes |
| **Azure Bicep** | Domain-specific | Azure-first architectures (cleaner than ARM JSON) | Azure only |
| **AWS CDK / CloudFormation** | TS/Python/Go | AWS-native deep integration | AWS only |
| **Pulumi** | TS, C#, Python, Go | Developers who prefer real programming languages | Yes |

---

## 4. Sizing & High Availability Tiers

### Tier 1: MVP / Startup (< 1,000 DAU)
- **Compute**: 1-2 container instances (0.5 - 1 vCPU, 1-2 GB RAM each).
- **Database**: Managed Single-node DB (e.g. Postgres 2 vCPU, 4GB RAM), daily automated backups.
- **Cache**: Single Redis instance (1GB) or in-memory cache.
- **RPO/RTO**: RPO = 24h, RTO = 2h.
- **Target Monthly Cost**: $30 - $150.

### Tier 2: Production Business (< 50,000 DAU)
- **Compute**: Auto-scaling containers (min 2, max 10 instances across 2 availability zones).
- **Database**: Managed Primary DB with automated failover replica + point-in-time recovery (PITR).
- **Cache**: Managed Redis cluster / replication pair.
- **Message Broker**: Managed RabbitMQ or Cloud Queue (SQS / Service Bus).
- **RPO/RTO**: RPO = 5 min, RTO = 15 min.
- **Target Monthly Cost**: $300 - $1,500.

### Tier 3: High Scale / Enterprise (> 50,000 DAU)
- **Compute**: Multi-zone Kubernetes cluster or multi-region container apps with global traffic manager.
- **Database**: Distributed relational cluster (Aurora / Citus / Azure SQL Hyperscale) with read-replicas.
- **Observability**: Dedicated OpenTelemetry collector pipeline into Grafana / Datadog.
- **RPO/RTO**: RPO < 1 min, RTO < 5 min.
- **Target Monthly Cost**: $2,000+.

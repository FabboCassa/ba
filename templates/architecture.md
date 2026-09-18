# Architecture
Status: draft | confirmed        Confirmed by: <user> on <date>
Style: <Layered MVC | Clean | Hexagonal | Vertical slice | MVVM | MVI | Feature modules | ...>

## Layers / modules
| Name | Paths | Responsibility | May depend on |
|---|---|---|---|
| Domain | src/Domain/** | entities, rules, no I/O | nothing |
| Application | src/Application/** | use cases, ports | Domain |
| Infrastructure | src/Infrastructure/** | DB, HTTP clients, files | Application, Domain |
| Presentation | src/Api/** | controllers/UI, mapping | Application |

## Rules (each must be checkable by a tool or test)
- R1 Domain has no reference to ORM/HTTP/UI packages.
- R2 No dependency cycles between modules.
- R3 Controllers/Views contain no data access.
- R4 <where new features go, naming, one public entry per module...>

## Enforcement
Tool/test: <dependency-cruiser | NetArchTest | ArchUnit | import-linter | go-arch-lint | Konsist>  File: <path>  Runs in: gate (build/test)

## Allowed exceptions
- <path> -> <path>: <why>

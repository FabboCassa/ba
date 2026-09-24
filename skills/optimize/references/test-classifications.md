# Test slowness classifications

For each slow test, classify the cause and propose a fix:

| Cause | Fix |
|---|---|
| `sleep/poll` | Fake clock / await condition |
| `setup-per-test` (DB migrate, container, app boot) | Shared fixture per class/collection, transaction rollback |
| `real-io` (network, disk, external service) | Boundary fake + one contract test kept in `slow` tier |
| `data-volume` / `combinatorial` | Representative cases + property-based sampling with fixed seed, full matrix in `slow` tier |
| `mega-test` (one test = many scenarios) | One test per scenario (logical split, same assertions) |
| `serial` | Enable safe parallelism (isolated state) |

## Tier proposal
Tag syntax by framework:
- .NET: `[Trait("Category","Slow")]`
- Python: `@pytest.mark.slow`
- JS/TS: separate vitest/jest project or config
- Go: `//go:build slow`
- Java/Kotlin: `@Tag("slow")`

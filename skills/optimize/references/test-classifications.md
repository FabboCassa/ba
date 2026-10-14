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

# Test slowness classifications & Tiering Strategy

When tests take 10+ minutes or up to 1 hour, developers and agents cannot iterate effectively.
The solution is a two-tier strategy:
1. **Fast Tier (`TEST_FAST`)**: Runs in seconds or <2 minutes during `/ba:implement`, `/ba:auto`, and PR gates.
2. **Full / Slow Tier (`TEST`)**: Runs before PR merges and in nightly CI jobs. Nothing is deleted or weakened.

## Classifications & Fixes

| Cause | Fix |
|---|---|
| `sleep/poll` | Fake clock (`vi.useFakeTimers()`, `TimeProvider`) / await condition polling with timeout |
| `setup-per-test` (DB migrate, container, app boot) | Shared fixture per class/collection (`IClassFixture`, `pytest.fixture(scope="session")`), transaction rollback |
| `real-io` (network, disk, external service) | Boundary fake + one contract/integration test kept in `slow` tier |
| `data-volume` / `combinatorial` | Representative cases + property-based sampling with fixed seed, full matrix in `slow` tier |
| `mega-test` (one test = many scenarios) | One test per scenario (logical split, same assertions) |
| `serial` execution | Enable safe test parallelism (isolated state, unique DB/schema per thread) |
| `unbounded-run` (hanging/deadlock) | Per-test timeouts (`--timeout 60` or `[Timeout(5000)]`) |

---

## Tier Syntax & Execution Commands

### .NET (xUnit / NUnit / MSTest)
- **Tag syntax**: `[Trait("Category", "Slow")]` or `[Trait("Category", "Integration")]`
- **Fast tier command**: `dotnet test --filter "Category!=Slow&Category!=Integration"`
- **Full suite command**: `dotnet test`
- **Parallelization**: `[assembly: CollectionBehavior(MaxParallelThreads = 4)]`

### Python (pytest)
- **Tag syntax**: `@pytest.mark.slow` or `@pytest.mark.integration` in `pyproject.toml`
- **Fast tier command**: `pytest -q -m "not slow and not integration"`
- **Full suite command**: `pytest -q`
- **Parallelization**: `pytest -n auto` (`pytest-xdist`)

### JavaScript / TypeScript (Vitest / Jest / Playwright)
- **Tag / Pattern**: Separate file naming (`*.test.ts` vs `*.e2e.ts` / `*.integration.ts`) or tags
- **Fast tier command (Vitest)**: `npx vitest run --exclude='**/*.e2e.*' --exclude='**/*.integration.*'`
- **Fast tier command (Jest)**: `npx jest --testPathIgnorePatterns='e2e|integration'`
- **Full suite command**: `npx vitest run` / `npx jest`

### Go
- **Tag syntax**: `testing.Short()` check or `//go:build slow`
- **Fast tier command**: `go test -short ./...`
- **Full suite command**: `go test ./...`

### Java / Kotlin (JUnit 5)
- **Tag syntax**: `@Tag("slow")` or `@Tag("integration")`
- **Fast tier command (Gradle)**: `./gradlew test -x integrationTest`
- **Fast tier command (Maven)**: `mvn test -Dgroups="!slow & !integration"`
- **Full suite command**: `./gradlew test` / `mvn test`

---

## Configuring `.ba/commands.env`
To customize project test tiers deterministically:
```bash
BUILD=dotnet build
TEST=dotnet test
TEST_FAST=dotnet test --filter "Category!=Slow&Category!=Integration"
LINT=dotnet format --verify-no-changes
```

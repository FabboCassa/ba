# Analysis tools by language/stack

## Architecture (arch-check)
- JS/TS: dependency-cruiser, madge
- .NET: NetArchTest, ArchUnitNET
- JVM: ArchUnit
- Kotlin: Konsist
- Python: import-linter
- Go: go-arch-lint

## Dead code / unused exports / unused deps
- JS/TS: knip
- Python: vulture + ruff
- .NET: IDE0051/IDE0052/CA1822 analyzers (`dotnet build -p:EnforceCodeStyleInBuild=true`)
- Go: staticcheck + `deadcode`
- Rust: clippy + cargo-machete
- Java: PMD

## Duplication
- Any language: jscpd

## Complexity hot spots
```bash
git log --format= --name-only | sort | uniq -c | sort -rn | head -30
```
Then inspect the longest/most-branched functions in those files.

## Benchmarking
- .NET: BenchmarkDotNet
- JS/TS: vitest bench / tinybench
- Python: pytest-benchmark
- Go: `go test -bench`
- Rust: criterion
- Java: JMH

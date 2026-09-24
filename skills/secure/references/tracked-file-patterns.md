# Tracked file patterns to check for secrets

Files that should NEVER be tracked in git (check with `git ls-files`):

## Secret/credential files
- `.env*` (NOT `.env.example`)
- `*.pem *.key *.p12 *.pfx *.jks *.keystore *.mobileprovision *.p8 id_rsa*`
- `*.tfstate*`
- `secrets.json credentials*.json service-account*.json`
- `*.sqlite *.db`

## Config files with potential secrets
- `appsettings.*.json` / `local.settings.json` with connection strings or keys
- `google-services.json` / `GoogleService-Info.plist` (not secret, but check API key restrictions are documented)

## What ships to users IS PUBLIC
Keys in front-end env (`VITE_*`, `NEXT_PUBLIC_*`, `REACT_APP_*`), in mobile code/resources/BuildConfig, in desktop binaries → anything there is readable by anyone. Flag any non-publishable key (server keys, DB creds, signing keys, payment secret keys).

## Ignore file coverage
Verify `.gitignore` / `.dockerignore` / `.npmignore` / `files` field cover the above.

## Publish dry runs (where applicable)
- `npm pack --dry-run` → list package content
- `dotnet pack` → list package content
- `python -m build` sdist listing
- `docker build` context vs `.dockerignore`
Flag unexpected files: tests with creds, .env, source maps with secrets, local DBs.

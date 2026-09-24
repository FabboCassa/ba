# Platform compliance checklists

What to verify per platform — always fetch the CURRENT values from official sources, never assume them.

## Android
- Required targetSdk level and deadline
- 64-bit / page-size requirements
- Permissions policy (sensitive permissions need declared use)
- Data safety form consistency
- Network security config
- Exported components
- Account-deletion requirement if accounts exist
- Signing (Play App Signing, keystore not in repo)

## iOS
- Required SDK/Xcode for submissions
- Privacy manifest (PrivacyInfo.xcprivacy) + required-reason APIs
- App Tracking Transparency
- ATS exceptions
- Account deletion
- Sign in with Apple rule when third-party login exists
- Purpose strings for each permission

## Web
- HTTPS/HSTS
- CSP
- Security headers
- Cookie flags (Secure/HttpOnly/SameSite)
- CORS
- Auth per OWASP ASVS level chosen (ask once, default L1)
- Dependency integrity (SRI for CDN)
- Privacy/cookie consent if analytics

## Windows/Desktop, Browser Extension, Package Registry, Containers
- The equivalent official policy (e.g. Chrome Web Store program policies + Manifest V3, NuGet/npm package signing & provenance, container base image support status)
- Each gap = finding with Kind `config` or `feature` and the source URL

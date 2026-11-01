# Cloudflare Origin CA public certificates

These are **public CA certificates**, not private signing keys or customer certificates. Downloaded over verified HTTPS from Cloudflare's official documentation on Nov-01-2026:

- RSA: <https://developers.cloudflare.com/ssl/static/origin_ca_rsa_root.pem>
- ECC: <https://developers.cloudflare.com/ssl/static/origin_ca_ecc_root.pem>
- Documentation: <https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/>

The `.crt` files retain the original PEM encoding. The bundle contains both roots. `Get-CloudflareCaFiles` pins the exact downloaded file hashes and validates them before use. Any future root update needs independent source verification and updated tests/pins.

`-CloudflareProxy` uses these roots only for an isolated certificate chain and curl's local origin request. It never installs them in the Windows trusted-root store. The public Cloudflare edge request still uses normal system/public trust, not this bundle.

Cloudflare Origin CA does not supply a Windows revocation endpoint. The local chain test checks signatures, expiry, hostname, server-auth use and the pinned anchor; Cloudflare Full (strict) and operator-managed revocation remain required. This mode is not for DNS-only/direct hosting.

# HIMS Wireframe — IIS Deployment Package

This is a self-contained static site (HTML + CSS only, no server-side
code required) containing the clickable HIMS (Hospital Information
Management System) wireframe — 20 screens covering the full OPD + IPD
patient journey.

## Folder structure

```
HIMS/
├─ index.html          ← Landing hub page (links to all 20 screens)
├─ web.config           ← IIS configuration (default document, MIME types)
├─ css/
│  └─ style.css          ← Shared design-system stylesheet
└─ screens/
   ├─ 01_login.html
   ├─ 02_dashboard.html
   ├─ ... (20 screens total)
   └─ 20_settings.html
```

## How to deploy on IIS — poc.sgsoftech.in

1. Copy this entire `HIMS` folder to your IIS server, e.g.:
   `C:\inetpub\wwwroot\poc.sgsoftech.in\HIMS`

   (If this is a dedicated POC site, you could also place it directly
   at `C:\inetpub\wwwroot\poc.sgsoftech.in` and skip the `/HIMS` subfolder,
   then the client URL will be `https://poc.sgsoftech.in/` instead of
   `https://poc.sgsoftech.in/HIMS/`.)

2. Open **IIS Manager**:
   - Right-click **Sites** → **Add Website**.
   - **Site name**: `poc.sgsoftech.in`
   - **Physical path**: `C:\inetpub\wwwroot\poc.sgsoftech.in` (or the
     `HIMS` subfolder, matching step 1)
   - **Binding**:
     - Type: `http` (add a second binding for `https` once an SSL
       certificate is installed)
     - Host name: `poc.sgsoftech.in`
     - Port: `80` (and `443` for https)

3. **DNS**: Make sure an A record (or CNAME) for `poc.sgsoftech.in`
   points to this server's public IP. Without this, the hostname
   binding above won't resolve for external visitors.

4. **SSL (recommended for client sharing)**: Install a certificate
   (e.g. via Let's Encrypt / win-acme, or your existing wildcard cert
   for `*.sgsoftech.in`) and add an https binding with host name
   `poc.sgsoftech.in` so the client can access it securely at
   `https://poc.sgsoftech.in/`.

5. Make sure the **Static Content** feature is enabled in
   Windows Features → Internet Information Services → World Wide Web
   Services → Common HTTP Features → Static Content.

6. Browse to `https://poc.sgsoftech.in/` (or `/HIMS/` if nested) — it
   will load `index.html` automatically (configured via `web.config`).

7. Share `https://poc.sgsoftech.in/` with the client — no login
   required, pure static HTML/CSS, works in any browser.

## Notes

- No build step, no dependencies, no database — just static files.
- All navigation between screens works via relative links already
  wired into each page (clickable sidebar + action buttons).
- If deploying under a sub-path (e.g. `/hims/`) instead of site root,
  no changes needed — all internal links are relative.
- To update content, just replace the HTML files in `screens/` and
  re-sync to the server (e.g. via robocopy, FTP, or a CI/CD pipeline).

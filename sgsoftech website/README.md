# SG Softech website workspace

All website-specific source, design tools, npm files, tests, screenshots, backups and deployment archives are kept inside this folder. Open this folder as the VS Code workspace to use its `.github/prompts` customizations.

## Folder layout

- `CMS/`: ASP.NET Core 8 application source and `wwwroot` frontend assets.
- `CMS/IIS-DEPLOYMENT.md`: server setup, HTTPS and SMTP instructions.
- `images/`: original supplied business and logo images.
- `.github/prompts/`: installed UI/UX Pro Max prompt, skill guides, datasets and scripts.
- `package.json`, `package-lock.json`, `node_modules/`: local npm dependencies. Framer Motion was installed as requested but is not used by the static website.
- `tests/browser-check/`: browser verification scripts and screenshots from previous design iterations.
- `backups/`: earlier website archives, including the ZIP previously stored at the repository root.
- `deployments/`: published IIS deployment ZIPs. Existing ZIPs are snapshots and are not changed when source or documentation changes.

## Run and build

From this folder:

```powershell
dotnet run --project '.\CMS\SGSoftech.Web.csproj' --urls http://localhost:5188
```

In another terminal:

```powershell
dotnet build '.\CMS\SGSoftech.Web.csproj' --configuration Release
```

The website needs the .NET SDK for development and the .NET 8 Hosting Bundle for IIS hosting. Node.js is only needed for optional npm tools and browser tests. These system runtimes are installed separately; they are not website source files. SMTP credentials remain server-only secrets.

## Browser checks

```powershell
npm ci
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.tools\ms-playwright'
npx playwright install chromium
npm run test:browser
```

Keep the application running at `http://localhost:5188` during browser checks. Set `PLAYWRIGHT_BROWSERS_PATH` in each terminal used for browser installation or tests to keep downloaded browsers inside this folder. Alternatively, set `CHROMIUM_EXECUTABLE_PATH` to an existing compatible Chromium executable.

`npm run test:browser` runs the latest logo, responsive layout and strip-control checks. The other scripts and screenshots preserve earlier verification work. In particular, `verify-marquee.cjs` targets the old separate pause button and is historical, not a current regression suite. `verify.cjs` also exercises the contact rate limiter; run it only against a local test instance, not the live website.

# Deploy SG Softech to IIS

The deployment ZIP contains the **Release-published ASP.NET Core 8 application**, not the source project. No Node.js, npm, Python or .NET SDK is needed on the server. The server does need IIS and the **.NET 8 Hosting Bundle**. The package does not contain SMTP credentials.

## 1. Prepare the server

1. On a supported Windows Server computer, enable **Web Server (IIS)** and **IIS Management Console** through Server Manager.
2. Install the latest serviced **.NET 8 Hosting Bundle** from [Microsoft's .NET 8 download page](https://dotnet.microsoft.com/en-us/download/dotnet/8.0). The bundle installs the runtime and ASP.NET Core IIS module.
3. If the bundle was installed before IIS, repair/reinstall it after enabling IIS. Restart the server during an approved maintenance window so IIS picks up the module.
4. Confirm IIS has `AspNetCoreModuleV2` under **Modules**. Use a 64-bit application pool on a 64-bit server.

## 2. Copy and configure the website

1. Copy the ZIP to the server and extract it to a dedicated folder, for example `C:\Sites\SGSoftech`.
2. Verify `web.config`, `SGSoftech.Web.dll` and `wwwroot` are directly inside that folder. Do **not** point IIS to `wwwroot`.
3. In IIS Manager, create an application pool named **SGSoftech**:
   - .NET CLR version: **No Managed Code**
   - Managed pipeline: **Integrated**
   - Identity: **ApplicationPoolIdentity**
   - Enable 32-Bit Applications: **False** on a 64-bit server
4. Grant `IIS AppPool\SGSoftech` **Read & execute**, **List folder contents** and **Read** access to the extracted folder. Do not grant general write access or use Everyone/Full Control.
5. Select **Sites > Add Website**:
   - Site name: **SGSoftech**
   - Application pool: **SGSoftech**
   - Physical path: `C:\Sites\SGSoftech`
   - Bind to your actual host name, such as `www.sgsoftech.in`.
6. Host this application at the website root, not a virtual subfolder: its asset and API URLs start with `/`.
7. Bind **HTTPS (443)** with a valid certificate; enable SNI when sharing an IP. Configure DNS and the firewall for the intended hostname and port.
8. Configure HTTP-to-HTTPS redirection in IIS or the front-end proxy before public launch. The app enables HSTS in Production but does not itself redirect HTTP. An IIS URL Rewrite redirect requires installing the URL Rewrite module; do not add such a rule without that module.
9. Keep the environment as **Production** (ASP.NET Core's default); do not enable Development on the public server.

## 3. Configure SMTP on the server only

Use your hosting platform's secret management or dedicated IIS application-pool environment variables. Do not put passwords in this ZIP, JavaScript, source control or a publicly served file.

Set these values for the **SGSoftech** application:

| Variable | Value |
| --- | --- |
| `Mail__Host` | Your SMTP hostname |
| `Mail__Port` | `587`, or your provider's STARTTLS port |
| `Mail__Username` | SMTP account username |
| `Mail__Password` | SMTP password or provider-issued app password |
| `Mail__FromAddress` | Provider-verified sender, normally `sales@sgsoftech.in` |
| `Mail__EnableSsl` | `true` |

For a dedicated IIS pool, an administrator can configure these under the pool's `environmentVariables` collection in IIS Configuration Editor (`system.applicationHost/applicationPools`), when supported by the installed IIS version. Protect server configuration access; environment variables are not an encrypted secret store. Prefer a supported secret-management solution where available.

Recycle the **SGSoftech** application pool after configuration. Permit outbound connections to the SMTP host. This application uses STARTTLS through .NET `SmtpClient`; implicit TLS-only port 465 is not supported.

Enquiries are delivered to `sales@sgsoftech.in`, with the visitor as Reply-To. Without valid SMTP settings, the contact form explicitly reports that delivery is unavailable; the rest of the site remains usable.

## 4. Verify before going live

- Open the HTTPS hostname; check the new circle logo, solution images and mobile navigation.
- Open `/product.html?product=diagnostics` and the other solution links.
- Check industry scrolling and reduced-motion behavior.
- Submit one controlled enquiry after configuring SMTP, and confirm receipt at `sales@sgsoftech.in`.
- Confirm HTTP redirects to HTTPS and the certificate matches the hostname.
- Confirm response headers include Content-Security-Policy, X-Content-Type-Options and Strict-Transport-Security over HTTPS.

## Troubleshooting and updates

- **500.19 / missing module:** verify the Hosting Bundle and `AspNetCoreModuleV2`; repair the bundle if IIS was installed later.
- **500.30 / 500.31:** inspect Windows Event Viewer > Application for ASP.NET Core startup errors. Confirm the .NET 8 runtime is installed and folder permissions are correct.
- **Missing photos:** deploy the provided `web.config`; it includes the WebP MIME mapping.
- **Homepage loads but WebP photos return 404:** check **Site > Basic Settings > Physical path** first. It must point to the extracted folder containing `web.config` and `SGSoftech.Web.dll`, not its `wwwroot` subfolder. Pointing directly at `wwwroot` bypasses the ASP.NET Core application and its WebP configuration, and also prevents the contact API from running. Correct the path, recycle only the site's pool and retest a `/Asset/Images/solutions/customers.webp` request.
- **Animation appears stopped:** the industry strip deliberately pauses while hovered, keyboard-focused, offscreen or in a hidden browser tab. Move the pointer away and keep the strip visible in the active tab. Tap/Enter/Space resumes a previously selected persistent pause; reduced-motion preferences disable animation. Section entrance animations play only once as each section enters view.
- **Contact returns 503:** check SMTP values, verified sender and outbound connectivity. Do not disable TLS to work around certificate errors.
- **Contact returns 429:** the endpoint allows five requests per IP per fifteen minutes.
- Stdout logging is disabled by default. Enable it only temporarily for diagnosis, grant write access only to a dedicated log folder, protect the logs, and turn it off afterwards.
- Before updating, back up the deployed folder and server-only configuration. Stop only this site's pool, replace the published files, preserve SMTP configuration, restart the pool and repeat the checks. Do not restart unrelated IIS sites.

The package was build-checked and smoke-tested locally. Actual IIS bindings, certificates, permissions and SMTP delivery must be verified on your server.

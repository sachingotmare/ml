# Publish Garage Manager on Google Play

Application ID: `in.sgsoftech.garagemanager`  
API: `https://android.sgsoftech.in`  
Initial app version: `1.0.0`; Android version code: `1`.

These are configuration changes, not a published release. No Google/Expo login, source upload, signing-key creation or Play submission has been performed.

## Google Play versus APK distribution

### Trial, licensing and reviewer access

Disclose the **30-day trial from first server connection** and the need for an installation-specific, time-limited license afterward in the listing and review instructions. See the [licensing guide](../licensing/README.md). License keys are activation tokens, not staff credentials or a payment implementation.

Keep the review server online and supply a safe test garage/staff account in Play Console's app-access instructions. Each review installation starts its own trial; if review exceeds it, obtain that installation's request code and issue a sufficiently long reviewer license. Test this process on internal testing before submission. Never include private signing keys or administrator credentials in reviewer instructions.

Before selling licenses or directing users to outside purchases, review the current [Google Play payments policy](https://support.google.com/googleplay/android-developer/answer/9858738) and implement any required Play Billing integration. The manual issuer is not a billing-policy exemption. Native tests must cover request-code persistence, first connection, expired access, activation/renewal, background/foreground expiry and the agreed new request code after reinstall/data clearing.

- New Google Play apps are uploaded as **signed Android App Bundles (`.aab`)** with [Play App Signing](https://developer.android.com/studio/publish/app-signing). Google generates optimized installation APKs from the bundle.
- A signed APK is useful for direct/internal installation, but it is not the requested new-app Play upload format.
- Keep the application ID permanent after first publication. Increment `expo.android.versionCode` for every subsequent uploaded release; update `expo.version` for the displayed version.

## Automated local signed build (Windows)

SDK package IDs containing semicolons are explicitly quoted for Windows batch forwarding. After installation the script checks all required SDK components, not just the license file; a zero exit code with “Package ... not found” is not accepted as successful installation. The sdkmanager deprecation warning alone is not a failure.

API 37 platforms use the published package `platforms;android-37.0`. Integer compileSdk 37 accepts an installed `platforms\android-37.0\android.jar` or the older integer-named layout. Detection requires the platform JAR, not an empty directory, and does not substitute 37.1 or preview platforms.

Use `-AndroidSdkRoot 'C:\AndroidSdk'` on Windows PowerShell 5.1 to keep SDK and extraction paths short. The installer preflights ZIP paths and required files, extracts in unique SDK-local staging, and never moves an incomplete extraction into `cmdline-tools\latest`. If a previous extraction failed with `DirectoryNotFoundException`, install using this short SDK path; do not delete unrelated SDKs or regenerate your signing key. npm dependency audit warnings are separate from archive extraction errors; do not run `npm audit fix --force` as a deployment workaround.

Use a short build checkout such as `E:\gm`, separate from the deployed API and any CA-file path used by cloudflared. The signing init script applies `-DCMAKE_OBJECT_PATH_MAX=240` to app/library CMake configurations on Windows, enabling deterministic hashed object paths below Ninja's legacy filename limits. The earlier 128 limit was smaller than the generated target directory itself, so CMake could not shorten paths safely. After a failed native build, use `-CleanPrebuild` only in the disposable build checkout to regenerate its Android project and CMake caches; custom generated-native edits are removed. Do not delete the original server project or signing keystore. This setting still requires a real signed native build to verify on your machine.

[deploy\windows\Deploy-GarageManager.ps1](../deploy/windows/Deploy-GarageManager.ps1) `-Mode BuildAndroid` performs the local build below, with no Expo/EAS or cloud upload. It reads the real project configuration (React Native's `libs.versions.toml`: currently minSdk 24, **targetSdk 36, compileSdk 37**, build-tools 37.0.0, NDK 27.1.12297006, AGP 9.2.1, Gradle wrapper 9.4.1) and refuses to continue if target is below 36 or compile below 37.

```powershell
Set-Location '<project>\deploy\windows'
.\Deploy-GarageManager.ps1 -Mode Check                      # toolchain report (read-only)
.\Deploy-GarageManager.ps1 -Mode BuildAndroid -WhatIf        # plan only; never prompts/installs
$env:GARAGE_UPLOAD_KEYSTORE = 'D:\keys\garage-upload.jks'    # outside the repository
$env:GARAGE_UPLOAD_KEY_ALIAS = 'upload'
.\Deploy-GarageManager.ps1 -Mode BuildAndroid -InstallDependencies
```

Passwords are prompted securely (or read from `GARAGE_UPLOAD_STORE_PASSWORD` / `GARAGE_UPLOAD_KEY_PASSWORD` set in your session) and exist only in the build's process environment. The key is injected by [android-signing.init.gradle](../deploy/windows/android-signing.init.gradle), which contains no secrets, forces the release build type to the upload key and fails if it would use any other (debug) signing config. Nothing is written to `mobile\android`'s Gradle files. Optional `-ExpectedCertificateSha256` pins the upload certificate registered in Play Console.

Sequence: tool detection (Node 24.13+, stable JDK 17/21/25, Android SDK) -> optional approved installs -> `expo prebuild --platform android` (`-CleanPrebuild` regenerates `mobile\android`) -> `gradlew --no-daemon :app:assembleRelease :app:bundleRelease` with `EXPO_PUBLIC_API_URL` from `mobile\.env.example` (HTTPS enforced) -> verification -> copy to `-OutputDirectory` (default `Documents\GarageManager\android-releases\<timestamp>`) with `SHA256SUMS.txt` and `build-info.json`.

Verification: both files exist and are non-empty; `apksigner verify` certificate SHA-256 equals the upload keystore's (`keytool`); `jarsigner -verify` and `keytool -printcert -jarfile` match for the AAB; the debug certificate is rejected; `aapt2 dump badging` confirms package `in.sgsoftech.garagemanager`, the `app.json` versionCode and targetSdk >= 36.

Approved installs (each requires your explicit answer): Microsoft Build of OpenJDK (`-JdkMajorToInstall`, default 17; Microsoft signature + vendor SHA-256 when reachable; needs an elevated console), Google's official command-line tools (checksum and size from Google's `repository2-3.xml`; Google publishes SHA-1 there), and SDK packages via `sdkmanager`, which shows each Android license for **you** to read and accept personally; licenses are never auto-accepted. Without those approvals the script stops with the missing item named.

Not automatable / your responsibility: creating or safeguarding the upload keystore, Play Console app creation, Play App Signing enrollment and registered upload certificate, Play policy forms, store listing, testing tracks and review, accounts, and public privacy policy hosting. Release builds remain unverified on a device until you test them (the AAB's package/version are checked via the APK, not bundletool). Customer-facing parts/accessories service tracking has no customer login: the owner shares status via WhatsApp from the app.
## Build locally on Windows (no Expo cloud upload)

Use a development/build workstation with Android Studio, Android SDK and the JDK required by the installed React Native/Gradle release. IIS and PostgreSQL are not required on that workstation. No native build tools need to be installed on the production API server.

```powershell
Set-Location 'C:\GitRepo\ml\Garage-Anroid-Application'
npm ci
npm run check
npm run build
npm test
Copy-Item '.\mobile\.env.example' '.\mobile\.env'
Set-Location '.\mobile'
npx expo prebuild --platform android
```

Do not overwrite an existing private `.env`. The example contains the public HTTPS API URL only. Local builds use it; [eas.json](eas.json)'s `env` applies only to EAS build profiles.

Open the generated [android](android) project in Android Studio. **Configure a release signing configuration using your upload key** through your approved Android signing process. The generated Gradle release may initially use the development debug key; that is not a production signing setup. Use a strong protected upload keystore stored outside source control and injected signing passwords, and verify that the release uses this key, not `debug.keystore`.

Do not commit private signing passwords or keystore files. Expo prebuild can regenerate native files, so preserve approved signing configuration outside generated files or through a reviewed config plugin/build procedure.

After configuring signing:

```powershell
Set-Location 'C:\GitRepo\ml\Garage-Anroid-Application\mobile\android'
.\gradlew.bat :app:bundleRelease
```

Expected bundle: `app\build\outputs\bundle\release\app-release.aab`. Inspect the bundle's package ID, version code, target SDK and upload certificate before submission. Test the release using Play internal testing or a verified bundletool procedure; an Android JavaScript export alone does not validate native code.

For a directly installable signed release APK using the same configured signing key:

```powershell
.\gradlew.bat :app:assembleRelease
```

Expected APK: `app\build\outputs\apk\release\app-release.apk`. Google Play's app signing key may differ from your upload key, so a locally signed APK may not be installable over a Play-installed copy. Manage test distribution deliberately.

## Optional Expo EAS build

Use only if you approve uploading this project to Expo and have an Expo account. Your Google developer account alone is insufficient for EAS.

```powershell
Set-Location 'C:\GitRepo\ml\Garage-Anroid-Application\mobile'
npx eas-cli login
npx eas-cli build:configure
npx eas-cli build --platform android --profile production
```

Follow the prompts to associate an actual Expo project and configure the Android upload keystore. No project UUID or signing key is invented by this repository. Back up your key through your approved secure process.

The `production` profile produces an AAB. For an internal APK:

```powershell
npx eas-cli build --platform android --profile preview
```

Download the artifact only after confirming the build result. Inspect and test before uploading to Play.

## Play Console checklist

1. Create your app with the agreed application ID, English default language and suitable category.
2. Configure Play App Signing and record the upload certificate.
3. Start with an **internal testing** release. Upload the verified signed AAB; resolve all Play validation errors.
4. Supply app name, descriptions, high-resolution icon, actual device screenshots, support contact and an accurate public privacy policy.
5. Complete content rating, target audience, ads declaration and Data safety based on actual behavior. This app stores customer names/phone numbers, bikes/service history, staff identity and financial records on your server; opted-in phone numbers and template variables are sent to your custom WhatsApp gateway. Do not claim “no data collected” without policy review.
6. Provide “App access” reviewer instructions and a limited test account against a dedicated review environment or safe sample records. Do not give reviewers a production owner password or expose actual customer records. The app has no public registration.
7. Review Google Play's account/data deletion requirements for your deployment and provide the required mechanisms/contact/URLs if applicable. Owner-managed staff accounts do not justify skipping policy review.
8. Verify native permissions and every bundled native library's current platform requirements, including [16 KB page-size support](https://developer.android.com/guide/practices/page-sizes). App-level permission blocks do not replace inspecting the final merged manifest.
9. Check the [current target API policy](https://support.google.com/googleplay/android-developer/answer/11926878?hl=en). As verified November 1, 2026, new mobile apps must target **Android 16 / API 36 or higher**. Check the final bundle, not just the Expo SDK version.
10. If you have a personal developer account created after November 13, 2023, [Google's testing requirements](https://support.google.com/googleplay/android-developer/answer/14151465?hl=en) require a closed test with at least 12 opted-in testers continuously for 14 days before applying for production access. Your Console determines which requirements apply.
11. Complete real-device, screen-reader/large-text, IIS connection, concurrent database writes, backup recovery and WhatsApp gateway testing. Resolve or formally assess documented dependency advisories before release.
12. Submit for review and monitor policy/technical results; a developer account does not guarantee approval.

The API domain currently serves JSON only. A privacy policy or support website must be hosted separately or deliberately added as a secure static site; publishing this guide does not create those public pages.

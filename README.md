# LectureFlow — Android App (TWA)

The Android app for [LectureFlow](https://lf.kiaashkan.workers.dev/), built as a
**Trusted Web Activity (TWA)**: a thin, official Google shell around the
LectureFlow web app (PWA). The app contains no duplicated site logic — it opens
the live website full-screen, so **every site update is instantly the app
update**. One codebase, one deploy.

- Package: `ir.kiaashkan.lectureflow`
- Version: 1.0.1 (versionCode 2)
- Min Android: 5.0 (API 21)
- Generated with [Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap)
  from the site's web app manifest; configuration lives in `twa-manifest.json`.

## Full-screen requirement (Digital Asset Links)

For the app to open without a browser URL bar, the site must serve
`/.well-known/assetlinks.json` linking the domain to this app's signing key.
That endpoint was added to the LectureFlow worker in **v3.9.2** with the
SHA-256 fingerprint of the release certificate:

```
CD:CF:5E:C4:01:1E:15:88:BC:3A:16:17:F4:D1:15:89:D3:79:3F:E1:C8:1B:85:DC:ED:A9:1F:42:9B:B5:9E:3A
```

If the signing key is ever replaced, the fingerprint in the worker (and in
this app) must be updated to match, or the app falls back to a Custom Tab.

## Signing key

The release keystore is **not** in this repo. It lives outside the project
(KiA's keys folder, alias `lectureflow`, cert CN=KiA, O=LectureFlow) — the same
pattern as EditNote. Never commit a keystore.

## Building

Normal route (any machine with JDK 17 + Android SDK):

```bash
npm i -g @bubblewrap/cli
bubblewrap build        # reads twa-manifest.json, produces signed APK + AAB
```

The v1.0.0 release APK was assembled with the manual pipeline in
`manual-build/` (`build_manual.py`: aapt2 + javac + d8 + apksigner, with
`resolve_deps.py` fetching the AndroidX dependency graph) because the build
VM's Gradle daemon could not run. The output is a standard release APK,
verified with `apksigner verify` (cert fingerprint above).

## Note for users upgrading from the old (pre-2026) app

The old LectureFlow app was signed with a different key, so Android will
refuse to install this one over it. Uninstall the old app first, then install
this APK.

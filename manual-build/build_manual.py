#!/usr/bin/env python3
"""Manual TWA APK build (no Gradle — Gradle's daemon IPC is broken in this VM).

Pipeline: extract AARs -> merge manifests -> aapt2 compile/link (final R ids)
-> per-library R.java from link symbols -> javac -> d8 -> add dex + jar
resources -> zipalign -> apksigner. Mirrors what AGP would do for this app.
"""
import os
import re
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = os.path.expanduser('~/workspace/lectureflow-app')
MB = os.path.join(ROOT, 'manual-build')
DEPS = os.path.join(MB, 'deps')
WORK = os.path.join(MB, 'work')
BT = os.path.expanduser('~/android-sdk/build-tools/36.1.0')
AJAR = os.path.expanduser('~/android-sdk/platforms/android-36/android.jar')
JDK = os.path.expanduser('~/tools/jdk-17/bin')
KS = os.path.expanduser('~/workspace/lectureflow-keys/release.keystore')
PWFILE = os.path.expanduser('~/workspace/lectureflow-keys/password.txt')
PKG = 'ir.kiaashkan.lectureflow'
ANDROID = '{http://schemas.android.com/apk/res/android}'

shutil.rmtree(WORK, ignore_errors=True)
for d in ('aars', 'compiled', 'gen', 'classes', 'dex', 'staging'):
    os.makedirs(os.path.join(WORK, d))


JAVA_ENV = dict(os.environ, PATH=os.path.expanduser('~/tools/jdk-17/bin') + ':' + os.environ.get('PATH', ''))


def run(cmd, **kw):
    print('+', ' '.join(cmd[:3]), '...' if len(cmd) > 3 else '')
    kw.setdefault('env', JAVA_ENV)
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stdout[-3000:]); print(r.stderr[-3000:])
        sys.exit(f'FAILED: {cmd[0]}')
    return r


# ---------- 0. generated resources Bubblewrap/Gradle would produce ----------
# resValue entries from app/build.gradle + generator images (splash,
# notification icons, maskable at Bubblewrap's sizes, raw web manifest).
from PIL import Image
RES = os.path.join(ROOT, 'app/src/main/res')
os.makedirs(os.path.join(RES, 'values'), exist_ok=True)
with open(os.path.join(RES, 'values', 'generated.xml'), 'w') as fh:
    fh.write('''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="appName">LectureFlow</string>
    <string name="launcherName">LectureFlow</string>
    <string name="launchUrl">https://lf.kiaashkan.workers.dev/</string>
    <string name="webManifestUrl">https://lf.kiaashkan.workers.dev/manifest.webmanifest</string>
    <string name="fullScopeUrl">https://lf.kiaashkan.workers.dev/</string>
    <string name="hostName">lf.kiaashkan.workers.dev</string>
    <color name="colorPrimary">#FAF8F4</color>
    <color name="colorPrimaryDark">#100E0C</color>
    <color name="navigationColor">#FAF8F4</color>
    <color name="navigationColorDark">#100E0C</color>
    <color name="navigationDividerColor">#000000</color>
    <color name="navigationDividerColorDark">#000000</color>
    <color name="backgroundColor">#FAF8F4</color>
    <string name="providerAuthority">ir.kiaashkan.lectureflow.fileprovider</string>
    <bool name="enableNotification">true</bool>
    <integer name="splashScreenFadeOutDuration">300</integer>
    <string name="generatorApp">bubblewrap-cli</string>
    <string name="fallbackType">customtabs</string>
    <bool name="enableSiteSettingsShortcut">true</bool>
    <string name="orientation">portrait</string>
</resources>
''')
os.makedirs(os.path.join(RES, 'values-night'), exist_ok=True)
with open(os.path.join(RES, 'values-night', 'generated.xml'), 'w') as fh:
    fh.write('''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="backgroundColor">#100E0C</color>
</resources>
''')
ICONS = os.path.join(ROOT, 'icons')
icon_any = Image.open(os.path.join(ICONS, 'icon-512.png')).convert('RGBA')
icon_mask = Image.open(os.path.join(ICONS, 'icon-maskable-512.png')).convert('RGBA')
icon_dark = Image.open(os.path.join(ICONS, 'icon-dark-512.png')).convert('RGBA')
BG = (0xFA, 0xF8, 0xF4, 255)
for d, s in [('drawable-mdpi', 300), ('drawable-hdpi', 450), ('drawable-xhdpi', 600),
             ('drawable-xxhdpi', 900), ('drawable-xxxhdpi', 1200)]:
    os.makedirs(os.path.join(RES, d), exist_ok=True)
    canvas = Image.new('RGBA', (s, s), BG)
    canvas.alpha_composite(icon_any.resize((s, s), Image.LANCZOS))
    canvas.save(os.path.join(RES, d, 'splash.png'))
BGD = (0x10, 0x0E, 0x0C, 255)
for d, s in [('drawable-night-mdpi', 300), ('drawable-night-hdpi', 450), ('drawable-night-xhdpi', 600),
             ('drawable-night-xxhdpi', 900), ('drawable-night-xxxhdpi', 1200)]:
    os.makedirs(os.path.join(RES, d), exist_ok=True)
    canvas = Image.new('RGBA', (s, s), BGD)
    canvas.alpha_composite(icon_dark.resize((s, s), Image.LANCZOS))
    canvas.save(os.path.join(RES, d, 'splash.png'))
for d, s in [('mipmap-mdpi', 82), ('mipmap-hdpi', 123), ('mipmap-xhdpi', 164),
             ('mipmap-xxhdpi', 246), ('mipmap-xxxhdpi', 328)]:
    icon_mask.resize((s, s), Image.LANCZOS).save(os.path.join(RES, d, 'ic_maskable.png'))
for d, s in [('mipmap-mdpi', 48), ('mipmap-hdpi', 72), ('mipmap-xhdpi', 96),
             ('mipmap-xxhdpi', 144), ('mipmap-xxxhdpi', 192)]:
    icon_any.resize((s, s), Image.LANCZOS).save(os.path.join(RES, d, 'ic_launcher.png'))
alpha = icon_any.split()[3]
for d, s in [('drawable-mdpi', 24), ('drawable-hdpi', 36), ('drawable-xhdpi', 48),
             ('drawable-xxhdpi', 72), ('drawable-xxxhdpi', 96)]:
    sil = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    sil.paste(Image.new('RGBA', (s, s), (255, 255, 255, 255)),
              (0, 0), alpha.resize((s, s), Image.LANCZOS))
    sil.save(os.path.join(RES, d, 'ic_notification_icon.png'))
os.makedirs(os.path.join(RES, 'raw'), exist_ok=True)
shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webmanifest.json'), os.path.join(RES, 'raw', 'web_app_manifest.json'))
print('generated resources written')

# ---------- 1. extract AARs ----------
aars = []  # (name, dir, classes_jar, package)
plain_jars = []
for f in sorted(os.listdir(DEPS)):
    p = os.path.join(DEPS, f)
    if f.endswith('.aar'):
        dest = os.path.join(WORK, 'aars', f[:-4])
        with zipfile.ZipFile(p) as z:
            z.extractall(dest)
        man = ET.parse(os.path.join(dest, 'AndroidManifest.xml')).getroot()
        aars.append((f, dest, os.path.join(dest, 'classes.jar'), man.get('package')))
    elif f.endswith('.jar'):
        plain_jars.append(p)
print(f'{len(aars)} AARs, {len(plain_jars)} plain jars')

# ---------- 2. merge manifests ----------
ET.register_namespace('android', 'http://schemas.android.com/apk/res/android')
app_man_path = os.path.join(ROOT, 'app/src/main/AndroidManifest.xml')
tree = ET.parse(app_man_path)
root = tree.getroot()
app_el = root.find('application')
existing = {c.get(ANDROID + 'name'): c for c in app_el if c.get(ANDROID + 'name')}
have_perms = {c.get(ANDROID + 'name') for c in root.findall('uses-permission')}
for (_, dest, _, _) in aars:
    lm = ET.parse(os.path.join(dest, 'AndroidManifest.xml')).getroot()
    # AGP substitutes ${applicationId} in library manifests; do the same.
    for el in lm.iter():
        for k, v in list(el.attrib.items()):
            if '${applicationId}' in v:
                el.set(k, v.replace('${applicationId}', PKG))
    for child in lm:
        if child.tag == 'uses-permission':
            n = child.get(ANDROID + 'name')
            if n not in have_perms:
                root.insert(0, child); have_perms.add(n)
        elif child.tag == 'application':
            for comp in child:
                n = comp.get(ANDROID + 'name')
                if not n:
                    continue
                if n not in existing:
                    app_el.append(comp); existing[n] = comp
                else:
                    # Same component declared by several libraries (e.g.
                    # androidx.startup.InitializationProvider): AGP unions
                    # their children. Merge meta-data by name, append the
                    # rest — dropping them loses required initializers and
                    # crashes the app at startup (v1.0.0/v1.0.1 bug).
                    target = existing[n]
                    have_md = {m.get(ANDROID + 'name')
                               for m in target.findall('meta-data')}
                    for sub in comp:
                        if sub.tag == 'meta-data':
                            mn = sub.get(ANDROID + 'name')
                            if mn not in have_md:
                                target.append(sub); have_md.add(mn)
                        else:
                            target.append(sub)
# androidx.startup ordering hazard (the v1.0.0–v1.0.2 startup crash):
# AppInitializer discovers initializers by iterating the provider's
# meta-data and initializes each on the spot. EmojiCompatInitializer
# depends on ProcessLifecycleInitializer, but discovery reaches Emoji
# first, so ProcessLifecycle gets created as a mere dependency before
# its own discovery — and its create() refuses lazy initialization
# (IllegalStateException: "ProcessLifecycleInitializer cannot be
# initialized lazily"). The TWA shell renders no native text, so
# EmojiCompat auto-init is dead weight here: drop its meta-data (the
# manual-build equivalent of tools:node="remove") and put
# ProcessLifecycleInitializer first among what remains.
for comp in app_el:
    if comp.get(ANDROID + 'name') == 'androidx.startup.InitializationProvider':
        for md in list(comp.findall('meta-data')):
            if md.get(ANDROID + 'name') == 'androidx.emoji2.text.EmojiCompatInitializer':
                comp.remove(md)
        mds = comp.findall('meta-data')
        mds.sort(key=lambda m: 0 if m.get(ANDROID + 'name') ==
                 'androidx.lifecycle.ProcessLifecycleInitializer' else 1)
        for md in mds:
            comp.remove(md)
        for md in mds:
            comp.append(md)
merged = os.path.join(WORK, 'AndroidManifest.xml')
tree.write(merged, encoding='utf-8', xml_declaration=True)
print('manifest merged; components:', len(existing))

# ---------- 3. aapt2 compile + link ----------
flats = []
res_dirs = [(os.path.join(ROOT, 'app/src/main/res'), 'app')]
for (f, dest, _, _) in aars:
    rd = os.path.join(dest, 'res')
    if os.path.isdir(rd) and os.listdir(rd):
        res_dirs.append((rd, f))
for rd, name in res_dirs:
    out = os.path.join(WORK, 'compiled', name + '.zip')
    run([os.path.join(BT, 'aapt2'), 'compile', '--dir', rd, '-o', out])
    flats.append(out)
symbols = os.path.join(WORK, 'symbols.txt')
gen_dir = os.path.join(WORK, 'gen')
base_apk = os.path.join(WORK, 'base.apk')
cmd = [os.path.join(BT, 'aapt2'), 'link', '-o', base_apk, '-I', AJAR,
       '--manifest', merged, '--java', gen_dir, '--output-text-symbols', symbols,
       '--auto-add-overlay', '--min-sdk-version', '21', '--target-sdk-version', '36',
       '--version-code', '7', '--version-name', '1.0.6']
for fl in flats:
    cmd += ['-R', fl]
run(cmd)
print('aapt2 link OK')

# ---------- 4. per-library R.java ----------
sym = {}
styleables = {}
for line in open(symbols):
    line = line.strip()
    m = re.match(r'int (\w+) (\S+) (0x[0-9a-fA-F]+)$', line)
    if m:
        sym[(m.group(1), m.group(2))] = m.group(3)
        continue
    m = re.match(r'int\[\] styleable (\S+) \{ (.*) \}$', line)
    if m:
        styleables[m.group(1)] = m.group(2)

r_sources = []
for (f, dest, _, pkg) in aars:
    rtxt = os.path.join(dest, 'R.txt')
    if not os.path.exists(rtxt) or not pkg:
        continue
    fields = {}
    for line in open(rtxt):
        parts = line.split()
        if len(parts) < 4:
            continue
        typ, name = parts[1], parts[2]
        if parts[0] == 'int' and (typ, name) in sym:
            fields.setdefault(typ, []).append((name, sym[(typ, name)]))
        elif parts[0] == 'int[]' and typ == 'styleable' and name in styleables:
            fields.setdefault('styleable_arr', []).append((name, styleables[name]))
            # styleable index ints are in sym as ('styleable', Name_attr)
            for (t2, n2), val in sym.items():
                if t2 == 'styleable' and n2.startswith(name + '_'):
                    fields.setdefault('styleable', []).append((n2, val))
    if not fields:
        continue
    out_dir = os.path.join(gen_dir, *pkg.split('.'))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, 'R.java')
    with open(out, 'w') as fh:
        fh.write(f'package {pkg};\npublic final class R {{\n')
        for typ, entries in fields.items():
            cls = 'styleable' if typ in ('styleable_arr', 'styleable') else typ
            fh.write(f'  public static final class {cls} {{\n')
            for name, val in entries:
                if typ == 'styleable_arr':
                    fh.write(f'    public static final int[] {name} = new int[] {{ {val} }};\n')
                else:
                    fh.write(f'    public static final int {name} = {val};\n')
            fh.write('  }\n')
        fh.write('}\n')
    r_sources.append(out)
print(f'{len(r_sources)} library R.java generated')

# ---------- 5. javac ----------
all_jars = [cj for (_, _, cj, _) in aars if os.path.exists(cj)] + plain_jars
cp = ':'.join([AJAR] + all_jars)
sources = []
for dp, _, fns in os.walk(os.path.join(ROOT, 'app/src/main/java')):
    sources += [os.path.join(dp, f) for f in fns if f.endswith('.java')]
for dp, _, fns in os.walk(gen_dir):
    sources += [os.path.join(dp, f) for f in fns if f.endswith('.java')]
classes_dir = os.path.join(WORK, 'classes')
run([os.path.join(JDK, 'javac'), '-source', '11', '-target', '11', '-nowarn',
     '-cp', cp, '-d', classes_dir] + sources)
print(f'javac OK ({len(sources)} sources)')

# ---------- 6. dedupe check + d8 ----------
def jar_classes(j):
    with zipfile.ZipFile(j) as z:
        return {n for n in z.namelist() if n.endswith('.class')}
owner = {}
dup_jars = []
for j in all_jars:
    cls = jar_classes(j)
    overlap = cls & set(owner)
    if cls and len(overlap) == len(cls):
        dup_jars.append(j)
        print('fully duplicated jar dropped:', os.path.basename(j))
    else:
        if overlap:
            print(f'partial dup in {os.path.basename(j)}: {len(overlap)} classes (d8 will keep first)')
        for c in cls:
            owner.setdefault(c, j)
dex_jars = [j for j in all_jars if j not in dup_jars]
# R8 in build-tools 36.1 rejects a bare directory as program input; jar it.
app_jar = os.path.join(WORK, 'app-classes.jar')
with zipfile.ZipFile(app_jar, 'w', zipfile.ZIP_DEFLATED) as z:
    for dp, _, fns in os.walk(classes_dir):
        for fn in fns:
            src = os.path.join(dp, fn)
            z.write(src, os.path.relpath(src, classes_dir))
dex_dir = os.path.join(WORK, 'dex')
run([os.path.join(BT, 'd8'), '--min-api', '21', '--lib', AJAR,
     '--output', dex_dir, app_jar] + dex_jars)
print('d8 OK:', sorted(os.listdir(dex_dir)))

# ---------- 7. stage jar resources + assemble ----------
staging = os.path.join(WORK, 'staging')
for j in dex_jars:
    with zipfile.ZipFile(j) as z:
        for n in z.namelist():
            if n.endswith('.class') or n.endswith('/') or n == 'META-INF/MANIFEST.MF' \
               or re.match(r'META-INF/.*\.(SF|RSA|DSA)$', n):
                continue
            target = os.path.join(staging, n)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            open(target, 'wb').write(z.read(n))
for (_, dest, _, _) in aars:
    assets = os.path.join(dest, 'assets')
    if os.path.isdir(assets):
        for dp, _, fns in os.walk(assets):
            for fn in fns:
                src = os.path.join(dp, fn)
                rel = os.path.relpath(src, dest)
                tgt = os.path.join(staging, rel)
                os.makedirs(os.path.dirname(tgt), exist_ok=True)
                shutil.copy(src, tgt)
unsigned = os.path.join(WORK, 'unsigned.apk')
shutil.copy(base_apk, unsigned)
with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(dex_dir)):
        z.write(os.path.join(dex_dir, f), f)
    for dp, _, fns in os.walk(staging):
        for fn in fns:
            src = os.path.join(dp, fn)
            z.write(src, os.path.relpath(src, staging))
print('unsigned apk assembled')

# ---------- 8. align + sign ----------
aligned = os.path.join(WORK, 'aligned.apk')
run([os.path.join(BT, 'zipalign'), '-f', '-p', '4', unsigned, aligned])
# apksigner reads ks-pass from line 1 and key-pass from line 2 of a file:
# source, so give it a two-line file derived from the one-line password.txt.
pw = open(PWFILE).read().strip()
signpass = os.path.join(WORK, 'signpass.txt')
open(signpass, 'w').write(pw + '\n' + pw + '\n')
final = os.path.join(ROOT, 'LectureFlow-v1.0.6.apk')
run([os.path.join(BT, 'apksigner'), 'sign', '--ks', KS,
     '--ks-pass', f'file:{signpass}', '--key-pass', f'file:{signpass}',
     '--ks-key-alias', 'lectureflow', '--out', final, aligned])
print('SIGNED:', final, os.path.getsize(final), 'bytes')

#!/usr/bin/env python3
"""Minimal Maven dependency resolver (Python + requests via env proxy).

Resolves the runtime graph of com.google.androidbrowserhelper 2.7.4 from
Google Maven / Maven Central and downloads .aar/.jar files into deps/.
Implements: parent POM inheritance, properties, dependencyManagement
(incl. BOM imports), scope/optional filtering, exclusions, nearest-wins.
Good enough for well-behaved AndroidX/Google graphs.
"""
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import deque

import requests

NS = {'m': 'http://maven.apache.org/POM/4.0.0'}
GOOGLE = 'https://dl.google.com/dl/android/maven2'
CENTRAL = 'https://repo.maven.apache.org/maven2'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deps')
os.makedirs(OUT, exist_ok=True)
S = requests.Session()

_pom_cache = {}


def repo_for(group):
    if group.startswith(('androidx.', 'com.google.', 'com.android', 'org.tensorflow')):
        return GOOGLE
    return CENTRAL


def pom_url(g, a, v):
    return f"{repo_for(g)}/{g.replace('.', '/')}/{a}/{v}/{a}-{v}.pom"


def fetch_pom(g, a, v):
    key = (g, a, v)
    if key in _pom_cache:
        return _pom_cache[key]
    url = pom_url(g, a, v)
    r = None
    for attempt in range(5):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 200:
                break
        except Exception:
            r = None
    if (r is None or r.status_code != 200) and repo_for(g) == GOOGLE:
        r = S.get(f"{CENTRAL}/{g.replace('.', '/')}/{a}/{v}/{a}-{v}.pom", timeout=60)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    _pom_cache[key] = root
    return root


def text(el, path):
    n = el.find(path, NS)
    return n.text.strip() if n is not None and n.text else None


def interp(s, props, depth=0):
    if s is None or depth > 10:
        return s
    def rep(m):
        return props.get(m.group(1), m.group(0))
    out = re.sub(r'\$\{([^}]+)\}', rep, s)
    return interp(out, props, depth + 1) if '${' in out else out


class Pom:
    def __init__(self, g, a, v):
        self.g, self.a, self.v = g, a, v
        root = fetch_pom(g, a, v)
        self.root = root
        parent = root.find('m:parent', NS)
        self.parent = None
        if parent is not None:
            pg = text(parent, 'm:groupId'); pa = text(parent, 'm:artifactId'); pv = text(parent, 'm:version')
            self.parent = Pom(pg, pa, pv)
        self.props = dict(self.parent.props) if self.parent else {}
        self.props.update({
            'project.groupId': g, 'pom.groupId': g, 'project.artifactId': a,
            'project.version': v, 'pom.version': v, 'project.parent.version':
                self.parent.v if self.parent else v,
        })
        pel = root.find('m:properties', NS)
        if pel is not None:
            for child in pel:
                tag = child.tag.split('}')[-1]
                self.props[tag] = child.text or ''
        # resolve property values that reference other properties
        for k in list(self.props):
            self.props[k] = interp(self.props[k], self.props)
        self.dep_mgmt = dict(self.parent.dep_mgmt) if self.parent else {}
        self._load_dep_mgmt(root)
        self.packaging = text(root, 'm:packaging') or 'jar'

    def _load_dep_mgmt(self, root):
        dm = root.find('m:dependencyManagement/m:dependencies', NS)
        if dm is None:
            return
        for dep in dm.findall('m:dependency', NS):
            g = interp(text(dep, 'm:groupId'), self.props)
            a = interp(text(dep, 'm:artifactId'), self.props)
            v = interp(text(dep, 'm:version'), self.props)
            scope = text(dep, 'm:scope')
            typ = text(dep, 'm:type') or 'jar'
            if scope == 'import' and typ == 'pom':
                bom = Pom(g, a, v)
                for k, val in bom.dep_mgmt.items():
                    self.dep_mgmt.setdefault(k, val)
            elif v:
                self.dep_mgmt[(g, a)] = v

    def dependencies(self):
        deps = []
        # parent's dependencies are inherited too
        if self.parent:
            deps.extend(self.parent.dependencies())
        dl = self.root.find('m:dependencies', NS)
        if dl is None:
            return deps
        for dep in dl.findall('m:dependency', NS):
            g = interp(text(dep, 'm:groupId'), self.props)
            a = interp(text(dep, 'm:artifactId'), self.props)
            v = interp(text(dep, 'm:version'), self.props) or self.dep_mgmt.get((g, a))
            scope = text(dep, 'm:scope') or 'compile'
            optional = text(dep, 'm:optional') == 'true'
            typ = text(dep, 'm:type') or 'jar'
            excl = set()
            ex = dep.find('m:exclusions', NS)
            if ex is not None:
                for e in ex.findall('m:exclusion', NS):
                    excl.add((text(e, 'm:groupId'), text(e, 'm:artifactId')))
            deps.append((g, a, v, scope, optional, typ, excl))
        return deps


def resolve(roots):
    seen = {}          # (g,a) -> version (nearest wins = first BFS hit)
    order = []
    q = deque()
    for (g, a, v) in roots:
        q.append((g, a, v, frozenset()))
    while q:
        g, a, v, excl = q.popleft()
        if (g, a) in seen or (g, a) in excl:
            continue
        if v is None:
            print(f'WARN: no version for {g}:{a}, skipped')
            continue
        v = v.strip('[]()')
        if ',' in v:  # version range: take upper-ish bound (last listed)
            v = v.split(',')[-1].strip('[]() ')
        seen[(g, a)] = v
        order.append((g, a, v))
        try:
            pom = Pom(g, a, v)
        except Exception as e:
            print(f'WARN: POM fetch failed {g}:{a}:{v}: {e}')
            continue
        for (dg, da, dv, scope, optional, typ, dexcl) in pom.dependencies():
            if scope in ('test', 'provided') or optional:
                continue
            q.append((dg, da, dv, excl | dexcl))
    return order


def download(order):
    files = []
    for (g, a, v) in order:
        try:
            pom = Pom(g, a, v)
            packaging = pom.packaging
        except Exception:
            packaging = 'jar'
        if packaging == 'pom':
            print(f'{g}:{a}:{v} -> (pom only, skipped)')
            continue
        ext = 'aar' if packaging == 'aar' else 'jar'
        name = f'{a}-{v}.{ext}'
        path = os.path.join(OUT, name)
        if not os.path.exists(path):
            url = f"{repo_for(g)}/{g.replace('.', '/')}/{a}/{v}/{name}"
            r = S.get(url, timeout=120)
            if r.status_code != 200:
                url = f"{CENTRAL}/{g.replace('.', '/')}/{a}/{v}/{name}"
                r = S.get(url, timeout=120)
            r.raise_for_status()
            open(path, 'wb').write(r.content)
        files.append(name)
        print(f'{g}:{a}:{v} -> {name} ({os.path.getsize(path)} B)')
    return files


if __name__ == '__main__':
    order = resolve([('com.google.androidbrowserhelper', 'androidbrowserhelper', '2.7.4')])
    print(f'--- {len(order)} artifacts')
    download(order)

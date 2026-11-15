#!/usr/bin/env python3
"""Drive Bubblewrap CLI prompts non-interactively (pexpect).

Usage: bw_drive.py <logfile> <command...>
Answers Bubblewrap's init/build questions with the LectureFlow choices;
everything else accepts the CLI default. The keystore password is read
from ~/workspace/lectureflow-keys/password.txt inside this script, so it
never appears on a command line.
"""
import re
import sys

import pexpect

PW = open('/home/hatch/workspace/lectureflow-keys/password.txt').read().strip()
KS_PATH = '/home/hatch/workspace/lectureflow-keys/release.keystore'
PKG = 'ir.kiaashkan.lectureflow'

log = open(sys.argv[1], 'w', encoding='utf-8')
cmd = sys.argv[2:]
child = pexpect.spawn(cmd[0], cmd[1:], encoding='utf-8', timeout=900, maxread=65536)
child.logfile_read = log

RULES = [
    (r'regenerate your project', 'n'),
    (r'versionName for the new App version', '1.0.0'),
    (r'install the JDK', 'n'),
    (r'install the Android SDK', 'n'),
    (r'Path to your existing JDK', '/home/hatch/tools/jdk-17'),
    (r'Path to your existing Android SDK', '/home/hatch/android-sdk'),
    (r'[Pp]ackage (ID|id|name)', PKG),
    (r'[Ss]igning [Kk]ey path|[Kk]eystore path|path to.*(key|store)', KS_PATH),
    (r'[Kk]ey alias|alias for the key', 'lectureflow'),
    (r'[Pp]assword', PW),
    (r'\(y/N\)', 'n'),
    (r'\(Y/n\)', 'y'),
    (r'[:?)]\s*$', ''),
]
PATTERNS = [r[0] for r in RULES] + [pexpect.EOF, pexpect.TIMEOUT]

answered = 0
while True:
    i = child.expect(PATTERNS, timeout=900)
    if i == len(RULES):  # EOF
        break
    if i == len(RULES) + 1:  # TIMEOUT
        print('DRIVER TIMEOUT; last output tail:')
        print((child.before or '')[-2000:])
        child.close(force=True)
        sys.exit(2)
    child.sendline(RULES[i][1])
    answered += 1
    if answered > 120:
        print('DRIVER: too many prompts, aborting')
        child.close(force=True)
        sys.exit(3)

child.close()
print('DRIVER DONE, prompts answered:', answered, 'exit:', child.exitstatus)
sys.exit(child.exitstatus or 0)

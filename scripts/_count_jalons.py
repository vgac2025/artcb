#!/usr/bin/env python3
"""Compte et liste les jalons ROADMAP_GENERAL_ARTCB."""
import re, sys
from pathlib import Path

roadmap = Path("ROADMAP_GENERAL_ARTCB").read_text(encoding="utf-8")
lines   = roadmap.split("\n")

done    = [l for l in lines if "[x]" in l]
todo    = [l for l in lines if "[ ]" in l]
inprog  = [l for l in lines if "[-]" in l]
total   = len(done) + len(todo) + len(inprog)
pct     = round(len(done) / total * 100, 1) if total else 0

print(f"[x] FAIT     : {len(done)}")
print(f"[ ] À FAIRE  : {len(todo)}")
print(f"[-] EN COURS : {len(inprog)}")
print(f"TOTAL jalons : {total}")
print(f"AVANCEMENT   : {pct}%")

print("\n=== JALONS À FAIRE ([ ] et [-]) ===")
for l in todo + inprog:
    print(" ", l.strip())

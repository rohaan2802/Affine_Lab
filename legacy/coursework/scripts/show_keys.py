"""Show only recovered numeric keys during a demo, never credentials."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
rows = json.loads((root/'output/recovered_keys.json').read_text())
print('Session  a   b   inverse(a)')
for row in rows:
    print(f"{row['session']:>7} {row['a']:>3} {row['b']:>3} {row['a_inverse']:>12}")

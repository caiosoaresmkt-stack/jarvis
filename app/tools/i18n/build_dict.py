"""Gera frontend/src/i18n/pt-BR.json a partir de strings.en.json + pt*.tsv (indexados)."""
import json, pathlib, sys
here = pathlib.Path(__file__).parent
en = json.loads((here / "strings.en.json").read_text(encoding="utf8"))
out, bad = {}, []
for tsv in sorted(here.glob("pt*.tsv")):
    for ln, line in enumerate(tsv.read_text(encoding="utf8").splitlines(), 1):
        if not line.strip():
            continue
        idx, _, pt = line.partition("\t")
        i = int(idx)
        key = en[i][0]
        if key.count("{}") != len(set(__import__("re").findall(r"\{(\d*)\}", pt)) ) and key.count("{}") != pt.count("{}"):
            bad.append((tsv.name, ln, key, pt))
        if key != pt:
            out[key] = pt
# extras escritos à mão (strings que o extrator não pega)
extras = here / "extras.json"
if extras.exists():
    out.update(json.loads(extras.read_text(encoding="utf8")))
dest = here.parent.parent / "frontend/src/i18n/pt-BR.json"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf8")
print(len(out), "traduções ->", dest)
if bad:
    print("AVISO placeholders {} divergentes:")
    for b in bad: print(" ", b)
missing = [i for i,(k,_) in enumerate(en) if k not in out]
print(len(missing), "sem tradução (idênticas/marca/código)")

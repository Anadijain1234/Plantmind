"""Build data/packs/*.json (one file per industry) from scripts/packs_src. Run after process_public_data.py."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from packs_src import factory, garage, healthcare, it, restaurant  # noqa: E402
from packs_src.common import add_credits  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "data" / "packs"
OUT.mkdir(parents=True, exist_ok=True)
for mod in (factory, restaurant, healthcare, garage, it):
    pack = add_credits(mod.build())
    ids = [a["id"] for a in pack["assets"]]
    for r in pack["records"]:
        assert r["asset_id"] in ids, (pack["id"], r["id"])
        assert any(p["id"] == r["person_id"] for p in pack["people"]), (pack["id"], r["id"])
    for t in pack["tips"]:
        assert t["asset_id"] in ids + ["ALL"], (pack["id"], t["id"])
    (OUT / f"{pack['id']}.json").write_text(json.dumps(pack, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{pack['id']:<11} assets={len(pack['assets']):>2} people={len(pack['people'])} records={len(pack['records']):>2} "
          f"tips={len(pack['tips']):>2} public={len(pack['public']):>3} credits={sum(1 for r in pack['records'] if r.get('credited_to'))}")

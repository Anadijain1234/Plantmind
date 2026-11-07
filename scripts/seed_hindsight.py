"""
Load all starter memories into Hindsight Cloud — one memory bank per industry.

  python scripts/seed_hindsight.py            # all industries
  python scripts/seed_hindsight.py factory    # just one
  python scripts/seed_hindsight.py --dry-run  # count memories + estimated cost, no API calls

Needs HINDSIGHT_API_KEY in the environment (or in a local .env file). Safe to run twice:
memories use stable document ids, so a re-run updates instead of duplicating.
Cost: about 81,000 tokens in total ≈ $0.81 at $10 per million retain tokens.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ustaad import config, packs, store  # noqa: E402
from ustaad.memory import HindsightMemory, all_memories  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
dry = "--dry-run" in sys.argv
store.init()
targets = args or packs.ids()
grand = 0
for ind in targets:
    mems = all_memories(ind)
    tokens = sum(len(m["text"]) for m in mems) // 4
    grand += tokens
    print(f"{ind:<11} {len(mems):>4} memories  ~{tokens:,} tokens  -> bank '{config.bank_id(ind)}'")
print(f"Total ~{grand:,} tokens ≈ ${grand / 1e6 * 10:.2f} retain cost")
if dry:
    sys.exit(0)
if not config.HINDSIGHT_API_KEY:
    sys.exit("HINDSIGHT_API_KEY is not set. Put it in .env (local) or in Render's Environment settings.")

hs = HindsightMemory()
for ind in targets:
    try:
        hs.setup_bank(ind)
        print(f"[{ind}] bank created")
    except Exception as e:  # usually "already exists"
        print(f"[{ind}] bank: {str(e)[:120]}")
    mems = all_memories(ind)
    for i in range(0, len(mems), 25):
        chunk = mems[i:i + 25]
        for attempt in range(3):
            try:
                hs.retain_batch(ind, chunk)
                print(f"[{ind}] saved {min(i + 25, len(mems))}/{len(mems)}")
                break
            except Exception as e:
                print(f"[{ind}] retry {attempt + 1}: {str(e)[:150]}")
                time.sleep(3 * (attempt + 1))
        else:
            print(f"[{ind}] gave up on memories {i}-{i + 25}; run the script again later")
print("Done. Hindsight processes memories in the background — give it a minute before testing recall.")

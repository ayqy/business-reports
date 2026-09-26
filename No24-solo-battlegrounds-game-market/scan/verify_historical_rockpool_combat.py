"""Verify bounded Rockpool target buffs through combat snapshots and settlement."""

from __future__ import annotations

import json
from pathlib import Path

import verify_historical_adapt_combat as bridge


VECTORS = json.loads((Path(__file__).resolve().parent /
                      "historical-combat-rockpool-vectors.json").read_text(encoding="utf-8"))


def main() -> None:
    assert VECTORS["build"] == bridge.combat.RULES["build"] == bridge.recruit.RULES["build"] == 35747
    assert VECTORS["mode"] == bridge.combat.RULES["mode"] == bridge.recruit.RULES["mode"]
    assert len(VECTORS["cases"]) == len({case["id"] for case in VECTORS["cases"]})
    assert all(value == "unknown" for value in VECTORS["historical_unknown"].values())
    for case in VECTORS["cases"]:
        bridge.verify_case(case)
    print(f"Rockpool recruit/combat/lifecycle reference vectors: "
          f"{len(VECTORS['cases'])} passed; original retarget timing unknown")


if __name__ == "__main__":
    main()

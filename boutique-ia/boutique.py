"""Lanceur : fait tourner un agent pour une boutique donnée.

  python boutique.py <boutique> <agent> [options de l'agent]

Exemples :
  python boutique.py animaux chercheur_produits idees --nombre 15
  python boutique.py cadeaux fiches
  python boutique.py cadeaux publier --essai
  python boutique.py tout tableau_de_bord --jours 7     (toutes les boutiques à la suite)

Boutiques : dossiers dans boutiques/. Agents : fichiers dans agents/.
"""

import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent


def main():
    boutiques = sorted(p.name for p in (RACINE / "boutiques").iterdir() if (p / "config.json").exists())
    agents = sorted(p.stem for p in (RACINE / "agents").glob("*.py") if p.stem != "commun")
    if len(sys.argv) < 3 or sys.argv[1] not in boutiques + ["tout"] or sys.argv[2] not in agents:
        print(__doc__)
        print(f"Boutiques disponibles : {', '.join(boutiques)}\nAgents : {', '.join(agents)}")
        sys.exit(1)
    cibles = boutiques if sys.argv[1] == "tout" else [sys.argv[1]]
    code = 0
    for b in cibles:
        if len(cibles) > 1:
            print(f"\n========== {b.upper()} ==========")
        r = subprocess.run([sys.executable, str(RACINE / "agents" / f"{sys.argv[2]}.py"), *sys.argv[3:]],
                           env=dict(os.environ, BOUTIQUE=b))
        code = code or r.returncode
    sys.exit(code)


if __name__ == "__main__":
    main()

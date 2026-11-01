"""Agent 5 : VEILLE DES TENDANCES
Cherche sur le web ce qui monte en ce moment dans la niche (questions fréquentes,
sujets viraux, nouveautés IA, recherches Google, discussions Reddit et Facebook)
et propose des sujets de guides PDF classés par potentiel de vente.

Usage : python contenu/veille.py [--nombre 15]
Sortie : donnees/sujets.csv (les nouveaux sujets s'ajoutent aux anciens)
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agents"))
from commun import DONNEES, RECHERCHE_WEB, claude_json, ecrire_csv, lire_csv  # noqa: E402

CONFIG = json.loads((Path(__file__).parent / "config.json").read_text(encoding="utf-8"))

SYSTEME = """Tu es stratège en produits numériques et en contenu court (TikTok, Reels).
Utilise la recherche web pour repérer ce qui intéresse VRAIMENT l'audience en ce moment :
nouveautés récentes, questions posées sur Reddit, Facebook et forums, recherches en hausse,
vidéos virales, et ce que les concurrents vendent déjà (prix, angle, avis).
Privilégie les sujets où les gens ont un problème urgent et payeraient 27 $ pour un guide pas à pas.
Évite les sujets déjà saturés en français, sauf si tu trouves un angle nettement meilleur.
Chaque sujet doit être traitable de façon fiable par écrit, sans promesse de revenus."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nombre", type=int, default=15)
    a = ap.parse_args()

    existants = lire_csv(DONNEES / "sujets.csv")
    deja = "\n".join(s["titre"] for s in existants) or "aucun"
    demande = f"""Niche : {CONFIG['niche']}
Audience : {CONFIG['audience']}
Date du jour : {date.today().isoformat()}
Sujets déjà retenus (ne pas répéter) :
{deja}

Propose {a.nombre} sujets de guides PDF. Pour chacun, JSON :
{{"sujets": [{{"titre": "titre vendeur, 60 caractères max",
"promesse": "résultat concret en une phrase",
"probleme": "la douleur précise de l'audience",
"preuve_tendance": "ce que tu as trouvé sur le web qui montre l'intérêt, avec la source",
"concurrence": "faible|moyenne|forte",
"potentiel": 1 à 10,
"accroches_video": ["3 premières phrases de vidéos qui arrêtent le défilement"]}}]}}"""

    resultat = claude_json(SYSTEME, demande, effort="high", outils=RECHERCHE_WEB)
    nouveaux = []
    for s in resultat["sujets"]:
        nouveaux.append({
            "date": date.today().isoformat(), "titre": s["titre"], "promesse": s["promesse"],
            "probleme": s["probleme"], "preuve_tendance": s["preuve_tendance"],
            "concurrence": s["concurrence"], "potentiel": s["potentiel"],
            "accroches_video": " | ".join(s.get("accroches_video", [])), "statut": "idee",
        })
    tous = existants + nouveaux
    tous.sort(key=lambda s: (s["statut"] != "idee", -int(s["potentiel"])))
    ecrire_csv(DONNEES / "sujets.csv", tous)
    print(f"{len(nouveaux)} sujets ajoutés. Les meilleurs :")
    for s in sorted(nouveaux, key=lambda s: -int(s["potentiel"]))[:5]:
        print(f"  [{s['potentiel']}/10] {s['titre']}  (concurrence {s['concurrence']})")


if __name__ == "__main__":
    main()

"""Saisie des dépenses publicitaires, produit par produit.

  python boutique.py cadeaux pub ajouter <produit> <montant> [--plateforme tiktok] [--date 2026-11-12]
  python boutique.py cadeaux pub liste                 (produits en vente et dernières saisies)
  python boutique.py cadeaux pub corriger              (supprime la dernière saisie)

<produit> : un ou plusieurs mots du titre ou de l'adresse du produit (ex. « lampe lune »),
ou « general » pour une dépense qui ne vise pas un produit précis.
Le montant est celui affiché par TikTok ou Meta pour la journée, en dollars.
"""

import argparse
import re
import sys
import unicodedata
from datetime import date

from commun import DONNEES, ecrire_csv, lire_csv, lire_json

FICHIER = DONNEES / "pub.csv"


def normaliser(t: str) -> str:
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()


def produits_en_vente() -> list[dict]:
    resultats = []
    for f in sorted((DONNEES / "produits").glob("*.json")):
        p = lire_json(f)
        if p.get("statut") in ("publie", "actif") and p.get("fiche"):
            resultats.append({"handle": p["fiche"]["handle"], "titre": p["fiche"]["titre"]})
    return resultats


def trouver(recherche: str) -> dict:
    if normaliser(recherche) in ("general", "global"):
        return {"handle": "general", "titre": "Dépense générale"}
    mots = normaliser(recherche).split()
    produits = produits_en_vente()
    exact = [p for p in produits if p["handle"] == recherche]
    trouves = exact or [p for p in produits if all(m in normaliser(p["titre"] + " " + p["handle"]) for m in mots)]
    if len(trouves) == 1:
        return trouves[0]
    if not trouves:
        sys.exit(f"Aucun produit en vente ne correspond à « {recherche} ». Voir : pub liste")
    print(f"Plusieurs produits correspondent à « {recherche} », précise :")
    for p in trouves:
        print(f"  {p['handle']}")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="action", required=True)
    a = sp.add_parser("ajouter")
    a.add_argument("produit", nargs="+")
    a.add_argument("--plateforme", default="")
    a.add_argument("--date", default=date.today().isoformat())
    sp.add_parser("liste")
    sp.add_parser("corriger")
    args = ap.parse_args()
    lignes = lire_csv(FICHIER)

    if args.action == "ajouter":
        *mots, montant = args.produit
        try:
            montant = float(montant.replace(",", ".").replace("$", ""))
        except ValueError:
            sys.exit("Le dernier mot doit être le montant, ex. : pub ajouter lampe lune 35")
        if not mots:
            sys.exit("Indique le produit, ex. : pub ajouter lampe lune 35")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
            sys.exit("Date au format AAAA-MM-JJ")
        p = trouver(" ".join(mots))
        lignes.append({"date": args.date, "produit": p["handle"], "plateforme": args.plateforme.lower(),
                       "depense": f"{montant:.2f}"})
        ecrire_csv(FICHIER, lignes)
        total = sum(float(l["depense"]) for l in lignes if l["produit"] == p["handle"])
        print(f"Noté : {montant:.2f} $ le {args.date} pour « {p['titre']} » (total pour ce produit : {total:.2f} $)")

    elif args.action == "corriger":
        if not lignes:
            sys.exit("Aucune saisie.")
        retiree = lignes.pop()
        ecrire_csv(FICHIER, lignes) if lignes else FICHIER.unlink()
        print(f"Supprimé : {retiree}")

    else:
        print("PRODUITS EN VENTE")
        for p in produits_en_vente():
            print(f"  {p['handle'][:45]:<45}  {p['titre'][:50]}")
        print("\nDERNIÈRES SAISIES")
        for l in lignes[-10:]:
            print(f"  {l['date']}  {l['depense']:>8} $  {l['plateforme']:<8} {l['produit']}")


if __name__ == "__main__":
    main()

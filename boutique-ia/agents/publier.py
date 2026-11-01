"""Agent 3 : PUBLICATION SHOPIFY
Met en ligne toutes les fiches prêtes : titre, description, photos, options, variantes, prix,
coût (pour le calcul des marges), SKU du fournisseur. Les produits déjà présents
(même adresse) ne sont jamais créés deux fois.

Par défaut les produits arrivent en BROUILLON : tu les regardes dans l'admin Shopify.
  python agents/publier.py              -> crée les brouillons
  python agents/publier.py --essai      -> montre ce qui serait envoyé, sans rien toucher
  python agents/publier.py --activer    -> rend actifs et visibles les brouillons déjà créés
"""

import argparse
import json

import shopify
from commun import CONFIG, DONNEES, ecrire_json, lire_json

PRODUITS = DONNEES / "produits"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--essai", action="store_true")
    ap.add_argument("--activer", action="store_true")
    ap.add_argument("--max", type=int, default=CONFIG["produits_par_lot"])
    a = ap.parse_args()

    fichiers = sorted(PRODUITS.glob("*.json"))
    if a.activer:
        for f in fichiers:
            p = lire_json(f)
            if p.get("statut") == "publie" and p.get("shopify_id"):
                shopify.publier_boutique_en_ligne(p["shopify_id"])
                p["statut"] = "actif"
                ecrire_json(f, p)
                print(f"Actif : {p['fiche']['titre']}")
        return

    faits = 0
    for f in fichiers:
        p = lire_json(f)
        if p.get("statut") != "fiche" or faits >= a.max:
            continue
        if a.essai:
            print(json.dumps(p["fiche"], ensure_ascii=False, indent=2)[:1500], "\n---")
            faits += 1
            continue
        try:
            p["shopify_id"] = shopify.creer_produit(p["fiche"], CONFIG["statut_publication"])
            p["statut"] = "publie" if CONFIG["statut_publication"] == "DRAFT" else "actif"
            if p["statut"] == "actif":
                shopify.publier_boutique_en_ligne(p["shopify_id"])
            ecrire_json(f, p)
            faits += 1
            print(f"Créé : {p['fiche']['titre']}  ->  {p['shopify_id']}")
        except Exception as e:
            print(f"Échec : {p['fiche']['titre']} ({e})")
    print(f"{faits} produits envoyés à Shopify.")


if __name__ == "__main__":
    main()

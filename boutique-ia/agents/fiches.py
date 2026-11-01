"""Agent 2 : RÉDACTEUR DE FICHES PRODUITS
Pour chaque produit approuvé : Claude regarde les photos, lit la description du fournisseur
et écrit une fiche complète et vendeuse (titre, description, référencement, étiquettes,
noms des options et des variantes traduits). Le prix est calculé automatiquement.

Usage : python agents/fiches.py [--max 25]
Sortie : la fiche est ajoutée dans donnees/produits/<id>.json (statut « fiche »).
"""

import argparse
import json
import re
import unicodedata

from commun import CONFIG, DONNEES, claude_json, ecrire_json, lire_csv, lire_json, prix_de_vente

PRODUITS = DONNEES / "produits"

SYSTEME = f"""Tu es rédacteur e-commerce pour la boutique « {CONFIG['boutique']} ».
Niche : {CONFIG['niche']}. Clientèle : {CONFIG['client_type']}.
Langue : {CONFIG['langue']} (si fr-CA : français du Québec naturel, vouvoiement, termes de l'OQLF).
Règles :
- Décris seulement ce que les photos et la description du fournisseur permettent d'affirmer.
  Aucune allégation de santé, de sécurité ou de certification non prouvée.
- Aucun faux prix barré, aucune fausse rareté, aucun faux avis.
- Titre : 70 caractères max, bénéfice clair, pas de majuscules partout, pas de nom de marque tierce.
- Description HTML (p, ul, li, strong, h3) : accroche émotionnelle de 2 phrases, 4 à 6 bénéfices,
  caractéristiques (dimensions, matière si connues), contenu du colis, entretien, puis la phrase
  de livraison fournie telle quelle.
- Si le produit est interdit ({', '.join(CONFIG['interdits'])}), réponds {{"refus": "raison"}}."""


MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
        "octobre", "novembre", "décembre"]


def date_longue(iso: str) -> str:
    a, m, j = (int(x) for x in iso.split("-"))
    return f"{j} {MOIS[m - 1]}"


def slug(texte: str) -> str:
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:70]


def rediger(p: dict) -> dict:
    noms_options = list(dict.fromkeys(k for v in p["variantes"] for k in v["valeurs"]))
    valeurs = {o: list(dict.fromkeys(v["valeurs"][o] for v in p["variantes"] if o in v["valeurs"]))
               for o in noms_options}
    livraison = (f"Livraison en {p['delai_jours']} jours ouvrables, avec numéro de suivi."
                 if p.get("delai_jours") else "Livraison avec numéro de suivi.")
    if CONFIG.get("message_saison") and CONFIG.get("date_limite"):
        livraison += " " + CONFIG["message_saison"].format(date_limite=date_longue(CONFIG["date_limite"]))
    blocs = [{"type": "image", "source": {"type": "url", "url": u}} for u in p["images"][:3]]
    blocs.append({"type": "text", "text": f"""Produit fournisseur : {p['titre_source']}
Description fournisseur : {p['description_source'][:3000]}
Angle trouvé par la recherche : {json.dumps(p.get('idee', {}), ensure_ascii=False)}
Options d'origine : {json.dumps(valeurs, ensure_ascii=False)}
Phrase de livraison : {livraison}

JSON : {{"titre": "...", "description_html": "...", "seo_titre": "60 car. max", "seo_description": "155 car. max",
"type": "catégorie de produit", "tags": ["5 à 10"], "collections": ["1 ou 2 noms de collection"],
"options": {{"nom d'origine": {{"nom": "nom traduit", "valeurs": {{"valeur d'origine": "valeur traduite"}}}}}}}}"""})
    r = claude_json(SYSTEME, blocs, effort="medium")
    if r.get("refus"):
        raise ValueError(r["refus"])

    trad = r.get("options", {})
    nom = lambda o: trad.get(o, {}).get("nom", o)  # noqa: E731
    val = lambda o, v: trad.get(o, {}).get("valeurs", {}).get(v, v)  # noqa: E731
    prix = prix_de_vente(p["cout_usd"], p["livraison_usd"])  # un seul prix : plus simple à tester
    return {
        "titre": r["titre"], "description_html": r["description_html"], "handle": slug(r["titre"]),
        "seo_titre": r.get("seo_titre", ""), "seo_description": r.get("seo_description", ""),
        "type": r.get("type", ""), "tags": r.get("tags", []) + [f"source-{p['source']}"] + r.get("collections", []),
        "fournisseur": CONFIG["boutique"], "images": p["images"],
        "options": [{"nom": nom(o), "valeurs": [val(o, v) for v in valeurs[o]]} for o in noms_options],
        "variantes": [{"valeurs": {nom(o): val(o, v) for o, v in var["valeurs"].items()}, "prix": prix,
                       "cout": round((var["cout_usd"] + p["livraison_usd"]) * CONFIG["taux_usd_vers_devise"], 2),
                       "sku": var.get("sku", ""), "image": var.get("image", "")} for var in p["variantes"]],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=CONFIG["produits_par_lot"])
    a = ap.parse_args()
    approuves = [c["id"] for c in lire_csv(DONNEES / "candidats.csv") if c["statut"] == "approuve"]
    faits = 0
    for ident in approuves:
        if faits >= a.max:
            break
        chemin = PRODUITS / f"{ident}.json"
        p = lire_json(chemin)
        if not p or p.get("fiche"):
            continue
        try:
            p["fiche"] = rediger(p)
            p["statut"] = "fiche"
            print(f"Fiche : {p['fiche']['titre']}  ({p['fiche']['variantes'][0]['prix']} {CONFIG['devise']})")
        except ValueError as refus:
            p["statut"] = "rejete"
            print(f"Rejeté : {p['titre_source'][:60]} ({refus})")
        except Exception as e:
            print(f"Échec : {p['titre_source'][:60]} ({e})")
            continue
        ecrire_json(chemin, p)
        faits += 1
    print(f"{faits} produits traités. Relis-les si tu veux, puis : python agents/publier.py")


if __name__ == "__main__":
    main()

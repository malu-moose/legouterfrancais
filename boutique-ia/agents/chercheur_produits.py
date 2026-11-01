"""Agent 1 : CHERCHEUR DE PRODUITS
1. idees    : Claude cherche sur le web ce qui se vend en ce moment dans la niche
              (TikTok, Amazon, tendances, concurrents) et propose des idées de produits.
2. sourcer  : pour chaque idée, cherche le produit chez CJ Dropshipping, calcule coût,
              livraison, prix de vente et marge, élimine les produits trop lents ou pas
              rentables, puis Claude note chaque candidat en regardant ses photos.
3. importer : alternative à CJ, importe un CSV de n'importe quel fournisseur.

Résultat : donnees/candidats.csv. Mettre la colonne statut à « approuve » pour les produits
retenus (ou utiliser --auto pour approuver ceux notés 7/10 et plus).

Usage :
  python agents/chercheur_produits.py idees --nombre 20
  python agents/chercheur_produits.py sourcer [--auto]
  python agents/chercheur_produits.py importer fournisseur.csv
"""

import argparse
import csv
import json
import re
from datetime import date

import cj
from commun import (CONFIG, DONNEES, RECHERCHE_WEB, claude_json, ecrire_csv, ecrire_json, lire_csv,
                    lire_json, prix_de_vente, rentable)

PRODUITS = DONNEES / "produits"
IDEES = DONNEES / "idees.csv"
CANDIDATS = DONNEES / "candidats.csv"


def delai_max(texte: str) -> int:
    nombres = [int(n) for n in re.findall(r"\d+", texte or "")]
    return max(nombres) if nombres else 0


# ---------------------------------------------------------------- 1. Idées

def idees(nombre: int):
    deja = [i["produit"] for i in lire_csv(IDEES)]
    r = claude_json(
        f"""Tu es chercheur de produits gagnants pour une boutique en dropshipping.
Niche : {CONFIG['niche']}
Clientèle : {CONFIG['client_type']}
Marché : {CONFIG['marche']}
Utilise la recherche web : vidéos TikTok et Reels qui performent, meilleures ventes Amazon,
tendances de recherche, publicités qui tournent depuis longtemps, boutiques concurrentes.
Un bon produit : effet « wow » en vidéo, règle un problème réel, introuvable en magasin,
prix de vente entre {CONFIG['prix_min']} et {CONFIG['prix_max']} {CONFIG['devise']}, léger, peu fragile.
Interdits : {', '.join(CONFIG['interdits'])}.""",
        f"""Date : {date.today().isoformat()}
Idées déjà connues (ne pas répéter) : {', '.join(deja) or 'aucune'}
Propose {nombre} produits. JSON : {{"idees": [{{"produit": "nom en français",
"mot_cle_en": "2 à 4 mots en anglais pour chercher chez le fournisseur",
"pourquoi": "preuve de la demande trouvée sur le web, avec la source",
"angle_video": "l'idée de vidéo qui le vendrait", "prix_marche": "prix constaté chez les concurrents"}}]}}""",
        effort="high", outils=RECHERCHE_WEB)
    nouvelles = [dict(i, date=date.today().isoformat(), source="") for i in r["idees"]]
    ecrire_csv(IDEES, lire_csv(IDEES) + nouvelles)
    print(f"{len(nouvelles)} idées ajoutées à {IDEES}")


# ---------------------------------------------------------------- 2. Sourcing

NOTATION = f"""Tu évalues des produits pour une boutique en dropshipping.
Niche : {CONFIG['niche']}. Clientèle : {CONFIG['client_type']}.
Note de 1 à 10 selon : effet visuel en vidéo, problème réglé, qualité perçue sur les photos,
marge, délai de livraison, risque de retours ou de plaintes. Sois exigeant : 7 et plus seulement
pour les produits que tu lancerais avec ton propre argent.
Rejette (note 0) tout produit de marque, contrefait, ou dans les interdits : {', '.join(CONFIG['interdits'])}."""


def enregistrer_candidat(p: dict, idee: dict | None = None):
    cout_total = p["cout_usd"] + p["livraison_usd"]
    p["prix_vente"] = prix_de_vente(p["cout_usd"], p["livraison_usd"])
    p["marge"] = round(p["prix_vente"] - cout_total * CONFIG["taux_usd_vers_devise"], 2)
    p["idee"] = idee or {}
    p.setdefault("statut", "candidat")
    ecrire_json(PRODUITS / f"{p['id']}.json", p)


def noter(produits: list[dict]):
    blocs = []
    for p in produits:
        blocs.append({"type": "text", "text": json.dumps({
            "id": p["id"], "titre": p["titre_source"], "cout_total_usd": round(p["cout_usd"] + p["livraison_usd"], 2),
            "prix_vente": p["prix_vente"], "marge": p["marge"], "delai_jours": p["delai_jours"],
            "description": p["description_source"][:600]}, ensure_ascii=False)})
        if p["images"]:
            blocs.append({"type": "image", "source": {"type": "url", "url": p["images"][0]}})
    blocs.append({"type": "text", "text": 'JSON : {"notes": [{"id": "...", "note": n, "raison": "1 phrase"}]}'})
    notes = {n["id"]: n for n in claude_json(NOTATION, blocs, effort="medium")["notes"]}
    for p in produits:
        n = notes.get(p["id"], {})
        p["note"], p["raison"] = int(n.get("note", 0)), n.get("raison", "")
        ecrire_json(PRODUITS / f"{p['id']}.json", p)


def sourcer(par_idee: int, auto: bool):
    toutes = lire_csv(IDEES)
    for idee in [i for i in toutes if not i.get("source")]:
        print(f"Sourcing : {idee['produit']} ({idee['mot_cle_en']})")
        retenus = []
        try:
            resultats = cj.chercher(idee["mot_cle_en"], 10)
        except Exception as e:
            print(f"  échec CJ : {e}")
            continue
        for r in resultats[:par_idee]:
            if (PRODUITS / f"{r['pid']}.json").exists():
                continue
            try:
                p = cj.produit(r["pid"], "CA" if "Canada" in CONFIG["marche"] else "US")
            except Exception as e:
                print(f"  {r.get('pid')} ignoré : {e}")
                continue
            if not rentable(p["cout_usd"], p["livraison_usd"]):
                print(f"  {p['titre_source'][:50]} : pas rentable dans la fourchette de prix")
                continue
            if delai_max(p["delai_jours"]) > CONFIG["delai_livraison_max_jours"]:
                print(f"  {p['titre_source'][:50]} : livraison trop lente ({p['delai_jours']} j)")
                continue
            enregistrer_candidat(p, idee)
            retenus.append(p)
        if retenus:
            noter(retenus)
        idee["source"] = f"{len(retenus)} candidats"
        ecrire_csv(IDEES, toutes)
    mettre_a_jour_candidats(auto)


def mettre_a_jour_candidats(auto: bool = False):
    """Régénère candidats.csv à partir des fiches JSON, en gardant les statuts choisis à la main."""
    statuts = {c["id"]: c["statut"] for c in lire_csv(CANDIDATS)}
    lignes = []
    for f in sorted(PRODUITS.glob("*.json")):
        p = lire_json(f)
        statut = statuts.get(p["id"], p.get("statut", "candidat"))
        if auto and statut == "candidat" and int(p.get("note", 0)) >= 7:
            statut = "approuve"
        if statut != p.get("statut"):
            p["statut"] = statut
            ecrire_json(f, p)
        lignes.append({"id": p["id"], "statut": statut, "note": p.get("note", ""), "titre": p["titre_source"][:80],
                       "prix_vente": p["prix_vente"], "marge": p["marge"], "delai_jours": p["delai_jours"],
                       "raison": p.get("raison", ""), "lien": p.get("lien_fournisseur", "")})
    lignes.sort(key=lambda l: (l["statut"] != "candidat", -int(l["note"] or 0)))
    ecrire_csv(CANDIDATS, lignes)
    print(f"{CANDIDATS} : {sum(l['statut'] == 'candidat' for l in lignes)} à décider, "
          f"{sum(l['statut'] == 'approuve' for l in lignes)} approuvés")


# ---------------------------------------------------------------- 3. Import CSV

def importer(chemin: str):
    """Colonnes : titre, description, images (URL séparées par |), cout_usd, livraison_usd,
    delai_jours, sku, lien_fournisseur. Facultatif : option, valeurs (séparées par |)."""
    with open(chemin, newline="", encoding="utf-8-sig") as f:
        lignes = list(csv.DictReader(f))
    produits = []
    for i, l in enumerate(lignes):
        ident = re.sub(r"[^A-Za-z0-9]+", "-", l.get("sku") or f"import-{date.today()}-{i}")
        cout = float(l["cout_usd"])
        valeurs = [v for v in (l.get("valeurs") or "").split("|") if v]
        variantes = [{"sku": f"{l.get('sku', ident)}-{j}", "valeurs": {l.get("option") or "Modèle": v},
                      "cout_usd": cout, "image": ""} for j, v in enumerate(valeurs)] or \
                    [{"sku": l.get("sku", ident), "valeurs": {}, "cout_usd": cout, "image": ""}]
        p = {"source": "import", "id": ident, "titre_source": l["titre"], "description_source": l.get("description", ""),
             "categorie_source": "", "images": [u for u in (l.get("images") or "").split("|") if u],
             "variantes": variantes, "cout_usd": cout, "livraison_usd": float(l.get("livraison_usd") or 0),
             "delai_jours": l.get("delai_jours", ""), "lien_fournisseur": l.get("lien_fournisseur", "")}
        enregistrer_candidat(p)
        produits.append(p)
    for i in range(0, len(produits), 10):
        noter(produits[i:i + 10])
    mettre_a_jour_candidats()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="action", required=True)
    sp.add_parser("idees").add_argument("--nombre", type=int, default=20)
    s = sp.add_parser("sourcer")
    s.add_argument("--par-idee", type=int, default=3)
    s.add_argument("--auto", action="store_true")
    sp.add_parser("importer").add_argument("fichier")
    sp.add_parser("actualiser").add_argument("--auto", action="store_true")
    a = ap.parse_args()
    PRODUITS.mkdir(exist_ok=True)
    if a.action == "idees":
        idees(a.nombre)
    elif a.action == "sourcer":
        sourcer(a.par_idee, a.auto)
    elif a.action == "importer":
        importer(a.fichier)
    else:
        mettre_a_jour_candidats(a.auto)

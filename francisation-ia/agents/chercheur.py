"""Agent 0 : CHERCHEUR DE LISTES
Construit donnees/entreprises.csv, la matière première du prospecteur. Deux modes :

1. Importer un export Google Maps (le plus rapide : 2 000 entreprises en une heure)
   Outil conseillé : « Google Maps Scraper » sur apify.com (environ 5 $ pour 1 000 lieux).
   Recherches à lancer : voir donnees/cibles.csv (secteur + ville).
   python agents/chercheur.py importer export_apify.csv

2. Laisser Claude chercher sur le web, secteur par secteur (plus lent, plus ciblé)
   python agents/chercheur.py chercher --cibles donnees/cibles.csv --par-cible 25

Les doublons (même domaine) sont éliminés automatiquement.
"""

import argparse
import csv
import sys
import urllib.parse
from pathlib import Path

from commun import DONNEES, RECHERCHE_WEB, claude_json, ecrire_csv, lire_csv

FICHIER = DONNEES / "entreprises.csv"

# Segments où la proportion de sites en anglais seulement est la plus forte.
CIBLES_DEFAUT = [
    # Entreprises hors Québec qui vendent au Québec : budget plus élevé, besoin évident
    ("boutique en ligne canadienne qui livre au Québec (vêtements, beauté, maison, sport)", "Toronto"),
    ("boutique en ligne canadienne qui livre au Québec (vêtements, beauté, maison, sport)", "Vancouver"),
    ("entreprise de logiciels SaaS canadienne avec clients au Québec", "Toronto"),
    ("franchise canadienne avec succursales au Québec", "Ontario"),
    ("distributeur ou grossiste B2B qui sert le Québec", "Ontario"),
    # Secteurs locaux dans les zones à forte présence anglophone
    *[(s, v) for v in ("Pointe-Claire", "Kirkland", "Dollard-des-Ormeaux", "Beaconsfield", "Westmount",
                       "Côte-Saint-Luc", "Hampstead", "Montréal centre-ville", "Gatineau", "Sherbrooke")
      for s in ("clinique dentaire", "clinique de physiothérapie", "cabinet comptable",
                "entreprise de rénovation", "agence immobilière", "école privée ou centre de tutorat",
                "restaurant et traiteur", "entreprise de technologie")],
]

SYSTEME = """Tu constitues des listes de prospects B2B. Utilise la recherche web pour trouver des
entreprises réelles et actives correspondant au segment demandé, avec leur site web officiel.
Privilégie celles dont le site semble être en anglais seulement ou dont la version française
est absente ou incomplète. N'invente jamais une entreprise ni une URL : si tu n'es pas sûr, omets-la.
Ne cherche pas d'adresses courriel personnelles."""


def domaine(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")


def fusionner(nouvelles: list[dict]) -> int:
    existantes = lire_csv(FICHIER)
    vus = {domaine(e["site"]) for e in existantes if e.get("site")}
    ajout = 0
    for n in nouvelles:
        site = (n.get("site") or "").strip()
        if not site or "google." in site or "facebook.com" in site:
            continue
        d = domaine(site)
        if d in vus:
            continue
        vus.add(d)
        existantes.append({"nom": n.get("nom", "").strip(), "site": site, "email": n.get("email", "").strip(),
                           "ville": n.get("ville", "").strip(), "secteur": n.get("secteur", "").strip(),
                           "source_liste": n.get("source_liste", "")})
        ajout += 1
    ecrire_csv(FICHIER, existantes)
    return ajout


def importer(chemin: str):
    """Accepte les exports Apify, Outscraper, PhantomBuster ou tout CSV avec un nom et un site."""
    alias = {
        "nom": ("title", "name", "nom", "company", "business name"),
        "site": ("website", "site", "url", "domain", "site web"),
        "email": ("email", "emails/0", "email_1", "courriel"),
        "ville": ("city", "ville", "municipality"),
        "secteur": ("categoryname", "category", "type", "secteur", "industry"),
    }
    with open(chemin, newline="", encoding="utf-8-sig") as f:
        lignes = list(csv.DictReader(f))
    if not lignes:
        sys.exit("Fichier vide")
    colonnes = {c.lower(): c for c in lignes[0]}
    correspondance = {cle: next((colonnes[a] for a in noms if a in colonnes), None) for cle, noms in alias.items()}
    if not correspondance["site"]:
        sys.exit(f"Aucune colonne de site web trouvée parmi : {list(lignes[0])}")
    nouvelles = [{cle: (l.get(col) or "") if col else "" for cle, col in correspondance.items()}
                 | {"source_liste": Path(chemin).name} for l in lignes]
    print(f"{fusionner(nouvelles)} entreprises ajoutées ({len(lignes)} lignes lues). Total : {len(lire_csv(FICHIER))}")


def chercher(fichier_cibles: Path, par_cible: int):
    if not fichier_cibles.exists():
        ecrire_csv(fichier_cibles, [{"secteur": s, "ville": v, "fait": ""} for s, v in CIBLES_DEFAUT])
        print(f"Liste de cibles créée : {fichier_cibles} ({len(CIBLES_DEFAUT)} segments). Modifie-la au besoin.")
    cibles = lire_csv(fichier_cibles)
    for c in cibles:
        if c.get("fait"):
            continue
        print(f"Recherche : {c['secteur']} / {c['ville']}")
        try:
            r = claude_json(SYSTEME, f"""Segment : {c['secteur']}
Zone : {c['ville']}
Trouve jusqu'à {par_cible} entreprises. JSON : {{"entreprises": [{{"nom": "...", "site": "https://...",
"ville": "...", "secteur": "...", "indice_anglais": "pourquoi tu penses que le site est surtout en anglais"}}]}}""",
                            effort="low", outils=RECHERCHE_WEB)
        except Exception as e:
            print(f"  échec : {e}")
            continue
        n = fusionner([e | {"source_liste": "recherche web"} for e in r.get("entreprises", [])])
        c["fait"] = str(n)
        ecrire_csv(fichier_cibles, cibles)
        print(f"  {n} nouvelles entreprises")
    print(f"Total dans {FICHIER.name} : {len(lire_csv(FICHIER))}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="action", required=True)
    i = sp.add_parser("importer")
    i.add_argument("fichier")
    c = sp.add_parser("chercher")
    c.add_argument("--cibles", default=str(DONNEES / "cibles.csv"))
    c.add_argument("--par-cible", type=int, default=25)
    a = ap.parse_args()
    importer(a.fichier) if a.action == "importer" else chercher(Path(a.cibles), a.par_cible)

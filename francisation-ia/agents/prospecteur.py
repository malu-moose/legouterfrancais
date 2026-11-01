"""Agent 1 : PROSPECTEUR
Prend une liste d'entreprises québécoises (donnees/entreprises.csv) et repère celles
dont le site web est en anglais seulement ou mal francisé. Ce sont les clients.

Colonnes attendues : nom, site, email, ville, secteur  (email/ville/secteur facultatifs)
Sortie : donnees/prospects.csv, trié du plus chaud au plus froid.

Usage : python agents/prospecteur.py [--pages 5]
"""

import argparse
from concurrent.futures import ThreadPoolExecutor

from commun import DONNEES, ecrire_csv, explorer_site, lire_csv, meilleur_courriel, nombre_mots, part_anglais


def evaluer(entreprise: dict, max_pages: int) -> dict:
    site = entreprise["site"].strip()
    if not site.startswith("http"):
        site = "https://" + site
    res = dict(entreprise, site=site, statut="nouveau")
    try:
        pages = explorer_site(site, max_pages)
    except Exception as e:
        return dict(res, erreur=str(e)[:120], score=0)
    if not pages:
        return dict(res, erreur="site injoignable", score=0)

    tous = [s for p in pages for s in p["segments"]]
    anglais = part_anglais(tous)
    a_version_fr = any("/fr" in p["url"] or p["lang"].startswith("fr") for p in pages)
    mots = nombre_mots(tous)
    # Score de 0 à 100 : plus le site est anglais, plus le prospect est chaud.
    score = round(anglais * 80 + (0 if a_version_fr else 20))
    if not res.get("email"):
        res["email"], res["preuve_courriel"] = meilleur_courriel(pages, site)
    return dict(
        res,
        pages_vues=len(pages),
        mots_echantillon=mots,
        part_anglais=f"{anglais:.0%}",
        version_fr_detectee="oui" if a_version_fr else "non",
        score=score,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=5, help="pages explorées par site")
    ap.add_argument("--seuil", type=int, default=50, help="score minimum pour être qualifié")
    args = ap.parse_args()

    entreprises = lire_csv(DONNEES / "entreprises.csv")
    if not entreprises:
        print("Ajoute d'abord des entreprises dans donnees/entreprises.csv (voir entreprises.exemple.csv)")
        return

    deja = {p["site"] for p in lire_csv(DONNEES / "prospects.csv")}
    a_traiter = [e for e in entreprises if e.get("site") and e["site"] not in deja]
    print(f"{len(a_traiter)} sites à analyser...")
    with ThreadPoolExecutor(8) as pool:
        resultats = list(pool.map(lambda e: evaluer(e, args.pages), a_traiter))

    tous = lire_csv(DONNEES / "prospects.csv") + resultats
    for r in tous:
        r["qualifie"] = "oui" if int(r.get("score") or 0) >= args.seuil else "non"
    tous.sort(key=lambda r: -int(r.get("score") or 0))
    ecrire_csv(DONNEES / "prospects.csv", tous)
    chauds = sum(r["qualifie"] == "oui" for r in resultats)
    print(f"Terminé : {chauds} prospects qualifiés sur {len(resultats)}. Voir donnees/prospects.csv")


if __name__ == "__main__":
    main()

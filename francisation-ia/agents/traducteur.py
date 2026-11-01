"""Agent 4 : TRADUCTEUR (la livraison)
Quand un client a payé : explore son site, extrait chaque texte, le traduit en
français du Québec par lots, puis un second passage relit et corrige.
Le livrable est un fichier CSV bilingue (url, anglais, français) que le client
ou son webmestre importe (WPML, Weglot, Shopify Translate & Adapt, etc.),
plus un rapport de contrôle qualité pour le réviseur humain.

Usage : python agents/traducteur.py https://client.com "Nom du client" [--glossaire glossaire.csv] [--pages 50]
Sortie : donnees/livraisons/<domaine>/traduction.csv et a_reviser.csv
"""

import argparse
import json
import urllib.parse

from commun import DONNEES, claude_json, ecrire_csv, explorer_site, lire_csv, part_anglais

LOT = 60

SYSTEME_TRAD = """Tu es traducteur agréé anglais vers français du Québec, spécialisé en sites web commerciaux.
Traduis chaque segment fidèlement, avec la terminologie recommandée par l'OQLF
(courriel, clavardage, panier d'achats, magasiner, infolettre, etc.).
Garde la ponctuation française (espace avant : ; ? ! dans le format québécois usuel), les nombres et prix au format québécois (19,99 $).
Garde intactes les marques, les noms propres, les URL et les variables comme {{nom}} ou %s.
Adapte les appels à l'action pour qu'ils sonnent naturels, sans allonger inutilement (boutons courts).
Si un segment est déjà en français, renvoie-le tel quel.
Format JSON : {"traductions": [{"id": n, "fr": "..."}]}"""

SYSTEME_QA = """Tu es réviseur linguistique au Québec. Pour chaque paire anglais/français, vérifie le sens,
les anglicismes, la terminologie OQLF, la cohérence avec le glossaire et la longueur des boutons.
Corrige directement si nécessaire. Indique "doute": true seulement si un humain doit vérifier
(ambiguïté, terme juridique ou médical, jeu de mots, contexte manquant).
Format JSON : {"revisions": [{"id": n, "fr": "...", "doute": bool, "note": "..."}]}"""


def traduire_site(url: str, nom: str, glossaire: list[dict], max_pages: int):
    domaine = urllib.parse.urlparse(url).netloc.replace("www.", "")
    dossier = DONNEES / "livraisons" / domaine
    dossier.mkdir(parents=True, exist_ok=True)

    pages = explorer_site(url, max_pages)
    segments, vus = [], set()
    for p in pages:
        for s in p["segments"]:
            if s not in vus:
                vus.add(s)
                segments.append({"id": len(segments), "url": p["url"], "en": s})
    a_traduire = [s for s in segments if part_anglais([s["en"]]) > 0.3 or len(s["en"].split()) <= 4]
    print(f"{len(pages)} pages, {len(segments)} segments uniques, {len(a_traduire)} à traduire")

    gloss = "\n".join(f"{g['en']} => {g['fr']}" for g in glossaire) or "aucun"
    contexte = f"Client : {nom} ({url}).\nGlossaire imposé :\n{gloss}\n\n"

    for i in range(0, len(a_traduire), LOT):
        lot = a_traduire[i:i + LOT]
        entree = json.dumps([{"id": s["id"], "en": s["en"]} for s in lot], ensure_ascii=False)
        trads = {t["id"]: t["fr"] for t in claude_json(SYSTEME_TRAD, contexte + entree)["traductions"]}
        paires = json.dumps([{"id": s["id"], "en": s["en"], "fr": trads.get(s["id"], "")} for s in lot],
                            ensure_ascii=False)
        revs = {r["id"]: r for r in claude_json(SYSTEME_QA, contexte + paires)["revisions"]}
        for s in lot:
            r = revs.get(s["id"], {})
            s["fr"] = r.get("fr") or trads.get(s["id"], "")
            s["doute"] = "oui" if r.get("doute") or not s["fr"] else ""
            s["note"] = r.get("note", "")
        print(f"  lot {i // LOT + 1}/{-(-len(a_traduire) // LOT)} terminé")

    ecrire_csv(dossier / "traduction.csv", [{k: s.get(k, "") for k in ("url", "en", "fr", "doute", "note")}
                                            for s in a_traduire])
    doutes = [s for s in a_traduire if s.get("doute")]
    ecrire_csv(dossier / "a_reviser.csv", [{k: s.get(k, "") for k in ("url", "en", "fr", "note")} for s in doutes])
    mots = sum(len(s["en"].split()) for s in a_traduire)
    print(f"Livraison prête dans {dossier} : {mots} mots, {len(doutes)} segments à faire vérifier par le réviseur.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("nom")
    ap.add_argument("--glossaire", help="CSV avec colonnes en,fr")
    ap.add_argument("--pages", type=int, default=50)
    a = ap.parse_args()
    from pathlib import Path
    g = lire_csv(Path(a.glossaire)) if a.glossaire else []
    traduire_site(a.url, a.nom, g, a.pages)

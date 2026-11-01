"""Agent 5 : SCÉNARISTE VIDÉO
Pour chaque produit en ligne, écrit des scripts de vidéos courtes (15 à 30 s) prêtes à produire
avec des outils IA ou des images du fournisseur, et remplit un calendrier de publication
importable dans Metricool ou Buffer (TikTok, Instagram Reels, Facebook Reels).

Usage : python agents/videos.py [--par-produit 3] [--par-jour 3]
Sortie : donnees/videos/<id>.json et donnees/calendrier.csv
"""

import argparse
import json
from datetime import date, timedelta

from commun import CONFIG, DONNEES, claude_json, ecrire_csv, ecrire_json, lire_csv, lire_json

PLATEFORMES = ["TikTok", "Instagram Reels", "Facebook Reels"]
HEURES = ["08:00", "12:30", "19:30"]

SYSTEME = f"""Tu es scénariste de vidéos courtes qui vendent des produits (TikTok, Reels).
Boutique : {CONFIG['boutique']}. Clientèle : {CONFIG['client_type']}. Langue : {CONFIG['langue']}.
Règles :
- Les 2 premières secondes arrêtent le défilement : problème visible, avant/après, réaction, démonstration.
- Montre le produit en action. Une idée par vidéo. Durée 15 à 30 secondes.
- Aucun faux témoignage présenté comme réel, aucune allégation de santé, aucune fausse rareté.
- Le contenu généré par IA doit porter l'étiquette « contenu IA » de la plateforme.
- Appel à l'action : lien en bio, ou « commente PRIX » pour recevoir le lien."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--par-produit", type=int, default=3)
    ap.add_argument("--par-jour", type=int, default=3, choices=[1, 2, 3])
    a = ap.parse_args()

    dossier = DONNEES / "videos"
    dossier.mkdir(exist_ok=True)
    calendrier = lire_csv(DONNEES / "calendrier.csv")
    derniere = max((date.fromisoformat(c["date"]) for c in calendrier), default=date.today())
    jour, rang = max(derniere, date.today()) + timedelta(days=1), 0

    for f in sorted((DONNEES / "produits").glob("*.json")):
        p = lire_json(f)
        if p.get("statut") not in ("publie", "actif") or (dossier / f.name).exists():
            continue
        fiche = p["fiche"]
        r = claude_json(SYSTEME, f"""Produit : {fiche['titre']} ({fiche['variantes'][0]['prix']} {CONFIG['devise']})
Description : {fiche['description_html'][:2000]}
Angle trouvé à la recherche : {json.dumps(p.get('idee', {}), ensure_ascii=False)}
Écris {a.par_produit} vidéos de formats différents. JSON : {{"videos": [{{"format": "...",
"accroche": "texte des 2 premières secondes", "plans": [{{"duree_s": n, "visuel": "ce qu'on voit
(prompt pour générateur vidéo IA ou extrait des images fournisseur)", "texte_ecran": "..."}}],
"voix_off": "facultatif, 40 mots max", "musique": "ambiance", "legende": "150 car. max",
"mots_clics": ["5 à 8"]}}]}}""", effort="low")
        ecrire_json(dossier / f.name, r["videos"])
        for v in r["videos"]:
            quand = jour + timedelta(days=rang // a.par_jour)
            for plateforme in PLATEFORMES:
                calendrier.append({
                    "date": quand.isoformat(), "heure": HEURES[rang % a.par_jour], "plateforme": plateforme,
                    "produit": fiche["titre"], "format": v["format"], "accroche": v["accroche"],
                    "legende": v["legende"] + "\n\n" + " ".join("#" + t.lstrip("#").replace(" ", "") for t in v["mots_clics"]),
                    "etiquette_ia": "à activer", "statut": "à produire"})
            rang += 1
        print(f"{len(r['videos'])} scripts : {fiche['titre']}")
    ecrire_csv(DONNEES / "calendrier.csv", calendrier)
    print(f"Calendrier : {DONNEES / 'calendrier.csv'}")


if __name__ == "__main__":
    main()

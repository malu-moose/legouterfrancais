"""Agent 7 : SCÉNARISTE VIDÉO ET CALENDRIER
À partir d'un guide écrit, produit une série de vidéos courtes (20 à 45 s) prêtes
à produire avec des outils IA, et un calendrier de publication de 30 jours
importable dans un outil de planification (Metricool, Buffer, Later).

Pour chaque vidéo : accroche, voix off (pour ElevenLabs ou un avatar HeyGen),
plans visuels (prompts pour un générateur vidéo ou du b-roll), textes à l'écran,
légende, mots-clics, appel à l'action vers le lien en bio.

Usage : python contenu/videos.py donnees/guides/<slug> [--nombre 20] [--par-jour 1]
Sortie : <dossier du guide>/videos.json et donnees/calendrier.csv
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agents"))
from commun import DONNEES, claude_json, ecrire_csv, lire_csv  # noqa: E402

CONFIG = json.loads((Path(__file__).parent / "config.json").read_text(encoding="utf-8"))
HEURES = ["07:30", "12:15", "19:00"]  # heures de l'Est où l'audience défile le plus

SYSTEME = f"""Tu es scénariste de vidéos courtes virales (TikTok, Reels) pour {CONFIG['marque']}.
Audience : {CONFIG['audience']}
Ton : {CONFIG['ton']}
Règles :
- Les 2 premières secondes arrêtent le défilement : chiffre surprenant, erreur fréquente, avant/après, question directe.
- Une seule idée par vidéo, utile même sans acheter le guide. La vente se fait par la valeur.
- Varie les formats : tutoriel écran, liste, mythe contre réalité, histoire de client fictive clairement présentée comme exemple, réaction à une nouveauté.
- Voix off en français du Québec naturel, 55 à 110 mots. Aucun emoji dans la voix off.
- Aucune promesse de revenus, aucun faux témoignage présenté comme réel.
- L'appel à l'action renvoie au lien en bio ou invite à commenter un mot-clé.
- Le contenu est généré par IA : rappelle d'activer l'étiquette « contenu IA » de la plateforme."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier", help="dossier du guide (contient plan.json)")
    ap.add_argument("--nombre", type=int, default=20)
    ap.add_argument("--par-jour", type=int, default=1, choices=[1, 2, 3])
    a = ap.parse_args()

    dossier = Path(a.dossier)
    plan = json.loads((dossier / "plan.json").read_text(encoding="utf-8"))
    resultat = claude_json(SYSTEME, f"""Guide : {plan['titre']} ({CONFIG['echelle_de_prix'][0]['prix']} $)
Chapitres : {json.dumps([{'titre': c['titre'], 'points': c['points']} for c in plan['chapitres']], ensure_ascii=False)}
Lien en bio : {CONFIG['lien_bio']}

Écris {a.nombre} vidéos. JSON : {{"videos": [{{"numero": n, "format": "...", "accroche": "texte des 2 premières secondes",
"voix_off": "...", "plans": [{{"duree_s": n, "visuel": "prompt précis pour générateur vidéo IA ou description du b-roll",
"texte_ecran": "..."}}], "legende": "légende de publication, 150 caractères max",
"mots_clics": ["5 à 8"], "appel_action": "...", "duree_totale_s": n}}]}}""", effort="medium")

    videos = resultat["videos"]
    (dossier / "videos.json").write_text(json.dumps(videos, ensure_ascii=False, indent=2), encoding="utf-8")

    calendrier = lire_csv(DONNEES / "calendrier.csv")
    derniere = max((date.fromisoformat(c["date"]) for c in calendrier), default=date.today())
    jour = max(derniere, date.today()) + timedelta(days=1)
    for i, v in enumerate(videos):
        quand = jour + timedelta(days=i // a.par_jour)
        for plateforme in CONFIG["plateformes"]:
            calendrier.append({
                "date": quand.isoformat(), "heure": HEURES[i % a.par_jour], "plateforme": plateforme,
                "guide": plan["titre"], "video": v["numero"], "format": v["format"],
                "accroche": v["accroche"], "legende": v["legende"] + "\n\n" + " ".join(
                    "#" + m.lstrip("#").replace(" ", "") for m in v["mots_clics"]),
                "etiquette_ia": "à activer", "statut": "à produire",
            })
    ecrire_csv(DONNEES / "calendrier.csv", calendrier)
    print(f"{len(videos)} scripts dans {dossier / 'videos.json'}")
    print(f"Calendrier mis à jour : {len(videos) * len(CONFIG['plateformes'])} publications ajoutées à donnees/calendrier.csv")


if __name__ == "__main__":
    main()

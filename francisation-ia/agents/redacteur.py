"""Agent 3 : RÉDACTEUR ET RELANCES
Écrit un courriel personnalisé par prospect qualifié (et 2 relances), puis peut
les envoyer par SMTP à un rythme raisonnable.

Conformité LCAP (loi canadienne anti-pourriel) : on n'écrit qu'aux adresses
professionnelles publiées sur le site de l'entreprise, le message concerne leur
activité, il identifie l'expéditeur et contient un moyen de se désabonner.

Usage :
  python agents/redacteur.py rediger           -> donnees/boite_envoi.csv (à relire)
  python agents/redacteur.py envoyer --max 40  -> envoie les courriels approuves=oui dus aujourd'hui
Variables : EXPEDITEUR_NOM, EXPEDITEUR_ENTREPRISE, EXPEDITEUR_ADRESSE_POSTALE,
            SMTP_HOTE, SMTP_PORT, SMTP_UTILISATEUR, SMTP_MOT_DE_PASSE, URL_AUDITS
"""

import argparse
import os
import smtplib
import time
from datetime import date, timedelta
from email.message import EmailMessage

from commun import DONNEES, claude_json, ecrire_csv, lire_csv

NOM = os.environ.get("EXPEDITEUR_NOM", "Prénom Nom")
ENTREPRISE = os.environ.get("EXPEDITEUR_ENTREPRISE", "Francisation Express")
ADRESSE = os.environ.get("EXPEDITEUR_ADRESSE_POSTALE", "Adresse postale à compléter")
URL_AUDITS = os.environ.get("URL_AUDITS", "https://votre-domaine.ca/audits")

SYSTEME = f"""Tu rédiges des courriels de prospection B2B pour {ENTREPRISE}, un service québécois
qui francise les sites web des entreprises (traduction IA + révision humaine, prix fixe, 5 jours).
Règles d'écriture strictes :
- Français du Québec, vouvoiement, ton humain et direct, phrases courtes.
- Aucun emoji. Aucun tiret ni puce. Aucune formule creuse ("j'espère que vous allez bien").
- Premier courriel : 90 mots maximum. Relances : 50 mots maximum.
- Mentionne un constat précis tiré des données (pourcentage d'anglais, absence de version française).
- Aucune menace ni affirmation juridique. Tu peux dire que la Charte de la langue française
  demande que l'information commerciale soit offerte en français.
- Un seul appel à l'action : consulter l'audit gratuit déjà préparé (lien fourni).
- Signe "{NOM}". N'ajoute pas de pied de page, il est ajouté automatiquement.
Format JSON : {{"objet": "...", "courriel": "...", "relance1": "...", "relance2": "..."}}"""


def pied_de_page(email: str) -> str:
    return (f"\n\n{NOM}\n{ENTREPRISE}\n{ADRESSE}\n"
            f"Vous ne souhaitez plus recevoir de messages de notre part ? Répondez simplement "
            f"\"désabonner\" et votre adresse ({email}) sera retirée sous 48 heures.")


def rediger():
    prospects = lire_csv(DONNEES / "prospects.csv")
    boite = lire_csv(DONNEES / "boite_envoi.csv")
    deja = {b["email"] for b in boite}
    nouveaux = [p for p in prospects if p.get("qualifie") == "oui" and p.get("email") and p["email"] not in deja]
    for p in nouveaux:
        lien = f"{URL_AUDITS}/{p['audit'].split('/')[-1]}" if p.get("audit") else URL_AUDITS
        donnees = (f"Entreprise : {p.get('nom')}\nSecteur : {p.get('secteur','')}\nVille : {p.get('ville','')}\n"
                   f"Site : {p['site']}\nPart d'anglais détectée : {p.get('part_anglais')}\n"
                   f"Version française détectée : {p.get('version_fr_detectee')}\nLien de l'audit : {lien}")
        try:
            r = claude_json(SYSTEME, donnees, effort="low")
        except Exception as e:
            print(f"ÉCHEC {p['nom']} : {e}")
            continue
        aujourd_hui = date.today()
        for etape, cle, delai in (("1", "courriel", 0), ("2", "relance1", 3), ("3", "relance2", 7)):
            boite.append({
                "email": p["email"], "nom": p.get("nom", ""), "etape": etape,
                "objet": r["objet"] if etape == "1" else "Re: " + r["objet"],
                "corps": r[cle] + pied_de_page(p["email"]),
                "date_prevue": (aujourd_hui + timedelta(days=delai)).isoformat(),
                "approuve": "non", "envoye": "", "reponse": "",
            })
        print(f"Rédigé : {p['nom']}")
    ecrire_csv(DONNEES / "boite_envoi.csv", boite)
    print("Relis donnees/boite_envoi.csv et passe la colonne approuve à oui (ou lance avec --auto).")


def envoyer(maximum: int, auto: bool):
    boite = lire_csv(DONNEES / "boite_envoi.csv")
    desabonnes = {l["email"] for l in lire_csv(DONNEES / "desabonnes.csv")}
    ont_repondu = {b["email"] for b in boite if b.get("reponse")}
    aujourd_hui = date.today().isoformat()
    a_envoyer = [b for b in boite if not b["envoye"] and b["date_prevue"] <= aujourd_hui
                 and (auto or b["approuve"] == "oui")
                 and b["email"] not in desabonnes and b["email"] not in ont_repondu]
    a_envoyer = a_envoyer[:maximum]
    if not a_envoyer:
        print("Rien à envoyer aujourd'hui.")
        return
    serveur = smtplib.SMTP(os.environ["SMTP_HOTE"], int(os.environ.get("SMTP_PORT", 587)))
    serveur.starttls()
    serveur.login(os.environ["SMTP_UTILISATEUR"], os.environ["SMTP_MOT_DE_PASSE"])
    for b in a_envoyer:
        m = EmailMessage()
        m["From"] = f"{NOM} <{os.environ['SMTP_UTILISATEUR']}>"
        m["To"] = b["email"]
        m["Subject"] = b["objet"]
        m.set_content(b["corps"])
        serveur.send_message(m)
        b["envoye"] = aujourd_hui
        print(f"Envoyé : {b['email']} (étape {b['etape']})")
        time.sleep(45)  # rythme humain, protège la réputation du domaine
    serveur.quit()
    ecrire_csv(DONNEES / "boite_envoi.csv", boite)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["rediger", "envoyer"])
    ap.add_argument("--max", type=int, default=40)
    ap.add_argument("--auto", action="store_true", help="envoie sans approbation manuelle")
    a = ap.parse_args()
    rediger() if a.action == "rediger" else envoyer(a.max, a.auto)

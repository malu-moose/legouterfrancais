"""Tableau de bord : où en est l'entonnoir et combien ça rapporte.
Clients signés : donnees/clients.csv (colonnes nom, forfait, montant, mensuel, date)

Usage : python agents/tableau_de_bord.py
"""

from datetime import date

from commun import DONNEES, lire_csv


def m(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


def main():
    prospects = lire_csv(DONNEES / "prospects.csv")
    boite = lire_csv(DONNEES / "boite_envoi.csv")
    clients = lire_csv(DONNEES / "clients.csv")
    mois = date.today().strftime("%Y-%m")

    envoyes = [b for b in boite if b.get("envoye")]
    contactes = {b["email"] for b in envoyes}
    reponses = {b["email"] for b in boite if b.get("reponse")}
    du_mois = [c for c in clients if c.get("date", "").startswith(mois)]
    ponctuel = sum(float(c.get("montant") or 0) for c in du_mois)
    recurrent = sum(float(c.get("mensuel") or 0) for c in clients)
    total = ponctuel + recurrent

    print(f"""
ENTONNOIR
  Sites analysés           {len(prospects)}
  Prospects qualifiés      {sum(p.get('qualifie') == 'oui' for p in prospects)}
  Audits produits          {sum(bool(p.get('audit')) for p in prospects)}
  Entreprises contactées   {len(contactes)}
  Courriels envoyés        {len(envoyes)}
  Réponses                 {len(reponses)}  ({len(reponses) / max(1, len(contactes)):.1%})
  Clients (total)          {len(clients)}

REVENUS {mois}
  Projets du mois          {m(ponctuel)} $
  Récurrent mensuel        {m(recurrent)} $
  TOTAL                    {m(total)} $   objectif 10 000 $  ({total / 10000:.0%})
""")
    manque = max(0, 10000 - total)
    if manque:
        print(f"  Il manque {m(manque)} $, soit environ {manque / 1990:.1f} forfait(s) Pro.")


if __name__ == "__main__":
    main()

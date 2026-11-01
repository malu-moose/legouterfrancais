"""Agent 4 : TABLEAU DE BORD
Ventes, marge estimée, produits gagnants et produits à retirer, à partir des vraies commandes Shopify.

Usage : python agents/tableau_de_bord.py [--jours 30] [--pub 0]
  --pub : dépenses publicitaires de la période, pour obtenir le profit net.
"""

import argparse
from collections import defaultdict
from datetime import date, timedelta

import shopify
from commun import CONFIG, DONNEES, lire_json


def m(x: float) -> str:
    return f"{x:,.2f}".replace(",", " ").replace(".", ",")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jours", type=int, default=30)
    ap.add_argument("--pub", type=float, default=0.0)
    a = ap.parse_args()

    depuis = (date.today() - timedelta(days=a.jours)).isoformat()
    commandes = [c for c in shopify.commandes(depuis) if c["displayFinancialStatus"] not in ("VOIDED", "REFUNDED")]
    ventes = sum(float(c["totalPriceSet"]["shopMoney"]["amount"]) for c in commandes)
    par_produit = defaultdict(lambda: {"titre": "", "qte": 0, "ventes": 0.0, "cout": 0.0})
    for c in commandes:
        for l in c["lineItems"]["nodes"]:
            cle = (l.get("product") or {}).get("handle") or l["title"]
            unite = float((((l.get("variant") or {}).get("inventoryItem") or {}).get("unitCost") or {}).get("amount") or 0)
            pp = par_produit[cle]
            pp["titre"] = l["title"]
            pp["qte"] += l["quantity"]
            pp["ventes"] += float(l["originalTotalSet"]["shopMoney"]["amount"])
            pp["cout"] += unite * l["quantity"]
    cout = sum(p["cout"] for p in par_produit.values())
    brut = ventes - cout
    net = brut - a.pub - ventes * 0.03  # environ 3 % de frais de paiement
    a_expedier = [c["name"] for c in commandes if c["displayFulfillmentStatus"] in ("UNFULFILLED", "PARTIALLY_FULFILLED")]

    print(f"""
{a.jours} DERNIERS JOURS ({CONFIG['devise']})
  Commandes               {len(commandes)}
  Ventes                  {m(ventes)}
  Panier moyen            {m(ventes / max(1, len(commandes)))}
  Coût produits+livraison {m(cout)}
  Marge brute             {m(brut)}  ({brut / max(1, ventes):.0%})
  Publicité               {m(a.pub)}
  PROFIT NET ESTIMÉ       {m(net)}
  Commandes à expédier    {len(a_expedier)} {' '.join(a_expedier[:10])}
""")
    print("PRODUITS GAGNANTS")
    for cle, p in sorted(par_produit.items(), key=lambda x: -x[1]["ventes"])[:10]:
        print(f"  {p['qte']:>4} vendus  {m(p['ventes']):>12}  marge {m(p['ventes'] - p['cout']):>10}  {p['titre'][:50]}")

    vendus = set(par_produit)
    sans_vente = []
    for f in (DONNEES / "produits").glob("*.json"):
        p = lire_json(f)
        if p.get("statut") == "actif" and p["fiche"]["handle"] not in vendus:
            sans_vente.append(p["fiche"]["titre"])
    if sans_vente:
        print(f"\nACTIFS SANS AUCUNE VENTE EN {a.jours} JOURS ({len(sans_vente)}) : à retravailler ou retirer")
        for t in sans_vente[:15]:
            print(f"  {t[:70]}")


if __name__ == "__main__":
    main()

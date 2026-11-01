"""Agent 4 : TABLEAU DE BORD ET DÉCISIONS PUB
Croise les vraies commandes Shopify avec les dépenses pub saisies (agent pub) et applique
les règles de config.json (regles_pub) : pour chaque produit, COUPER, BAISSER, CONTINUER LE TEST,
GARDER ou POUSSER, avec le budget conseillé pour le lendemain.

Usage : python boutique.py cadeaux tableau_de_bord [--jours 30]
"""

import argparse
from collections import defaultdict
from datetime import date, timedelta

import shopify
from commun import CONFIG, DONNEES, lire_csv, lire_json

REGLES = {"couper_si_depense_sans_vente": 40, "roas_cible": 2.5, "hausse_quotidienne": 0.25,
          "baisse_quotidienne": 0.3, "jours_recents": 3, "budget_test_total": 0, "frais_paiement": 0.03,
          **CONFIG.get("regles_pub", {})}
ORDRE = ["POUSSER", "GARDER", "CONTINUER LE TEST", "BAISSER", "COUPER"]


def m(x: float) -> str:
    return f"{x:,.2f}".replace(",", " ").replace(".", ",")


def n(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def catalogue() -> dict:
    """handle -> {titre, prix, cout, statut} à partir des fiches."""
    res = {}
    for f in (DONNEES / "produits").glob("*.json"):
        p = lire_json(f)
        if p.get("fiche"):
            v = p["fiche"]["variantes"][0]
            res[p["fiche"]["handle"]] = {"titre": p["fiche"]["titre"], "prix": float(v["prix"]),
                                         "cout": float(v.get("cout", 0)), "statut": p.get("statut")}
    return res


def decider(s: dict, prix: float, cout: float) -> tuple[str, str, float | None]:
    """Renvoie (décision, explication, budget conseillé demain)."""
    r = REGLES
    marge_u = prix - cout - prix * r["frais_paiement"]
    if marge_u <= 0:
        return "COUPER", "aucune marge au prix actuel", 0
    seuil = prix / marge_u  # ROAS en dessous duquel chaque vente fait perdre de l'argent
    roas = s["ventes"] / s["pub"] if s["pub"] else 0
    roas_r = s["ventes_r"] / s["pub_r"] if s["pub_r"] else 0
    dernier = s["dernier_jour"]

    if s["qte"] == 0 and s["pub"] >= r["couper_si_depense_sans_vente"]:
        return "COUPER", f"{m(s['pub'])} $ dépensés sans aucune vente", 0
    if s["qte"] and roas < seuil and s["pub"] >= 2 * marge_u * max(1, s["qte"]):
        return "COUPER", f"rendement {n(roas)} sous le seuil de rentabilité {n(seuil)} après un test suffisant", 0
    if s["qte_r"] >= 2 and roas_r >= r["roas_cible"]:
        return "POUSSER", f"rendement {n(roas_r)} sur {r['jours_recents']} jours (cible {n(r['roas_cible'])})", \
            round(dernier * (1 + r["hausse_quotidienne"]), 2)
    if s["qte_r"] and roas_r >= seuil:
        return "GARDER", f"rentable ({n(roas_r)}, seuil {n(seuil)}) mais pas encore assez pour accélérer", dernier
    if s["qte_r"] and roas_r < seuil:
        return "BAISSER", f"rendement {n(roas_r)} sous le seuil {n(seuil)} ces derniers jours", \
            round(dernier * (1 - r["baisse_quotidienne"]), 2)
    reste = max(0, r["couper_si_depense_sans_vente"] - s["pub"]) if not s["qte"] else None
    detail = f"encore {m(reste)} $ avant décision" if reste is not None else "pas assez de données récentes"
    return "CONTINUER LE TEST", detail, dernier or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jours", type=int, default=30)
    a = ap.parse_args()

    aujourd_hui = date.today()
    debut = (aujourd_hui - timedelta(days=a.jours)).isoformat()
    debut_r = (aujourd_hui - timedelta(days=REGLES["jours_recents"])).isoformat()
    commandes = [c for c in shopify.commandes(debut) if c["displayFinancialStatus"] not in ("VOIDED", "REFUNDED")]
    pubs = [p for p in lire_csv(DONNEES / "pub.csv") if p["date"] >= debut]
    cat = catalogue()

    s = defaultdict(lambda: {"titre": "", "qte": 0, "ventes": 0.0, "cout": 0.0, "pub": 0.0,
                             "qte_r": 0, "ventes_r": 0.0, "pub_r": 0.0, "dernier_jour": 0.0, "date_dernier": ""})
    for c in commandes:
        recent = c["createdAt"][:10] >= debut_r
        for l in c["lineItems"]["nodes"]:
            h = (l.get("product") or {}).get("handle") or l["title"]
            unite = float((((l.get("variant") or {}).get("inventoryItem") or {}).get("unitCost") or {}).get("amount") or 0)
            montant = float(l["originalTotalSet"]["shopMoney"]["amount"])
            x = s[h]
            x["titre"] = l["title"]
            x["qte"] += l["quantity"]
            x["ventes"] += montant
            x["cout"] += unite * l["quantity"]
            if recent:
                x["qte_r"] += l["quantity"]
                x["ventes_r"] += montant
    for p in pubs:
        x, d = s[p["produit"]], float(p["depense"])
        x["pub"] += d
        if p["date"] >= debut_r:
            x["pub_r"] += d
        if p["date"] > x["date_dernier"]:
            x["date_dernier"], x["dernier_jour"] = p["date"], 0.0
        if p["date"] == x["date_dernier"]:
            x["dernier_jour"] += d

    ventes = sum(float(c["totalPriceSet"]["shopMoney"]["amount"]) for c in commandes)
    cout = sum(x["cout"] for x in s.values())
    pub = sum(x["pub"] for x in s.values())
    frais = ventes * REGLES["frais_paiement"]
    net = ventes - cout - frais - pub
    a_expedier = [c["name"] for c in commandes if c["displayFulfillmentStatus"] in ("UNFULFILLED", "PARTIALLY_FULFILLED")]

    print(f"""
{CONFIG['boutique'].upper()} : {a.jours} DERNIERS JOURS ({CONFIG['devise']})
  Commandes               {len(commandes)}
  Ventes                  {m(ventes)}
  Panier moyen            {m(ventes / max(1, len(commandes)))}
  Coût produits+livraison {m(cout)}
  Frais de paiement       {m(frais)}
  Publicité               {m(pub)}   rendement global {n(ventes / pub if pub else 0)} $ de ventes par $ de pub
  PROFIT NET ESTIMÉ       {m(net)}
  Commandes à expédier    {len(a_expedier)} {' '.join(a_expedier[:10])}""")

    # ------------------------------------------------ décisions par produit
    lignes = []
    for h, x in s.items():
        if h == "general" or x["pub"] == 0:
            continue
        info = cat.get(h)
        prix = info["prix"] if info else (x["ventes"] / x["qte"] if x["qte"] else 0)
        cout_u = info["cout"] if info else (x["cout"] / x["qte"] if x["qte"] else 0)
        decision, pourquoi, budget = decider(x, prix, cout_u)
        profit = x["ventes"] - x["cout"] - x["ventes"] * REGLES["frais_paiement"] - x["pub"]
        lignes.append((ORDRE.index(decision), decision, (info or {}).get("titre") or x["titre"] or h,
                       x, profit, pourquoi, budget))

    if lignes:
        print("\nDÉCISIONS PUB PAR PRODUIT")
        for _, decision, titre, x, profit, pourquoi, budget in sorted(lignes, key=lambda l: (l[0], -l[4])):
            demain = "arrêter la pub" if budget == 0 else (f"{m(budget)} $ / jour" if budget else "budget de test")
            print(f"\n  [{decision}] {titre[:60]}")
            print(f"     pub {m(x['pub'])} $   ventes {x['qte']} ({m(x['ventes'])} $)   profit {m(profit)} $")
            print(f"     {pourquoi}  ->  demain : {demain}")
        gagnants = [l for l in lignes if l[1] in ("POUSSER", "GARDER")]
    else:
        gagnants = []
        print("\nAucune dépense pub saisie. Saisie : python boutique.py <boutique> pub ajouter <produit> <montant>")

    budget_test = REGLES["budget_test_total"]
    if budget_test:
        total_pub = sum(float(p["depense"]) for p in lire_csv(DONNEES / "pub.csv"))
        print(f"\nBUDGET DE TEST : {m(total_pub)} $ utilisés sur {m(budget_test)} $ ({total_pub / budget_test:.0%})")
        if total_pub >= budget_test and not gagnants:
            print("  ALERTE : budget de test épuisé sans produit rentable. Règle fixée d'avance : arrêter la pub,"
                  "\n  continuer en vidéos gratuites et revoir le choix des produits.")
        elif total_pub >= 0.8 * budget_test and not gagnants:
            print("  Attention : 80 % du budget de test utilisé sans produit rentable.")

    # ------------------------------------------------ produits sans vente (organique)
    sans_vente = [i["titre"] for h, i in cat.items() if i["statut"] == "actif" and s.get(h, {}).get("qte", 0) == 0
                  and s.get(h, {}).get("pub", 0) == 0]
    if sans_vente:
        print(f"\nEN VENTE SANS PUB NI VENTE EN {a.jours} JOURS ({len(sans_vente)}) : nouvelles vidéos ou retrait")
        for t in sans_vente[:10]:
            print(f"  {t[:70]}")


if __name__ == "__main__":
    main()

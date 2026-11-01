"""Client CJ Dropshipping (API 2.0) : recherche de produits, détails, frais de livraison.

Clé : sur cjdropshipping.com, menu Mon CJ > Autorisation > API, générer la clé et la mettre dans
CJ_CLE_API (.env). Le jeton obtenu dure environ 15 jours et il est gardé en cache
(CJ n'autorise qu'une demande de jeton toutes les 5 minutes).

Vérification rapide : python agents/cj.py "dog harness"
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse

from commun import DONNEES, ecrire_json, http_json, lire_json

BASE = "https://developers.cjdropshipping.com/api2.0/v1"
_CACHE = DONNEES / ".jeton_cj.json"


def jeton() -> str:
    cache = lire_json(_CACHE, {})
    if cache.get("jeton") and cache.get("expire", 0) > time.time() + 3600:
        return cache["jeton"]
    r = http_json("POST", f"{BASE}/authentication/getAccessToken", {"apiKey": os.environ["CJ_CLE_API"]})
    if not r.get("result"):
        raise RuntimeError(f"CJ : {r.get('message')}")
    ecrire_json(_CACHE, {"jeton": r["data"]["accessToken"], "expire": time.time() + 14 * 86400})
    return r["data"]["accessToken"]


def appel(methode: str, chemin: str, params: dict | None = None, corps: dict | None = None):
    url = f"{BASE}{chemin}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    r = http_json(methode, url, corps, {"CJ-Access-Token": jeton()})
    if not r.get("result"):
        raise RuntimeError(f"CJ {chemin} : {r.get('message')}")
    time.sleep(1.1)  # limite de débit CJ
    return r.get("data")


def chercher(mot_cle: str, taille: int = 20) -> list[dict]:
    d = appel("GET", "/product/list", {"productNameEn": mot_cle, "pageNum": 1, "pageSize": taille})
    return (d or {}).get("list", [])


def _images(p: dict) -> list[str]:
    brut = p.get("productImageSet") or p.get("productImage") or []
    if isinstance(brut, str):
        try:
            brut = json.loads(brut)
        except json.JSONDecodeError:
            brut = [brut]
    return [u for u in brut if isinstance(u, str) and u.startswith("http")]


def livraison(vid: str, destination: str = "CA", depart: str = "CN") -> tuple[float, str, str]:
    """Option la moins chère : (prix USD, délai 'min-max' jours, nom du transporteur)."""
    try:
        options = appel("POST", "/logistic/freightCalculate", corps={
            "startCountryCode": depart, "endCountryCode": destination, "products": [{"quantity": 1, "vid": vid}]})
    except RuntimeError:
        return 0.0, "", ""
    if not options:
        return 0.0, "", ""
    o = min(options, key=lambda o: float(o.get("logisticPrice") or 999))
    return float(o.get("logisticPrice") or 0), str(o.get("logisticAging") or ""), o.get("logisticName", "")


def produit(pid: str, destination: str = "CA") -> dict:
    """Détails normalisés d'un produit CJ, prêts pour l'agent des fiches."""
    p = appel("GET", "/product/query", {"pid": pid})
    noms_options = [n.strip() for n in re.split(r"[-/]", p.get("productKeyEn") or "") if n.strip()]
    variantes = []
    for v in p.get("variants") or []:
        morceaux = [m.strip() for m in (v.get("variantKey") or "").split("-")]
        if noms_options and len(morceaux) == len(noms_options):
            valeurs = dict(zip(noms_options, morceaux))
        else:
            valeurs = {"Modèle": v.get("variantKey") or v.get("variantNameEn") or v.get("variantSku")}
        variantes.append({"vid": v.get("vid"), "sku": v.get("variantSku", ""), "valeurs": valeurs,
                          "cout_usd": float(v.get("variantSellPrice") or p.get("sellPrice") or 0),
                          "image": v.get("variantImage") or "", "poids_g": v.get("variantWeight")})
    if not variantes:
        raise RuntimeError(f"Produit {pid} sans variante")
    frais, delai, transporteur = livraison(variantes[0]["vid"], destination)
    return {
        "source": "cj", "id": pid, "titre_source": p.get("productNameEn", ""),
        "description_source": re.sub(r"<[^>]+>", " ", p.get("description") or "")[:4000],
        "categorie_source": p.get("categoryName", ""), "images": _images(p), "variantes": variantes,
        "cout_usd": max(v["cout_usd"] for v in variantes), "livraison_usd": frais,
        "delai_jours": delai, "transporteur": transporteur,
        "lien_fournisseur": f"https://cjdropshipping.com/product/-p-{pid}.html",
    }


if __name__ == "__main__":
    for r in chercher(" ".join(sys.argv[1:]) or "pet", 5):
        print(r.get("pid"), r.get("sellPrice"), r.get("productNameEn"))

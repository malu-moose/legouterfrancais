"""Client Shopify (Admin GraphQL API).

Accès : créer une app dans le Dev Dashboard Shopify (dev.shopify.com), l'installer sur la boutique,
avec les permissions write_products, read_products, read_orders, read_publications, write_publications.
Mettre SHOPIFY_CLIENT_ID et SHOPIFY_CLIENT_SECRET dans .env : le jeton (valable 24 h) est
généré et renouvelé automatiquement. Si tu as déjà un jeton, mets-le dans SHOPIFY_JETON.

Vérification rapide : python agents/shopify.py
"""

from __future__ import annotations

import os
import time

from commun import DONNEES, ecrire_json, http_json, lire_json

VERSION = os.environ.get("SHOPIFY_VERSION", "2026-10")
_CACHE = DONNEES / ".jeton_shopify.json"


def _boutique() -> str:
    b = os.environ.get("SHOPIFY_BOUTIQUE", "").replace("https://", "").strip("/")
    if not b:
        raise RuntimeError("SHOPIFY_BOUTIQUE manquant dans .env (ex. ma-boutique.myshopify.com)")
    return b


def jeton() -> str:
    if os.environ.get("SHOPIFY_JETON"):
        return os.environ["SHOPIFY_JETON"]
    cache = lire_json(_CACHE, {})
    if cache.get("jeton") and cache.get("expire", 0) > time.time() + 300:
        return cache["jeton"]
    r = http_json("POST", f"https://{_boutique()}/admin/oauth/access_token", {
        "grant_type": "client_credentials",
        "client_id": os.environ["SHOPIFY_CLIENT_ID"],
        "client_secret": os.environ["SHOPIFY_CLIENT_SECRET"],
    }, formulaire=True)
    ecrire_json(_CACHE, {"jeton": r["access_token"], "expire": time.time() + int(r.get("expires_in", 86000))})
    return r["access_token"]


def gql(requete: str, variables: dict | None = None) -> dict:
    url = f"https://{_boutique()}/admin/api/{VERSION}/graphql.json"
    for essai in range(5):
        r = http_json("POST", url, {"query": requete, "variables": variables or {}},
                      {"X-Shopify-Access-Token": jeton()})
        erreurs = r.get("errors")
        if erreurs and any(e.get("extensions", {}).get("code") == "THROTTLED" for e in erreurs):
            time.sleep(2 ** essai)
            continue
        if erreurs:
            raise RuntimeError(f"Erreur Shopify : {erreurs}")
        return r["data"]
    raise RuntimeError("Shopify : trop de requêtes, réessaie plus tard")


def _verifier(resultat: dict, nom: str) -> dict:
    erreurs = resultat[nom].get("userErrors") or []
    if erreurs:
        raise RuntimeError(f"{nom} : " + "; ".join(f"{e.get('field')}: {e['message']}" for e in erreurs))
    return resultat[nom]


# ---------------------------------------------------------------- Produits

def produit_existe(handle: str) -> str | None:
    d = gql("query($q:String!){products(first:1,query:$q){nodes{id handle}}}", {"q": f"handle:{handle}"})
    noeuds = [n for n in d["products"]["nodes"] if n["handle"] == handle]
    return noeuds[0]["id"] if noeuds else None


CREER = """
mutation creer($produit: ProductCreateInput!, $media: [CreateMediaInput!]) {
  productCreate(product: $produit, media: $media) {
    product { id handle variants(first: 1) { nodes { id } } }
    userErrors { field message }
  }
}"""

VARIANTES = """
mutation variantes($id: ID!, $variantes: [ProductVariantsBulkInput!]!) {
  productVariantsBulkCreate(productId: $id, variants: $variantes, strategy: REMOVE_STANDALONE_VARIANT) {
    productVariants { id sku }
    userErrors { field message }
  }
}"""

MAJ_VARIANTE = """
mutation maj($id: ID!, $variantes: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $id, variants: $variantes) {
    productVariants { id }
    userErrors { field message }
  }
}"""


def creer_produit(fiche: dict, statut: str = "DRAFT") -> str:
    """fiche : titre, description_html, handle, type, tags, seo_titre, seo_description, fournisseur,
    images [url], options [{nom, valeurs}], variantes [{valeurs {option: valeur}, prix, cout, sku, image}]"""
    existant = produit_existe(fiche["handle"])
    if existant:
        return existant

    produit = {
        "title": fiche["titre"], "descriptionHtml": fiche["description_html"], "handle": fiche["handle"],
        "productType": fiche.get("type", ""), "vendor": fiche.get("fournisseur") or "",
        "tags": fiche.get("tags", []), "status": statut,
        "seo": {"title": fiche.get("seo_titre", ""), "description": fiche.get("seo_description", "")},
    }
    if fiche.get("options"):
        produit["productOptions"] = [{"name": o["nom"], "values": [{"name": v} for v in o["valeurs"]]}
                                     for o in fiche["options"]]
    media = [{"originalSource": u, "mediaContentType": "IMAGE", "alt": fiche["titre"]}
             for u in fiche.get("images", [])[:10]]
    p = _verifier(gql(CREER, {"produit": produit, "media": media}), "productCreate")["product"]

    def entree(v: dict) -> dict:
        e = {"price": f"{v['prix']:.2f}", "inventoryPolicy": "CONTINUE",
             "inventoryItem": {"sku": v.get("sku", ""), "tracked": False, "cost": f"{v.get('cout', 0):.2f}",
                               "requiresShipping": True}}
        if fiche.get("options"):
            e["optionValues"] = [{"optionName": o, "name": val} for o, val in v["valeurs"].items()]
        return e

    if fiche.get("options"):
        variantes = [entree(v) for v in fiche["variantes"]]
        avec_images = [dict(e, mediaSrc=[v["image"]]) if v.get("image") else e
                       for e, v in zip(variantes, fiche["variantes"])]
        try:
            _verifier(gql(VARIANTES, {"id": p["id"], "variantes": avec_images}), "productVariantsBulkCreate")
        except RuntimeError as err:
            if "media" not in str(err).lower():
                raise
            _verifier(gql(VARIANTES, {"id": p["id"], "variantes": variantes}), "productVariantsBulkCreate")
    else:
        e = entree(fiche["variantes"][0]) | {"id": p["variants"]["nodes"][0]["id"]}
        _verifier(gql(MAJ_VARIANTE, {"id": p["id"], "variantes": [e]}), "productVariantsBulkUpdate")
    return p["id"]


def publier_boutique_en_ligne(produit_id: str):
    """Rend le produit actif et visible sur la boutique en ligne."""
    _verifier(gql("mutation($p:ProductUpdateInput!){productUpdate(product:$p){product{id} userErrors{field message}}}",
                  {"p": {"id": produit_id, "status": "ACTIVE"}}), "productUpdate")
    pubs = gql("{publications(first:20){nodes{id name}}}")["publications"]["nodes"]
    cible = next((p for p in pubs if p["name"] in ("Online Store", "Boutique en ligne")), None)
    if not cible:
        raise RuntimeError(f"Canal Boutique en ligne introuvable parmi {[p['name'] for p in pubs]}")
    _verifier(gql("mutation($id:ID!,$i:[PublicationInput!]!){publishablePublish(id:$id,input:$i){userErrors{field message}}}",
                  {"id": produit_id, "i": [{"publicationId": cible["id"]}]}), "publishablePublish")


# ---------------------------------------------------------------- Commandes

COMMANDES = """
query($q:String!,$apres:String){orders(first:100,after:$apres,query:$q,sortKey:CREATED_AT){
  pageInfo{hasNextPage endCursor}
  nodes{name createdAt displayFinancialStatus displayFulfillmentStatus
    totalPriceSet{shopMoney{amount currencyCode}}
    lineItems(first:50){nodes{title quantity sku
      originalTotalSet{shopMoney{amount}}
      variant{inventoryItem{unitCost{amount}}} product{id handle}}}}}}"""


def commandes(depuis_iso: str) -> list[dict]:
    resultats, apres = [], None
    while True:
        d = gql(COMMANDES, {"q": f"created_at:>={depuis_iso}", "apres": apres})["orders"]
        resultats += d["nodes"]
        if not d["pageInfo"]["hasNextPage"]:
            return resultats
        apres = d["pageInfo"]["endCursor"]


if __name__ == "__main__":
    info = gql("{shop{name currencyCode primaryDomain{url}} productsCount{count}}")
    print(f"Connecté à {info['shop']['name']} ({info['shop']['primaryDomain']['url']}), "
          f"devise {info['shop']['currencyCode']}, {info['productsCount']['count']} produits.")

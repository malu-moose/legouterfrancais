"""Briques partagées : configuration, secrets (.env), appels à Claude, HTTP, CSV/JSON."""

from __future__ import annotations

import csv
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- Boutique active
# Chaque boutique a son dossier boutiques/<nom>/ : config.json, .env (accès Shopify), donnees/.
# On la choisit avec le lanceur : python boutique.py <nom> <agent> ...

_disponibles = sorted(p.name for p in (RACINE / "boutiques").iterdir() if (p / "config.json").exists())
BOUTIQUE = os.environ.get("BOUTIQUE") or (_disponibles[0] if len(_disponibles) == 1 else "")
if BOUTIQUE not in _disponibles:
    raise SystemExit(f"Choisis une boutique parmi {_disponibles} : python boutique.py <nom> <agent>")
DOSSIER_BOUTIQUE = RACINE / "boutiques" / BOUTIQUE
DONNEES = DOSSIER_BOUTIQUE / "donnees"
DONNEES.mkdir(exist_ok=True)
CONFIG = json.loads((DOSSIER_BOUTIQUE / "config.json").read_text(encoding="utf-8"))

# ---------------------------------------------------------------- .env
# D'abord celui de la boutique (accès Shopify), puis celui de la racine (clés communes).

for _env in (DOSSIER_BOUTIQUE / ".env", RACINE / ".env"):
    if _env.exists():
        for ligne in _env.read_text(encoding="utf-8").splitlines():
            if "=" in ligne and not ligne.lstrip().startswith("#"):
                cle, val = ligne.split("=", 1)
                if val.strip() and not os.environ.get(cle.strip()):
                    os.environ[cle.strip()] = val.strip()

MODELE = os.environ.get("MODELE_CLAUDE", "claude-opus-5-5")

# ---------------------------------------------------------------- Claude

RECHERCHE_WEB = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 15}]
_client = None


def claude(systeme: str, message, effort: str = "medium", max_tokens: int = 32000,
           outils: list | None = None) -> str:
    """Un appel à Claude, renvoie le texte. `message` peut être une chaîne ou une liste de blocs
    (texte + images). Repli automatique côté serveur en cas de refus."""
    global _client
    import anthropic

    if _client is None:
        _client = anthropic.Anthropic()
    messages = [{"role": "user", "content": message}]
    options = {"tools": outils} if outils else {}
    for _ in range(6):  # reprises si la recherche web met le tour en pause
        with _client.beta.messages.stream(
            model=MODELE, max_tokens=max_tokens, system=systeme,
            output_config={"effort": effort},
            betas=["server-side-fallback-2026-07-01"], extra_body={"fallbacks": "default"},
            messages=messages, **options,
        ) as flux:
            reponse = flux.get_final_message()
        if reponse.stop_reason != "pause_turn":
            break
        messages = [messages[0], {"role": "assistant", "content": reponse.content}]
    if reponse.stop_reason == "refusal":
        raise RuntimeError("Claude a refusé la requête")
    return "".join(b.text for b in reponse.content if b.type == "text").strip()


def extraire_json(texte: str):
    texte = re.sub(r"```(?:json)?", "", texte)
    debut = min([i for i in (texte.find("{"), texte.find("[")) if i >= 0], default=0)
    return json.JSONDecoder().raw_decode(texte[debut:])[0]


def claude_json(systeme: str, message, effort: str = "medium", **options):
    texte = claude(systeme + "\nTermine par du JSON valide uniquement, sans commentaire après.",
                   message, effort, **options)
    return extraire_json(texte)


# ---------------------------------------------------------------- HTTP


def http_json(methode: str, url: str, corps=None, entetes: dict | None = None, formulaire: bool = False):
    donnees = None
    h = {"Accept": "application/json", **(entetes or {})}
    if corps is not None:
        if formulaire:
            import urllib.parse
            donnees = urllib.parse.urlencode(corps).encode()
            h["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            donnees = json.dumps(corps).encode()
            h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=donnees, headers=h, method=methode)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} sur {url} : {e.read().decode()[:500]}") from None


# ---------------------------------------------------------------- Fichiers


def lire_csv(chemin: Path) -> list[dict]:
    if not chemin.exists():
        return []
    with chemin.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ecrire_csv(chemin: Path, lignes: list[dict]):
    if not lignes:
        return
    colonnes = list(dict.fromkeys(k for l in lignes for k in l))
    with chemin.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colonnes)
        w.writeheader()
        w.writerows(lignes)


def lire_json(chemin: Path, defaut=None):
    return json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else defaut


def ecrire_json(chemin: Path, donnees):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- Prix


def prix_de_vente(cout_usd: float, livraison_usd: float) -> float:
    """Prix psychologique en devise locale : (coût + livraison) x multiplicateur, terminé par ,99,
    borné par la marge minimale et la fourchette de prix de la configuration."""
    cout = (cout_usd + livraison_usd) * CONFIG["taux_usd_vers_devise"]
    prix = max(cout * CONFIG["multiplicateur_prix"], cout + CONFIG["marge_min_devise"], CONFIG["prix_min"])
    return round(int(prix) + 0.99, 2)


def rentable(cout_usd: float, livraison_usd: float) -> bool:
    return prix_de_vente(cout_usd, livraison_usd) <= CONFIG["prix_max"]

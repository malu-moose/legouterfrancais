"""Briques partagées par tous les agents : appel à Claude, lecture de pages web,
détection de langue, lecture/écriture CSV."""

from __future__ import annotations

import csv
import json
import os
import re
import ssl
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DONNEES = RACINE / "donnees"
DONNEES.mkdir(exist_ok=True)

MODELE = os.environ.get("MODELE_CLAUDE", "claude-opus-5-5")
USER_AGENT = "Mozilla/5.0 (compatible; AuditFrancisation/1.0)"

# ---------------------------------------------------------------- Claude

_client = None


RECHERCHE_WEB = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 15}]


def claude(systeme: str, message: str, effort: str = "medium", max_tokens: int = 16000,
           outils: list | None = None) -> str:
    """Un appel à Claude, renvoie le texte. Repli automatique côté serveur si refus.
    outils=RECHERCHE_WEB donne à Claude l'accès à la recherche web."""
    global _client
    import anthropic  # importé ici pour que les parties sans IA tournent sans le SDK

    if _client is None:
        _client = anthropic.Anthropic()
    messages = [{"role": "user", "content": message}]
    options = {"tools": outils} if outils else {}
    for _ in range(6):  # reprises si la recherche web met le tour en pause
        with _client.beta.messages.stream(
            model=MODELE,
            max_tokens=max_tokens,
            system=systeme,
            output_config={"effort": effort},
            betas=["server-side-fallback-2026-07-01"],
            extra_body={"fallbacks": "default"},
            messages=messages,
            **options,
        ) as flux:
            reponse = flux.get_final_message()
        if reponse.stop_reason != "pause_turn":
            break
        messages = [messages[0], {"role": "assistant", "content": reponse.content}]
    if reponse.stop_reason == "refusal":
        raise RuntimeError("Claude a refusé la requête")
    return "".join(b.text for b in reponse.content if b.type == "text").strip()


def extraire_json(texte: str):
    """Récupère le premier objet JSON dans une réponse (avec ou sans ```)."""
    texte = re.sub(r"```(?:json)?", "", texte)
    debut = min([i for i in (texte.find("{"), texte.find("[")) if i >= 0], default=0)
    return json.JSONDecoder().raw_decode(texte[debut:])[0]


def claude_json(systeme: str, message: str, effort: str = "medium", **options):
    """Appel à Claude qui doit renvoyer du JSON."""
    texte = claude(systeme + "\nTermine par du JSON valide uniquement, sans commentaire après.",
                   message, effort, **options)
    return extraire_json(texte)


# ---------------------------------------------------------------- Web


def telecharger(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "fr-CA,fr;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
        type_contenu = r.headers.get("Content-Type", "")
        if "html" not in type_contenu:
            return ""
        return r.read(2_000_000).decode(r.headers.get_content_charset() or "utf-8", "replace")


class _Extracteur(HTMLParser):
    IGNORE = {"script", "style", "noscript", "svg", "template", "code", "pre"}
    BLOCS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "a", "button", "label",
             "option", "figcaption", "blockquote", "dt", "dd", "span", "div", "title"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.segments: list[str] = []
        self.liens: list[str] = []
        self.courriels: list[str] = []
        self.lang = ""
        self._pile_ignore = 0
        self._courant: list[str] = []

    def _vider(self):
        texte = " ".join("".join(self._courant).split())
        if texte:
            self.segments.append(texte)
        self._courant = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html" and a.get("lang"):
            self.lang = a["lang"].lower()
        if tag in self.IGNORE:
            self._pile_ignore += 1
        if tag == "a" and a.get("href"):
            if a["href"].lower().startswith("mailto:"):
                self.courriels.append(a["href"][7:].split("?")[0])
            else:
                self.liens.append(a["href"])
        for attr in ("alt", "placeholder", "title", "aria-label"):
            if a.get(attr) and len(a[attr]) > 2:
                self.segments.append(" ".join(a[attr].split()))
        if tag == "meta" and a.get("name", "").lower() == "description" and a.get("content"):
            self.segments.append(" ".join(a["content"].split()))
        if tag in self.BLOCS or tag == "br":
            self._vider()

    def handle_endtag(self, tag):
        if tag in self.IGNORE and self._pile_ignore:
            self._pile_ignore -= 1
        if tag in self.BLOCS:
            self._vider()

    def handle_data(self, data):
        if not self._pile_ignore:
            self._courant.append(data)

    def close(self):
        super().close()
        self._vider()


def analyser_html(html: str, url_base: str) -> dict:
    ex = _Extracteur()
    ex.feed(html)
    ex.close()
    vus, segments = set(), []
    for s in ex.segments:
        if s not in vus and re.search(r"[A-Za-zÀ-ÿ]{2}", s):
            vus.add(s)
            segments.append(s)
    hote = urllib.parse.urlparse(url_base).netloc
    liens = []
    for href in ex.liens:
        absolu = urllib.parse.urljoin(url_base, href).split("#")[0]
        p = urllib.parse.urlparse(absolu)
        if p.scheme in ("http", "https") and p.netloc == hote and not re.search(
            r"\.(pdf|jpe?g|png|gif|svg|zip|mp4|webp|docx?|xlsx?)$", p.path, re.I
        ):
            liens.append(absolu)
    courriels = ex.courriels + RE_COURRIEL.findall(" ".join(ex.segments))
    courriels = [c.strip().lower() for c in courriels
                 if not re.search(r"\.(png|jpe?g|gif|webp|svg)$|example\.|sentry|wixpress|@2x", c, re.I)]
    return {"lang": ex.lang, "segments": segments, "liens": list(dict.fromkeys(liens)),
            "courriels": list(dict.fromkeys(courriels))}


RE_COURRIEL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PAGES_CONTACT = re.compile(r"contact|nous-joindre|joindre|about|a-propos|propos|equipe|team", re.I)


def explorer_site(url: str, max_pages: int = 30) -> list[dict]:
    """Parcours des pages internes d'un site, pages Contact en premier.
    Renvoie [{url, lang, segments, courriels}]."""
    a_visiter, visitees, pages = [url], set(), []
    while a_visiter and len(pages) < max_pages:
        courante = a_visiter.pop(0)
        if courante in visitees:
            continue
        visitees.add(courante)
        try:
            html = telecharger(courante)
        except Exception:
            continue
        if not html:
            continue
        info = analyser_html(html, courante)
        pages.append({"url": courante, "lang": info["lang"], "segments": info["segments"],
                      "courriels": info["courriels"]})
        nouveaux = [l for l in info["liens"] if l not in visitees and l not in a_visiter]
        a_visiter = [l for l in nouveaux if PAGES_CONTACT.search(l)] + a_visiter + \
                    [l for l in nouveaux if not PAGES_CONTACT.search(l)]
    return pages


def meilleur_courriel(pages: list[dict], site: str) -> tuple[str, str]:
    """Choisit l'adresse générique publiée sur le domaine de l'entreprise (info@, contact@...).
    Renvoie (courriel, page où il est publié) : la page sert de preuve LCAP."""
    dom = urllib.parse.urlparse(site).netloc.lower().removeprefix("www.")
    trouves = [(c, p["url"]) for p in pages for c in p.get("courriels", [])]
    if not trouves:
        return "", ""
    rang = lambda c: (  # noqa: E731
        0 if c[0].endswith("@" + dom) else 1,
        0 if re.match(r"(info|contact|bonjour|hello|admin|bureau|office|sales|ventes)@", c[0]) else 1,
    )
    return sorted(trouves, key=rang)[0]


# ---------------------------------------------------------------- Langue

_MOTS_FR = set("le la les des du de un une et est pour avec dans sur nous vous votre vos notre nos qui que pas plus "
               "au aux ce cette ces son sa ses leur sont être avoir fait par mais ou où très tout tous".split())
_MOTS_EN = set("the and for with your our you we are is to of in on this that from by be have has more all "
               "about contact us shop cart home services learn get now free new".split())


def part_anglais(segments: list[str]) -> float:
    """Proportion (0 à 1) des mots fonctionnels anglais parmi les mots fonctionnels FR+EN détectés."""
    fr = en = 0
    for s in segments:
        for mot in re.findall(r"[a-zà-ÿ']+", s.lower()):
            if mot in _MOTS_FR:
                fr += 1
            elif mot in _MOTS_EN:
                en += 1
    return en / (fr + en) if fr + en else 0.0


def nombre_mots(segments: list[str]) -> int:
    return sum(len(s.split()) for s in segments)


# ---------------------------------------------------------------- CSV


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

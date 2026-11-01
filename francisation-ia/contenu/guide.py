"""Agent 6 : AUTEUR DE GUIDES PDF
Écrit un guide complet (plan, chapitres, exercices, liste de vérification),
le met en page, le convertit en PDF et rédige sa page de vente.

Usage : python contenu/guide.py "Titre du sujet"      (ou --meilleur : le sujet au plus fort potentiel)
Sortie : donnees/guides/<slug>/guide.html, guide.pdf, vente.html

PDF : utilise WeasyPrint s'il est installé (pip install weasyprint), sinon Playwright,
sinon ouvre guide.html dans Chrome et fais Imprimer > Enregistrer en PDF.
"""

import argparse
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agents"))
from commun import DONNEES, claude, claude_json, ecrire_csv, lire_csv  # noqa: E402

CONFIG = json.loads((Path(__file__).parent / "config.json").read_text(encoding="utf-8"))
CONTEXTE = (f"Marque : {CONFIG['marque']}\nNiche : {CONFIG['niche']}\nAudience : {CONFIG['audience']}\n"
            f"Ton : {CONFIG['ton']}\nInterdits : {', '.join(CONFIG['interdits'])}")

SYSTEME_PLAN = f"""Tu es auteur de guides pratiques à succès en français du Québec.
{CONTEXTE}
Un bon guide à 27 $ : 25 à 40 pages, une promesse tenue, des étapes actionnables,
des exemples concrets québécois, des modèles à copier, zéro remplissage."""

SYSTEME_CHAPITRE = f"""Tu écris un chapitre d'un guide pratique payant, en français du Québec.
{CONTEXTE}
Écris en HTML simple uniquement (h2, h3, p, ul, ol, li, strong, em, table, blockquote,
et <div class="encadre"> pour les modèles à copier ou les astuces).
Pas de balise html, head ou body. Pas d'emoji. Chaque section doit faire agir le lecteur.
Si tu cites un outil ou un prix, reste prudent et indique que les offres changent.
Ne donne pas de conseil juridique ou fiscal personnalisé."""


def slug(texte: str) -> str:
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:60]


def ecrire_guide(sujet: dict) -> Path:
    dossier = DONNEES / "guides" / slug(sujet["titre"])
    dossier.mkdir(parents=True, exist_ok=True)

    plan = claude_json(SYSTEME_PLAN, f"""Sujet : {sujet['titre']}
Promesse : {sujet.get('promesse', '')}
Problème de l'audience : {sujet.get('probleme', '')}
Fais le plan. JSON : {{"titre": "...", "sous_titre": "...", "introduction": "2 paragraphes en HTML <p>",
"chapitres": [{{"titre": "...", "objectif": "ce que le lecteur saura faire", "points": ["..."]}}] (6 à 9 chapitres),
"liste_verification": ["10 actions à cocher"]}}""", effort="high")
    (dossier / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    chapitres = []
    for i, ch in enumerate(plan["chapitres"], 1):
        print(f"  chapitre {i}/{len(plan['chapitres'])} : {ch['titre']}")
        corps = claude(SYSTEME_CHAPITRE, f"""Guide : {plan['titre']}
Plan complet : {json.dumps([c['titre'] for c in plan['chapitres']], ensure_ascii=False)}
Chapitre {i} : {ch['titre']}
Objectif : {ch['objectif']}
Points à couvrir : {json.dumps(ch['points'], ensure_ascii=False)}
Longueur : 900 à 1 400 mots. Commence directement par le contenu (le titre est déjà affiché).""",
                       effort="medium", max_tokens=32000)
        corps = re.sub(r"```(?:html)?", "", corps)
        chapitres.append((ch["titre"], corps))

    page = mettre_en_page(plan, chapitres)
    (dossier / "guide.html").write_text(page, encoding="utf-8")
    convertir_pdf(dossier / "guide.html", dossier / "guide.pdf")
    (dossier / "vente.html").write_text(page_de_vente(plan), encoding="utf-8")
    return dossier


def mettre_en_page(plan: dict, chapitres: list) -> str:
    toc = "".join(f"<li>{html.escape(t)}</li>" for t, _ in chapitres)
    corps = "".join(f'<section class="chap"><h1><span>Chapitre {i}</span>{html.escape(t)}</h1>{c}</section>'
                    for i, (t, c) in enumerate(chapitres, 1))
    liste = "".join(f"<li>{html.escape(x)}</li>" for x in plan.get("liste_verification", []))
    return f"""<!doctype html><html lang="fr-CA"><head><meta charset="utf-8"><title>{html.escape(plan['titre'])}</title>
<style>
@page {{ size: Letter; margin: 22mm 20mm; @bottom-center {{ content: counter(page); color:#889; font-size:9pt }} }}
body {{ font: 11.5pt/1.6 Georgia, serif; color:#1b1f2a }}
h1,h2,h3 {{ font-family: system-ui, sans-serif; color:#0b3d91 }}
.couv {{ height: 230mm; display:flex; flex-direction:column; justify-content:center; page-break-after:always }}
.couv h1 {{ font-size: 34pt; line-height:1.1; margin:0 0 12px }} .couv p {{ font-size:15pt; color:#5b6475 }}
.couv .marque {{ margin-top:60px; font: 700 12pt system-ui; letter-spacing:.1em; text-transform:uppercase }}
.chap {{ page-break-before: always }} .chap h1 span {{ display:block; font-size:11pt; color:#889; text-transform:uppercase }}
.encadre {{ background:#eef3fc; border-left:4px solid #0b3d91; padding:10px 14px; margin:14px 0; font-family: system-ui, sans-serif; font-size:10.5pt }}
table {{ border-collapse:collapse; width:100% }} td,th {{ border:1px solid #ccd; padding:6px; font-size:10pt }}
blockquote {{ font-style:italic; color:#444; border-left:3px solid #ccd; margin-left:0; padding-left:12px }}
.verif li {{ list-style:"☐  "; margin:6px 0 }}
</style></head><body>
<div class="couv"><h1>{html.escape(plan['titre'])}</h1><p>{html.escape(plan.get('sous_titre', ''))}</p>
<div class="marque">{html.escape(CONFIG['marque'])}</div></div>
<section><h2>Introduction</h2>{plan.get('introduction', '')}<h2>Au programme</h2><ol>{toc}</ol></section>
{corps}
<section class="chap"><h1><span>Pour passer à l'action</span>Liste de vérification</h1><ul class="verif">{liste}</ul>
<p>Pour aller plus loin : {html.escape(CONFIG['echelle_de_prix'][1]['produit'])}, sur {html.escape(CONFIG['lien_bio'])}</p></section>
</body></html>"""


def convertir_pdf(source: Path, cible: Path):
    try:
        from weasyprint import HTML
        HTML(filename=str(source)).write_pdf(str(cible))
        print(f"PDF : {cible}")
        return
    except ImportError:
        pass
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            nav = p.chromium.launch()
            page = nav.new_page()
            page.goto(source.resolve().as_uri())
            page.pdf(path=str(cible), format="Letter", print_background=True,
                     margin={"top": "22mm", "bottom": "22mm", "left": "20mm", "right": "20mm"})
            nav.close()
        print(f"PDF : {cible}")
    except ImportError:
        print(f"Ouvre {source} dans Chrome, puis Imprimer > Enregistrer en PDF (ou pip install weasyprint).")


def page_de_vente(plan: dict) -> str:
    v = claude_json(f"Tu es rédacteur publicitaire québécois. {CONTEXTE}\nAucune promesse de revenus. Aucun emoji.",
                    f"""Page de vente pour le guide « {plan['titre']} » à {CONFIG['echelle_de_prix'][0]['prix']} $.
Plan : {json.dumps([c['titre'] for c in plan['chapitres']], ensure_ascii=False)}
JSON : {{"titre": "...", "sous_titre": "...", "douleurs": ["3"], "benefices": ["6"], "pour_qui": ["3"],
"pas_pour_qui": ["2"], "faq": [{{"q": "...", "r": "..."}}] (5), "garantie": "1 phrase"}}""", effort="low")
    li = lambda xs: "".join(f"<li>{html.escape(x)}</li>" for x in xs)  # noqa: E731
    faq = "".join(f"<details><summary>{html.escape(f['q'])}</summary><p>{html.escape(f['r'])}</p></details>" for f in v["faq"])
    prix = CONFIG["echelle_de_prix"][0]["prix"]
    return f"""<!doctype html><html lang="fr-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(plan['titre'])}</title><style>
:root{{--b:#0b3d91;--t:#1b1f2a;--f:#fff;--c:#f4f6fb}}@media (prefers-color-scheme:dark){{:root{{--b:#7aa7ff;--t:#e8ebf2;--f:#0e1220;--c:#171c2c}}}}
body{{margin:0;font:18px/1.6 system-ui,sans-serif;color:var(--t);background:var(--f)}}main{{max-width:720px;margin:auto;padding:40px 16px}}
h1{{font-size:clamp(30px,6vw,44px);line-height:1.1}}h2{{color:var(--b)}}section{{background:var(--c);border-radius:14px;padding:20px;margin:20px 0}}
.btn{{display:block;text-align:center;background:var(--b);color:var(--f);padding:18px;border-radius:12px;font-weight:800;text-decoration:none;font-size:20px}}
details{{margin:10px 0}}summary{{font-weight:700;cursor:pointer}}</style></head><body><main>
<h1>{html.escape(v['titre'])}</h1><p>{html.escape(v['sous_titre'])}</p>
<a class="btn" href="LIEN_PAIEMENT">Obtenir le guide, {prix} $</a>
<section><h2>Vous vous reconnaissez ?</h2><ul>{li(v['douleurs'])}</ul></section>
<section><h2>Ce que vous saurez faire</h2><ul>{li(v['benefices'])}</ul></section>
<section><h2>Pour qui</h2><ul>{li(v['pour_qui'])}</ul><h2>Pas pour qui</h2><ul>{li(v['pas_pour_qui'])}</ul></section>
<section><h2>Questions</h2>{faq}</section><p><strong>Garantie :</strong> {html.escape(v['garantie'])}</p>
<a class="btn" href="LIEN_PAIEMENT">Obtenir le guide, {prix} $</a></main></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("titre", nargs="?")
    ap.add_argument("--meilleur", action="store_true")
    a = ap.parse_args()
    sujets = lire_csv(DONNEES / "sujets.csv")
    if a.meilleur:
        candidats = sorted((s for s in sujets if s["statut"] == "idee"), key=lambda s: -int(s["potentiel"]))
        if not candidats:
            sys.exit("Aucun sujet en attente : lance d'abord contenu/veille.py")
        sujet = candidats[0]
    elif a.titre:
        sujet = next((s for s in sujets if s["titre"] == a.titre), {"titre": a.titre})
    else:
        ap.error("donne un titre ou --meilleur")

    print(f"Rédaction : {sujet['titre']}")
    dossier = ecrire_guide(sujet)
    if sujet in sujets:
        sujet["statut"] = "guide_ecrit"
        ecrire_csv(DONNEES / "sujets.csv", sujets)
    print(f"Terminé : {dossier}")


if __name__ == "__main__":
    main()

"""Agent 2 : AUDITEUR
Produit un rapport d'audit de francisation gratuit, personnalisé, en HTML.
C'est l'aimant à clients : on l'envoie en lien dans le courriel de prospection.

Usage : python agents/auditeur.py https://exemple.com "Nom de l'entreprise"
        python agents/auditeur.py --tous      (tous les prospects qualifiés sans audit)
Sortie : donnees/audits/<domaine>.html
"""

import argparse
import html
import os
import urllib.parse
from datetime import date

from commun import DONNEES, claude_json, ecrire_csv, explorer_site, lire_csv, nombre_mots, part_anglais

DOSSIER = DONNEES / "audits"
DOSSIER.mkdir(exist_ok=True)

SYSTEME = """Tu es un spécialiste de la francisation des entreprises au Québec.
On te donne des extraits de texte d'un site web. Repère les éléments en anglais
qu'une entreprise québécoise devrait offrir en français (contenu, boutons, menus,
conditions de vente, formulaires, descriptions de produits).
Ne donne aucun avis juridique : décris des constats, et rappelle simplement que la
Charte de la langue française exige que l'information commerciale soit disponible en français.
Ton : professionnel, factuel, bienveillant, français du Québec.
Format JSON : {"resume": "3 phrases", "constats": [{"page": url, "exemple": "texte anglais exact",
"gravite": "élevée|moyenne|faible"}] (8 maximum), "recommandations": ["..."] (4 maximum)}"""


def auditer(url: str, nom: str, max_pages: int = 15) -> str:
    pages = explorer_site(url, max_pages)
    if not pages:
        raise RuntimeError(f"Impossible de lire {url}")
    lignes = []
    for p in pages:
        p["anglais"] = part_anglais(p["segments"])
        p["mots"] = nombre_mots(p["segments"])
    extraits = "\n\n".join(
        f"PAGE {p['url']} ({p['anglais']:.0%} anglais)\n" + "\n".join(p["segments"][:60]) for p in pages
    )
    analyse = claude_json(SYSTEME, f"Entreprise : {nom}\n\n{extraits[:150_000]}")

    total_mots = sum(p["mots"] for p in pages)
    global_en = part_anglais([s for p in pages for s in p["segments"]])
    for p in sorted(pages, key=lambda p: -p["anglais"]):
        lignes.append(
            f"<tr><td>{html.escape(p['url'])}</td><td>{p['mots']}</td>"
            f"<td><div class='barre'><span style='width:{p['anglais']:.0%}'></span></div>{p['anglais']:.0%}</td></tr>"
        )
    constats = "".join(
        f"<li class='{html.escape(c.get('gravite','moyenne'))}'><b>{html.escape(c.get('gravite',''))}</b> "
        f"« {html.escape(c.get('exemple',''))} »<br><small>{html.escape(c.get('page',''))}</small></li>"
        for c in analyse.get("constats", [])
    )
    recos = "".join(f"<li>{html.escape(r)}</li>" for r in analyse.get("recommandations", []))
    return GABARIT.format(
        nom=html.escape(nom), url=html.escape(url), date=date.today().isoformat(),
        global_en=f"{global_en:.0%}", pages=len(pages), mots=total_mots,
        resume=html.escape(analyse.get("resume", "")),
        lien_rdv=html.escape(os.environ.get("LIEN_RDV", "#")), constats=constats, recos=recos, lignes="".join(lignes),
    )


GABARIT = """<!doctype html><html lang="fr-CA"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Audit de francisation, {nom}</title>
<style>
:root{{--bleu:#0b3d91;--fond:#f6f7fb;--texte:#1b1f2a;--rouge:#c62828;--orange:#ef6c00;--vert:#2e7d32}}
body{{margin:0;font:16px/1.55 system-ui,sans-serif;background:var(--fond);color:var(--texte)}}
main{{max-width:860px;margin:auto;padding:32px 16px}}
h1{{color:var(--bleu);margin-bottom:4px}} .meta{{color:#667}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:24px 0}}
.kpi{{background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 3px #0001}}
.kpi b{{display:block;font-size:28px;color:var(--bleu)}}
section{{background:#fff;border-radius:12px;padding:20px;margin:16px 0;box-shadow:0 1px 3px #0001}}
li{{margin:8px 0}} li.élevée b{{color:var(--rouge)}} li.moyenne b{{color:var(--orange)}} li.faible b{{color:var(--vert)}}
table{{width:100%;border-collapse:collapse;font-size:14px}} td{{padding:6px;border-bottom:1px solid #eee;word-break:break-all}}
.barre{{display:inline-block;width:80px;height:8px;background:#eee;border-radius:4px;margin-right:6px}}
.barre span{{display:block;height:100%;background:var(--rouge);border-radius:4px}}
.cta{{background:var(--bleu);color:#fff;text-align:center}} .cta a{{color:#fff;font-weight:700}}
small{{color:#889}}
</style></head><body><main>
<h1>Audit de francisation</h1><div class="meta">{nom} · {url} · {date}</div>
<div class="kpis"><div class="kpi"><b>{global_en}</b>du contenu analysé est en anglais</div>
<div class="kpi"><b>{pages}</b>pages analysées</div><div class="kpi"><b>{mots}</b>mots à franciser (estimation)</div></div>
<section><h2>En résumé</h2><p>{resume}</p></section>
<section><h2>Constats</h2><ul>{constats}</ul></section>
<section><h2>Recommandations</h2><ol>{recos}</ol></section>
<section><h2>Détail par page</h2><table>{lignes}</table></section>
<section class="cta"><p>Nous francisons votre site complet en 5 jours ouvrables, révision humaine incluse, prix fixe.</p>
<p><a href="{lien_rdv}">Réserver un appel de 15 minutes</a></p></section>
<p><small>Cet audit est un constat technique automatisé. Il ne constitue pas un avis juridique.
Pour vos obligations précises, consultez l'Office québécois de la langue française.</small></p>
</main></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("nom", nargs="?", default="")
    ap.add_argument("--tous", action="store_true")
    args = ap.parse_args()

    cibles = []
    prospects = lire_csv(DONNEES / "prospects.csv")
    if args.tous:
        cibles = [p for p in prospects if p.get("qualifie") == "oui" and not p.get("audit")]
    elif args.url:
        cibles = [{"site": args.url, "nom": args.nom or urllib.parse.urlparse(args.url).netloc}]
    else:
        ap.error("donne une URL ou --tous")

    for c in cibles:
        domaine = urllib.parse.urlparse(c["site"]).netloc.replace("www.", "")
        try:
            page = auditer(c["site"], c.get("nom") or domaine)
        except Exception as e:
            print(f"ÉCHEC {domaine} : {e}")
            continue
        chemin = DOSSIER / f"{domaine}.html"
        chemin.write_text(page, encoding="utf-8")
        c["audit"] = str(chemin.relative_to(DONNEES))
        print(f"Audit prêt : {chemin}")

    if args.tous:
        ecrire_csv(DONNEES / "prospects.csv", prospects)


if __name__ == "__main__":
    main()

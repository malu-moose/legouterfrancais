# Francisation Express

Service qui francise les sites web des entreprises québécoises encore en anglais.
Les agents IA trouvent les clients, préparent un audit gratuit, écrivent les courriels
et font la traduction. Toi, tu relis, tu prends les appels de 15 minutes et tu encaisses.

## Pourquoi cette idée

1. **La demande est imposée par la loi.** La Charte de la langue française, renforcée par la loi 96,
   exige que l'information commerciale (dont le site web) soit offerte en français au Québec.
   Les obligations se sont resserrées en juin 2025 (affichage, francisation dès 25 employés).
   Des milliers de PME, de franchises et d'entreprises du ROC ou des États-Unis qui vendent au Québec
   ont encore un site en anglais seulement. On ne crée pas le besoin, il existe déjà.
2. **Les agences de traduction sont lentes et chères** (souvent 0,20 $ à 0,30 $ du mot, plusieurs
   semaines). L'IA traduit en minutes ; un réviseur humain à la pige garantit la qualité.
3. **Tout se fait derrière un ordinateur.** Pas de stock, pas de local, pas de livraison physique.
4. **Le produit se vend tout seul avec une preuve.** L'audit gratuit montre au prospect, page par page,
   ce qui est en anglais sur son propre site. C'est beaucoup plus convaincant qu'un pitch.

## L'offre

| Forfait | Pour qui | Prix | Ton coût réel* |
|---|---|---|---|
| Audit | Tout prospect | Gratuit | environ 0,50 $ d'API |
| Essentiel | Site vitrine, jusqu'à 15 pages / 5 000 mots | 990 $ | environ 200 $ |
| Pro | Jusqu'à 50 pages / 15 000 mots, boutique incluse | 1 990 $ | environ 500 $ |
| Sur mesure | Au-delà, ou documents (contrats, conditions, catalogues) | sur devis | |
| Entretien | Traduction des nouveaux contenus chaque mois | 249 $/mois | environ 40 $ |

\* API Claude + réviseur à la pige (environ 0,03 $ du mot, relecture des segments signalés seulement).

**Objectif 10 000 $/mois** = 5 forfaits Pro, ou 3 Pro + 4 Essentiel, et l'entretien s'accumule
chaque mois (20 clients en entretien = 5 000 $ récurrents).

## Les agents

| Agent | Fichier | Ce qu'il fait |
|---|---|---|
| Chercheur | `agents/chercheur.py` | Construit la liste d'entreprises (import Google Maps ou recherche web) |
| Prospecteur | `agents/prospecteur.py` | Analyse les sites, mesure la part d'anglais, récupère le courriel publié, classe les prospects |
| Auditeur | `agents/auditeur.py` | Génère un rapport d'audit HTML personnalisé (l'aimant à clients) |
| Rédacteur | `agents/redacteur.py` | Écrit le courriel + 2 relances par prospect, les envoie au bon rythme |
| Traducteur | `agents/traducteur.py` | Livre la traduction complète du site, avec relecture IA et liste des doutes |
| Tableau de bord | `agents/tableau_de_bord.py` | Entonnoir, revenus du mois, écart à l'objectif |

Le site de vente est dans `site/index.html`.

Le plan de lancement jour par jour est dans `LANCEMENT.md`.

## Ta routine (environ 1 h par jour)

```bash
python agents/prospecteur.py             # matin : analyse la nouvelle liste
python agents/auditeur.py --tous         # audits des prospects qualifiés
python agents/redacteur.py rediger       # brouillons des courriels
# relire donnees/boite_envoi.csv, passer approuve à oui
python agents/redacteur.py envoyer       # envoi (40 par jour par adresse au départ)
python agents/tableau_de_bord.py
```

Quand un client paie :
```bash
python agents/traducteur.py https://client.com "Nom du client"
# envoyer donnees/livraisons/<domaine>/a_reviser.csv au réviseur, puis livrer traduction.csv
```

Tout ça peut ensuite tourner seul chaque matin via une tâche planifiée (cron), une fois que tu
fais confiance aux courriels générés (option `--auto`).

## Plan des 30 premiers jours

**Jours 1 à 3 : mise en place (environ 300 $)**
1. Enregistrer un nom d'entreprise (Registraire des entreprises du Québec, environ 40 $).
2. Acheter un domaine et **deux domaines secondaires** pour la prospection (ne jamais prospecter
   depuis le domaine principal). Google Workspace ou équivalent, 3 boîtes courriel.
3. Réchauffer les boîtes (outil de warm-up, environ 30 $/mois chacune) pendant que tu prépares le reste.
4. Compte Stripe : liens de paiement pour 990 $ et 1 990 $, abonnement 249 $.
5. Calendly gratuit pour l'appel de 15 minutes.
6. Clé API Anthropic (console.anthropic.com), budget de départ 100 $.
7. Publier `site/index.html` (Netlify ou GitHub Pages, gratuit) et les audits sous `/audits`.
8. Recruter **un réviseur** sur l'annuaire de l'OTTIAQ ou sur Upwork : test payant de 500 mots.

**Jours 3 à 7 : la liste**
Construire `donnees/entreprises.csv` avec 2 000 entreprises. Meilleures sources :
* Les chaînes et franchises canadiennes présentes au Québec avec un site anglais seulement.
* Entreprises de l'Ouest-de-l'Île, de Laval, de l'Outaouais, des Cantons-de-l'Est (marché anglophone fort).
* Boutiques Shopify canadiennes qui livrent au Québec.
* Annuaires sectoriels, Google Maps, LinkedIn Sales Navigator, Apollo.io pour les courriels.
Ne garder que les adresses professionnelles publiées (voir LCAP plus bas).

**Jours 7 à 30 : la machine tourne**
* 3 boîtes x 40 courriels/jour x 20 jours ouvrables = environ 2 400 premiers contacts.
* Taux de réponse réaliste avec audit personnalisé : 2 à 4 %, soit 50 à 90 conversations.
* Taux de conclusion réaliste : 10 à 15 %, soit 5 à 13 clients.
* Panier moyen visé : 1 500 $. **Fourchette du mois 1 : 7 500 $ à 19 000 $.**

## Ce qu'il faut savoir, honnêtement

* **Rien n'est garanti au mois 1.** Le scénario ci-dessus est réaliste mais pas acquis. Le plus
  probable : un premier mois entre 3 000 $ et 12 000 $ selon la qualité de ta liste et la vitesse
  de mise en place. Le récurrent (entretien) rend les mois suivants plus faciles.
* **Ce que tu ne peux pas déléguer :** l'appel de 15 minutes, la décision d'approuver les courriels
  au début, et la relation avec le réviseur. Compte 1 à 2 h par jour.
* **LCAP (loi canadienne anti-pourriel)** : le courriel B2B non sollicité est permis seulement si
  l'adresse est publiée publiquement par l'entreprise, sans mention de refus, et si le message
  concerne son activité. Chaque message identifie l'expéditeur, son adresse postale et offre un
  désabonnement (déjà intégré). Garde la preuve de la source de chaque adresse.
* **Pas d'avis juridique.** Le service est de la traduction. On ne promet jamais la « conformité
  légale », on ne menace pas d'amendes dans les courriels. Pour les questions précises, renvoyer à l'OQLF.
* **Qualité.** La relecture IA signale les segments douteux ; le réviseur humain les corrige.
  Ne jamais livrer sans cette étape : un seul client mécontent coûte plus cher qu'un réviseur.

## Installation

```bash
cd francisation-ia
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...            # ou : ant auth login
cp donnees/entreprises.exemple.csv donnees/entreprises.csv
```

Variables pour l'envoi : `EXPEDITEUR_NOM`, `EXPEDITEUR_ENTREPRISE`, `EXPEDITEUR_ADRESSE_POSTALE`,
`SMTP_HOTE`, `SMTP_PORT`, `SMTP_UTILISATEUR`, `SMTP_MOT_DE_PASSE`, `URL_AUDITS`, `LIEN_RDV`.

Les fichiers de `donnees/` contiennent des données de prospects : ils sont exclus de Git.

---

# Volet 2 : guides PDF et vidéos IA (marque « PME Futée »)

Chaîne de contenu qui tourne en parallèle de Francisation Express. Niche par défaut :
**l'IA pour les PME et travailleurs autonomes du Québec**. C'est le sujet le plus en vogue,
le marché francophone est bien moins saturé que l'anglais, et cette audience est
exactement celle qui achète Francisation Express. Tout se change dans `contenu/config.json`.

## L'échelle de prix

| Étape | Produit | Prix |
|---|---|---|
| Gratuit | Vidéos TikTok, Reels Instagram et Facebook | 0 $ |
| Entrée | Guide PDF | 27 $ |
| Milieu | Guide + modèles prêts à copier (prompts, gabarits, tableurs) | 97 $ |
| Haut | Francisation Express ou accompagnement IA sur mesure | 990 $ et plus |

Le PDF sert surtout à transformer un spectateur en client. Le revenu vient du haut de l'échelle.

## Les agents

| Agent | Fichier | Ce qu'il fait |
|---|---|---|
| Veille | `contenu/veille.py` | Recherche web des sujets qui montent, classés par potentiel de vente |
| Auteur | `contenu/guide.py` | Plan, chapitres, mise en page, PDF et page de vente |
| Scénariste | `contenu/videos.py` | 20 scripts de vidéos courtes par guide et calendrier de publication de 30 jours |

```bash
python contenu/veille.py                      # sujets tendance -> donnees/sujets.csv
python contenu/guide.py --meilleur            # guide du meilleur sujet -> donnees/guides/<sujet>/
python contenu/videos.py donnees/guides/<sujet> --par-jour 2
```

Un guide de 30 pages coûte environ 3 à 6 $ d'API et prend 10 à 15 minutes.

## Production des vidéos (ce qui reste manuel ou semi-automatique)

Chaque script contient la voix off, les plans visuels (prompts) et les textes à l'écran.
1. **Voix** : ElevenLabs (environ 22 $/mois) ou un avatar HeyGen (environ 29 $/mois).
2. **Images** : générateur vidéo IA à partir des prompts, ou b-roll et captures d'écran.
3. **Montage** : CapCut (sous-titres automatiques, gabarits).
4. **Publication** : importer `donnees/calendrier.csv` dans Metricool ou Buffer, qui publie seul
   sur les trois plateformes.

Compte environ 10 minutes par vidéo une fois le rythme pris, soit 3 à 5 h par semaine pour une vidéo par jour.

## Vente et livraison

Payhip ou Gumroad : livraison automatique du PDF, gestion des taxes et des remboursements.
Mettre l'URL de paiement à la place de `LIEN_PAIEMENT` dans `vente.html`.

## Ce qu'il faut savoir, honnêtement

* **Ce volet ne fera probablement pas 10 000 $ au premier mois.** Un compte neuf met en général
  2 à 6 mois à décoller. Il faut le voir comme un actif qui grandit, pendant que Francisation Express
  amène l'argent rapide.
* **Étiquette IA obligatoire.** TikTok, Instagram et Facebook demandent d'étiqueter le contenu
  réaliste généré par IA. Le calendrier le rappelle à chaque publication.
* **Constance avant tout.** 1 à 2 vidéos par jour pendant 90 jours. Après 30 jours, garder les
  formats qui marchent (vues, partages, clics en bio) et doubler dessus.
* **Les taxes.** Inscription à la TPS et à la TVQ obligatoire au-delà de 30 000 $ de ventes sur
  4 trimestres (petit fournisseur). Payhip peut percevoir les taxes à ta place.
* **Pub payante** : seulement quand une vidéo organique performe déjà. On la booste avec 10 à 20 $ par jour,
  pas avant.

## Installation supplémentaire

```bash
pip install weasyprint    # pour la conversion PDF (sinon : ouvrir guide.html et Imprimer en PDF)
```

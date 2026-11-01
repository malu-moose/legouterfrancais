# Lancement de Francisation Express : 14 jours jusqu'aux premières ventes

Le chemin critique, c'est le **réchauffement des boîtes courriel** : une adresse neuve qui envoie
40 courriels le premier jour finit en indésirables. Donc on lance le réchauffement le jour 1,
et pendant qu'il chauffe, on vend par **téléphone et LinkedIn**, qui n'ont pas besoin d'attendre.

Budget total de départ : environ 300 $.

## Jour 1 : les comptes (2 h, environ 150 $)

- [ ] Choisir le nom final et vérifier qu'il est libre (registreentreprises.quebec), puis l'enregistrer.
- [ ] Acheter le domaine principal (ex. francisationexpress.ca) et 2 domaines secondaires pour la
      prospection (ex. francisation-express.ca, getfrancisation.ca). Environ 15 $ chacun.
- [ ] Google Workspace : 2 boîtes par domaine secondaire (ex. prenom@...). Environ 8 $ par boîte par mois.
- [ ] Configurer SPF, DKIM et DMARC sur chaque domaine (Google donne les valeurs, 15 minutes).
- [ ] Lancer le réchauffement sur les 4 boîtes (Instantly, Lemwarm ou Warmup Inbox, environ 30 $/mois).
- [ ] Créer la clé API Anthropic (console.anthropic.com) et charger 50 $.

## Jour 2 : la vitrine et le paiement (2 h)

- [ ] Publier `site/index.html` sur Netlify (glisser-déposer, gratuit) et brancher le domaine principal.
- [ ] Compte Stripe : liens de paiement Essentiel 990 $, Pro 1 990 $, abonnement Entretien 249 $/mois.
- [ ] Calendly gratuit : rendez-vous de 15 minutes. Mettre le lien dans `LIEN_RDV`.
- [ ] Formulaire du site : compte Formspree gratuit, remplacer `VOTRE_ID` dans `site/index.html`.

## Jour 2 et 3 : la liste (1 h de ton temps, les agents font le reste)

- [ ] Compte apify.com (5 $ de crédit gratuit). Outil « Google Maps Scraper ».
      Lancer les recherches des segments de `donnees/cibles.csv`
      (ex. « clinique dentaire Pointe-Claire », « cabinet comptable Westmount »), 100 à 200 résultats chacune.
- [ ] `python agents/chercheur.py importer export.csv`
- [ ] En complément, ciblé : `python agents/chercheur.py chercher` (boutiques et SaaS hors Québec).
- [ ] `python agents/prospecteur.py --pages 6` : analyse les sites et récupère les courriels publiés.
      Compter environ 2 000 entreprises pour obtenir 400 à 700 prospects qualifiés.

## Jour 3 : le réviseur (1 h)

- [ ] Publier une offre sur Upwork ou contacter 5 langagiers de l'annuaire OTTIAQ :
      « Révision de traductions EN vers FR (Québec) produites par IA, sites web, environ 2 000 mots
      par mandat, délai 48 h, tarif au mot ». Test payant de 500 mots, garder le meilleur.

## Jours 3 à 7 : premières ventes par téléphone et LinkedIn

Les appels B2B ne sont pas visés par la liste nationale de numéros de télécommunication exclus,
et ils ne demandent aucun réchauffement.
- [ ] `python agents/auditeur.py --tous` : un audit par prospect qualifié, publié sous `/audits`.
- [ ] 20 appels par jour aux prospects au score le plus élevé (le numéro est dans l'export Google Maps).
      Script : « Bonjour, j'ai remarqué que votre site est presque entièrement en anglais, j'ai préparé
      un court rapport gratuit qui montre les pages concernées. Je peux vous l'envoyer par courriel ? »
      Le « oui » donne un consentement exprès pour le courriel.
- [ ] 15 messages LinkedIn par jour aux propriétaires ou responsables marketing avec le lien de leur audit.
- Objectif réaliste : 1 à 3 ventes la première semaine.

## Jours 5 à 14 : la machine à courriels monte en puissance

- [ ] `python agents/redacteur.py rediger`, relire les premiers lots, puis approuver.
- [ ] Envoi progressif par boîte : 10 par jour (jours 5 à 7), 20 (jours 8 à 10), 40 ensuite.
      Avec 4 boîtes : environ 160 premiers contacts par jour à partir du jour 11.
- [ ] Répondre à chaque réponse en moins de 2 heures, avec le lien Calendly.
- [ ] Désabonnements : ajouter l'adresse à `donnees/desabonnes.csv` le jour même.

## Chaque jour ensuite (1 à 2 h)

```bash
python agents/prospecteur.py && python agents/auditeur.py --tous
python agents/redacteur.py rediger && python agents/redacteur.py envoyer --max 160
python agents/tableau_de_bord.py
```
Appels de 15 minutes, livraisons avec `agents/traducteur.py`, envoi au réviseur, facturation.

## Indicateurs à surveiller

| Indicateur | Bon | À corriger si |
|---|---|---|
| Prospects qualifiés / sites analysés | 20 à 35 % | moins de 10 % : changer de segments |
| Taux de réponse aux courriels | 2 à 4 % | moins de 1 % : changer l'objet et l'accroche |
| Appels réservés / réponses | 30 % et plus | moins de 15 % : revoir l'audit |
| Ventes / appels | 20 à 30 % | moins de 10 % : revoir l'offre ou le prix |

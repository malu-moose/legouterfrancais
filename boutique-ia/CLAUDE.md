# Boutique IA

Plusieurs boutiques Shopify en dropshipping (fournisseur CJ Dropshipping) pilotées par des scripts Python dans `agents/`.
Une boutique = un dossier `boutiques/<nom>/` (config.json, .env Shopify, donnees/).
Toujours lancer les agents avec `python boutique.py <boutique> <agent> [options]`
(ou `tout` pour toutes les boutiques). Si le propriétaire ne précise pas la boutique, demande-lui.
Le propriétaire n'est pas développeur : réponds en français, explique simplement ce que tu fais.

## Chaîne de travail

1. `python boutique.py <b> chercheur_produits idees --nombre N` : idées de produits (recherche web)
2. `python boutique.py <b> chercheur_produits sourcer` : produits CJ, prix, marge, note -> `boutiques/<b>/donnees/candidats.csv`
3. Le propriétaire approuve dans `boutiques/<b>/donnees/candidats.csv` (colonne `statut` = `approuve`),
   ou `sourcer --auto` approuve les notes de 7 et plus.
4. `python boutique.py <b> fiches` : fiches produits
5. `python boutique.py <b> publier --essai` puis `python boutique.py <b> publier` : brouillons Shopify
6. `python boutique.py <b> publier --activer` : mise en vente
7. `python boutique.py <b> videos` : scripts vidéo et `donnees/calendrier.csv`
8. `python boutique.py <b> pub ajouter <mots du produit> <montant> [--plateforme tiktok] [--date AAAA-MM-JJ]` :
   saisie quotidienne de la dépense pub par produit (`pub liste`, `pub corriger`)
9. `python boutique.py <b> tableau_de_bord --jours 7` : résultats et décision pub par produit
   (COUPER, BAISSER, CONTINUER LE TEST, GARDER, POUSSER) selon `regles_pub` de la config.
   Quand le propriétaire donne ses dépenses en vrac (« 35 sur la lampe, 20 sur le plaid »),
   fais les saisies une par une puis lance le tableau de bord et résume les décisions.

État de chaque produit : `boutiques/<b>/donnees/produits/<id>.json`, champ `statut` :
candidat, approuve, rejete, fiche, publie (brouillon Shopify), actif (en vente).
Réglages (niche, prix, délais, langue, date limite de Noël) : `boutiques/<b>/config.json`.
Secrets : `.env` à la racine (Anthropic, CJ) et `boutiques/<b>/.env` (Shopify).

## Règles

* Ne jamais rendre des produits actifs (`--activer`, ou `statut_publication` à `ACTIVE`) sans
  l'accord explicite du propriétaire dans la conversation en cours.
* Toujours lancer `publier --essai` avant un premier envoi de lot.
* Ne jamais afficher, copier ni committer le contenu de `.env` ou des fichiers `donnees/.jeton_*`.
* Pas de faux prix barrés, de fausse rareté, de faux avis, d'allégations de santé, de produits de marque.
* Pour supprimer ou modifier des produits déjà en ligne, montrer d'abord la liste et attendre la confirmation.
* Si une API renvoie une erreur de format (champ inconnu, version), corriger le script dans
  `agents/shopify.py` ou `agents/cj.py` en vérifiant la documentation officielle, puis relancer sur 1 produit.

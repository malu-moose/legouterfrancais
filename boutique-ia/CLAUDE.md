# Boutique IA

Boutique Shopify en dropshipping (fournisseur CJ Dropshipping) pilotée par des scripts Python dans `agents/`.
Le propriétaire n'est pas développeur : réponds en français, explique simplement ce que tu fais.

## Chaîne de travail

1. `python agents/chercheur_produits.py idees --nombre N` : idées de produits (recherche web)
2. `python agents/chercheur_produits.py sourcer` : produits CJ, prix, marge, note -> `donnees/candidats.csv`
3. Le propriétaire approuve dans `donnees/candidats.csv` (colonne `statut` = `approuve`),
   ou `sourcer --auto` approuve les notes de 7 et plus.
4. `python agents/fiches.py` : fiches produits
5. `python agents/publier.py --essai` puis `python agents/publier.py` : brouillons Shopify
6. `python agents/publier.py --activer` : mise en vente
7. `python agents/videos.py` : scripts vidéo et `donnees/calendrier.csv`
8. `python agents/tableau_de_bord.py --jours 7 --pub <dépenses pub>` : résultats

État de chaque produit : `donnees/produits/<id>.json`, champ `statut` :
candidat, approuve, rejete, fiche, publie (brouillon Shopify), actif (en vente).
Réglages (niche, prix, délais, langue) : `config.json`. Secrets : `.env` (voir `.env.exemple`).

## Règles

* Ne jamais rendre des produits actifs (`--activer`, ou `statut_publication` à `ACTIVE`) sans
  l'accord explicite du propriétaire dans la conversation en cours.
* Toujours lancer `publier.py --essai` avant un premier envoi de lot.
* Ne jamais afficher, copier ni committer le contenu de `.env` ou des fichiers `donnees/.jeton_*`.
* Pas de faux prix barrés, de fausse rareté, de faux avis, d'allégations de santé, de produits de marque.
* Pour supprimer ou modifier des produits déjà en ligne, montrer d'abord la liste et attendre la confirmation.
* Si une API renvoie une erreur de format (champ inconnu, version), corriger le script dans
  `agents/shopify.py` ou `agents/cj.py` en vérifiant la documentation officielle, puis relancer sur 1 produit.

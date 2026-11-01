# Boutique IA : dropshipping Shopify piloté par agents

Les agents trouvent les produits, écrivent les fiches, les mettent en ligne sur Shopify,
écrivent les scripts vidéo et suivent les ventes. CJ Dropshipping expédie.
Toi : tu approuves les produits, tu produis les vidéos, tu gères la pub et l'argent.

## La stratégie : la masse, oui, mais au bon endroit

**2 boutiques, 50 produits chacune au lancement, puis 25 nouveaux tests par semaine et par boutique.**

| Boutique | Dossier | Niche | Rôle |
|---|---|---|---|
| Animaux | `boutiques/animaux/` | Accessoires pour chiens et chats | Boutique de fond, toute l'année |
| Cadeaux | `boutiques/cadeaux/` | Idées cadeaux et déco cosy | Coup de Noël, puis Saint-Valentin, fête des Mères, fête des Pères |

Chaque boutique a son dossier : `config.json` (niche, prix, délais), `.env` (accès Shopify) et
`donnees/` (produits, candidats, calendrier). Pour en ajouter une : copier un dossier et changer la config.
Pas plus de 2 boutiques tant qu'aucune n'a de produit gagnant.

Pourquoi pas 10 boutiques et 1 000 produits dès le départ :
* Chaque boutique coûte son abonnement Shopify, ses applications et son budget pub.
* Le budget pub dilué sur 1 000 produits ne permet de tester correctement aucun d'eux.
* Les boutiques « fourre-tout » convertissent mal et attirent les contrôles de Shopify Payments,
  Google Merchant Center et Meta (blocages de fonds, comptes suspendus).

La masse qui rapporte en dropshipping, c'est **la masse de tests** (produits, vidéos, publicités),
pas la masse de boutiques. Les agents rendent ces tests presque gratuits : 25 fiches en
30 minutes au lieu de 2 jours.

**Niche par défaut : accessoires pour chiens et chats.** Les acheteurs sont passionnés et
achètent sur un coup de coeur, les produits sont très visuels en vidéo, il y a peu de
contraintes réglementaires et les achats se répètent. Tout se change dans `config.json`.

## Les agents

| Agent | Commande | Ce qu'il fait |
|---|---|---|
| Chercheur | `chercheur_produits.py idees` | Recherche web des produits qui se vendent en ce moment |
| | `chercheur_produits.py sourcer` | Trouve chaque produit chez CJ, calcule livraison, prix et marge, élimine les mauvais, note les autres sur photos |
| Rédacteur | `fiches.py` | Fiche complète en français du Québec à partir des photos : titre, description, référencement, options traduites |
| Publication | `publier.py` | Crée les produits sur Shopify (brouillon par défaut), avec photos, variantes, prix, coût et SKU |
| Scénariste | `videos.py` | 3 scripts vidéo par produit et calendrier de publication TikTok, Instagram, Facebook |
| Tableau de bord | `tableau_de_bord.py` | Ventes, marge, profit net après pub, gagnants, produits sans vente |

Règle de prix (dans `config.json`) : (coût + livraison) x 2,5, terminé par ,99,
marge minimum de 15 $, entre 19,99 $ et 89,99 $. Aucun faux prix barré : c'est interdit
au Canada (indications trompeuses sur le prix) et ça fait suspendre les comptes publicitaires.

## La routine

Toutes les commandes passent par le lanceur : `python boutique.py <boutique> <agent> [options]`.

```bash
# Lundi (30 min par boutique) : nouveaux produits
python boutique.py cadeaux chercheur_produits idees --nombre 15
python boutique.py cadeaux chercheur_produits sourcer   # puis boutiques/cadeaux/donnees/candidats.csv : « approuve »
python boutique.py cadeaux fiches
python boutique.py cadeaux publier                      # brouillons, coup d'oeil dans l'admin Shopify
python boutique.py cadeaux publier --activer
python boutique.py cadeaux videos

# Chaque jour (10 min) : noter la pub de la veille, puis lire les décisions
python boutique.py cadeaux pub ajouter lampe lune 35 --plateforme tiktok
python boutique.py tout tableau_de_bord --jours 7
```

## Les décisions pub du tableau de bord

Chaque jour, noter la dépense de la veille par produit (montant affiché par TikTok ou Meta) :
`pub ajouter <mots du produit> <montant>`. `pub liste` montre les produits, `pub corriger`
annule la dernière saisie. Le tableau de bord croise ces dépenses avec les vraies ventes Shopify :

| Décision | Quand | Budget du lendemain |
|---|---|---|
| POUSSER | 2 ventes ou plus et au moins 2,50 $ de ventes par $ de pub sur 3 jours | +25 % |
| GARDER | Rentable, mais pas encore assez pour accélérer | identique |
| CONTINUER LE TEST | Pas assez de données | identique, jusqu'au seuil de coupe |
| BAISSER | Des ventes, mais sous le seuil de rentabilité | -30 % |
| COUPER | 40 $ dépensés sans vente, ou sous le seuil après un test suffisant | arrêter |

Le seuil de rentabilité est calculé pour chaque produit à partir de son prix et de son coût
(environ 1,7 $ de ventes par $ de pub pour un produit à 35 $ qui coûte 13 $).
Le tableau de bord suit aussi le budget de test total et alerte s'il s'épuise sans produit rentable.
Tous les seuils se règlent dans `regles_pub` de `config.json`.

## Calendrier de Noël 2026 (boutique cadeaux)

La fenêtre est courte : chaque semaine de retard coûte une part importante des ventes.

| Dates | Étape |
|---|---|
| 2 au 8 novembre | Boutique en ligne, 50 premiers produits, premières vidéos. Tests pub à petit budget |
| 9 au 22 novembre | Garder les 3 à 5 produits qui vendent, couper le reste, ajouter 25 produits par semaine |
| 23 au 30 novembre | Black Friday (27 novembre) et Cyber Monday (30 novembre) : le plus gros pic. Offres réelles seulement |
| 1er au 8 décembre | Dernière ligne droite : la date limite « livré avant Noël » pousse à l'achat |
| 8 au 15 décembre | Seuls les produits d'entrepôts US ou CA restent livrables. Ajuster `date_limite` dans la config |
| Après le 15 décembre | Cartes-cadeaux Shopify (livraison immédiate), puis préparation de la Saint-Valentin |

La config cadeaux limite la livraison à 10 jours et teste d'abord les entrepôts US et CA de CJ.
Chaque fiche et chaque vidéo mentionnent la date limite de commande (`date_limite` dans la config,
au 8 décembre par défaut). Vérifie les délais réels des premières commandes et ajuste.

## Mise en place (une demi-journée par boutique)

1. **Shopify** : créer la boutique (plan Basic), thème gratuit Dawn, pages obligatoires
   (livraison, retours, conditions, confidentialité, contact). Le délai de livraison réel doit
   être écrit clairement.
2. **Clé Shopify** : sur dev.shopify.com, créer une app, permissions `write_products`,
   `read_products`, `read_orders`, `read_publications`, `write_publications`, l'installer
   sur la boutique, copier Client ID et Client secret dans `boutiques/<boutique>/.env`
   (modèle : `.env.exemple` du même dossier). Une app par boutique.
3. **CJ Dropshipping** : compte gratuit, Mon CJ > Autorisation > API, copier la clé dans le `.env`
   à la racine de `boutique-ia` (un seul compte CJ pour les deux boutiques).
4. **Expédition automatique** : installer l'app CJ Dropshipping sur Shopify et connecter la boutique.
   Nos produits portent le SKU des variantes CJ, ce qui permet de les associer aux produits CJ
   dans le tableau de bord CJ ; activer le paiement automatique des commandes. CJ expédie et
   renvoie le numéro de suivi à Shopify. Vérifier cette association sur les premiers produits.
5. **Clé Anthropic** dans le `.env` à la racine (console.anthropic.com).
6. `pip install -r requirements.txt`, puis tester : `python boutique.py cadeaux shopify` et
   `python boutique.py cadeaux cj gift`.

## Budget et chiffres, honnêtement

| Poste | Coût mensuel |
|---|---|
| Shopify Basic | environ 40 à 55 $ |
| API Claude | 20 à 60 $ selon le volume |
| Outils vidéo (CapCut, voix IA) et planification (Metricool) | 0 à 60 $ |
| **Publicité de test** (TikTok ou Meta) | **600 à 1 500 $ par boutique** : c'est le vrai coût |

Avec 2 boutiques, tous les coûts doublent. En novembre et décembre, la publicité coûte nettement plus
cher qu'en temps normal (tout le monde annonce), mais les gens achètent aussi beaucoup plus.
Si le budget est serré, mieux vaut mettre l'argent pub sur la boutique cadeaux jusqu'à Noël
et faire tourner la boutique animaux en vidéos gratuites.

* 10 000 $ de **ventes** ne sont pas 10 000 $ de **profit**. Avec 60 % de marge brute et
  25 à 35 % des ventes dépensés en pub, il reste en général 15 à 25 % de profit net.
  Pour 10 000 $ de profit, il faut viser 40 000 à 60 000 $ de ventes par mois.
* Le premier mois sert surtout à trouver 1 ou 2 produits gagnants. Un premier mois typique :
  quelques centaines à quelques milliers de dollars de ventes, souvent à perte à cause des tests.
  Rien n'est garanti.
* Sans publicité, compter sur les vidéos organiques : gratuit, mais plus lent et irrégulier.

## Règles à respecter

* Délais de livraison honnêtes sur chaque fiche et dans la politique de livraison.
* Québec : site en français (la boutique l'est par défaut), Loi sur la protection du consommateur
  (informations obligatoires pour la vente à distance, remboursement si la livraison dépasse 30 jours).
* Inscription TPS et TVQ obligatoire au-delà de 30 000 $ de ventes sur 4 trimestres.
* Étiquette « contenu IA » sur les vidéos générées par IA.
* Jamais de produits de marque, contrefaits, ou avec allégations de santé.

## Utiliser avec Claude Code dans VS Code

Ouvrir le dossier `boutique-ia` dans VS Code avec l'extension Claude Code, puis demander par exemple :
« trouve 15 nouveaux produits pour la boutique cadeaux et prépare les fiches », « mets en ligne les produits approuvés »,
« quels produits dois-je retirer ? ». Le fichier `CLAUDE.md` lui explique le projet et ses règles.

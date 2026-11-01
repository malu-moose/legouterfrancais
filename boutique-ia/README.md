# Boutique IA : dropshipping Shopify piloté par agents

Les agents trouvent les produits, écrivent les fiches, les mettent en ligne sur Shopify,
écrivent les scripts vidéo et suivent les ventes. CJ Dropshipping expédie.
Toi : tu approuves les produits, tu produis les vidéos, tu gères la pub et l'argent.

## La stratégie : la masse, oui, mais au bon endroit

**1 boutique, 50 produits au lancement, 25 nouveaux tests par semaine.**
Une 2e boutique (autre niche) seulement quand la 1re a un produit gagnant (en général mois 2 ou 3).

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

```bash
# Lundi (30 min) : nouveaux produits
python agents/chercheur_produits.py idees --nombre 15
python agents/chercheur_produits.py sourcer          # puis ouvrir donnees/candidats.csv, mettre « approuve »
python agents/fiches.py
python agents/publier.py                             # brouillons, coup d'oeil dans l'admin Shopify
python agents/publier.py --activer
python agents/videos.py

# Chaque jour (10 min)
python agents/tableau_de_bord.py --jours 7 --pub 140
```

## Mise en place (une demi-journée)

1. **Shopify** : créer la boutique (plan Basic), thème gratuit Dawn, pages obligatoires
   (livraison, retours, conditions, confidentialité, contact). Le délai de livraison réel doit
   être écrit clairement.
2. **Clé Shopify** : sur dev.shopify.com, créer une app, permissions `write_products`,
   `read_products`, `read_orders`, `read_publications`, `write_publications`, l'installer
   sur la boutique, copier Client ID et Client secret dans `.env`.
3. **CJ Dropshipping** : compte gratuit, Mon CJ > Autorisation > API, copier la clé dans `.env`.
4. **Expédition automatique** : installer l'app CJ Dropshipping sur Shopify et connecter la boutique.
   Nos produits portent le SKU des variantes CJ, ce qui permet de les associer aux produits CJ
   dans le tableau de bord CJ ; activer le paiement automatique des commandes. CJ expédie et
   renvoie le numéro de suivi à Shopify. Vérifier cette association sur les premiers produits.
5. **Clé Anthropic** dans `.env` (console.anthropic.com).
6. `pip install -r requirements.txt`, puis tester : `python agents/shopify.py` et `python agents/cj.py dog`.

## Budget et chiffres, honnêtement

| Poste | Coût mensuel |
|---|---|
| Shopify Basic | environ 40 à 55 $ |
| API Claude | 20 à 60 $ selon le volume |
| Outils vidéo (CapCut, voix IA) et planification (Metricool) | 0 à 60 $ |
| **Publicité de test** (TikTok ou Meta) | **600 à 1 500 $** : c'est le vrai coût |

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
« trouve 15 nouveaux produits et prépare les fiches », « mets en ligne les produits approuvés »,
« quels produits dois-je retirer ? ». Le fichier `CLAUDE.md` lui explique le projet et ses règles.

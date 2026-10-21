# Mettre le site en ligne sur l'hébergement WHC

Le site statique (`index.html` + `images/`) va sur ton hébergement WHC
existant (Hébergement Web Pro, déjà rattaché à `legouterfrancais.com`), pas
sur le VPS. Je n'ai pas d'accès à ton compte WHC depuis cette session —
voici les étapes à faire toi-même, ça prend 5 minutes.

## 1. Accéder au cPanel

Depuis le manager WHC, sur la ligne `legouterfrancais.com` dans
"Hébergement et sites web", clique **Gérer** puis trouve le lien vers le
cPanel (souvent un bouton "cPanel" ou une icône dédiée).

## 2. Ouvrir le Gestionnaire de fichiers (File Manager)

Dans cPanel, ouvre **Gestionnaire de fichiers**, puis navigue jusqu'au
dossier racine du site — généralement `public_html` (parfois
`public_html/legouterfrancais.com` si plusieurs domaines sont gérés sur le
même compte).

## 3. Uploader les fichiers

- Supprime ou renomme le fichier `index.html` par défaut s'il y en a un
  (souvent une page "Bienvenue" du fournisseur).
- Upload (bouton **Upload** en haut) :
  - `index.html` (à la racine de `public_html`)
  - le dossier `images/` en entier (tu peux zipper `images/` en local,
    l'uploader, puis clic droit → **Extract** dans le File Manager — plus
    rapide qu'un upload fichier par fichier)

Variante avec un client FTP (FileZilla) si tu préfères : récupère les
identifiants FTP dans cPanel → **Comptes FTP**, connecte-toi, et glisse
`index.html` + `images/` dans `public_html`.

## 4. Vérifier le HTTPS

WHC active généralement un certificat SSL gratuit automatiquement
(AutoSSL). Dans cPanel, section **SSL/TLS Status**, vérifie que
`legouterfrancais.com` et `www.legouterfrancais.com` ont un certificat
valide. Si ce n'est pas encore le cas, lance l'exécution AutoSSL depuis
cette page (ou attends — c'est généralement automatique sous 24h).

## 5. Vérifier que le DNS pointe bien vers WHC

Puisque le domaine est déjà rattaché à cet hébergement dans l'interface, le
DNS pointe normalement déjà au bon endroit. Vérifie quand même :

```bash
dig +short legouterfrancais.com
```

Ça doit renvoyer l'IP de l'hébergement WHC (pas celle du VPS
`54.39.20.153`).

## 6. Mises à jour futures du site

Pour mettre à jour le contenu (`index.html`, images), répète l'étape 3 à
chaque changement — pas d'automatisation prévue pour l'instant vu la
simplicité du site. On pourra scripter ça via FTP plus tard si utile.

## 7. Structure "coming soon" + aperçu privé protégé

Le dépôt a maintenant deux pages :
- `index.html` (racine) : la page publique "bientôt disponible"
- `apercu/index.html` : le site complet, protégé par mot de passe, pour vos
  tests internes avant le lancement officiel

### Déployer cette structure (depuis le SSH du serveur WHC)

```bash
cd ~/legouterfrancais
git pull

# page publique
cp index.html ~/public_html/
cp robots.txt ~/public_html/

# aperçu privé
mkdir -p ~/public_html/apercu
cp -r apercu/* ~/public_html/apercu/
```

### Activer le mot de passe sur /apercu/

Le fichier `.htaccess` dans `apercu/` référence
`/home/legou878/.htpasswds/apercu/passwd` — ce fichier de mots de passe doit
être créé séparément (jamais commité dans git). Deux façons de faire :

**Via cPanel (le plus simple) :**
1. cPanel → **Confidentialité des répertoires** (Directory Privacy)
2. Navigue jusqu'à `public_html/apercu`
3. Coche "Protéger ce répertoire", choisis un nom, clique Enregistrer
4. Crée un utilisateur + mot de passe pour y accéder
5. ⚠️ Ça va générer son propre `.htaccess` dans `apercu/` — vérifie qu'il
   garde bien la ligne `Header set X-Robots-Tag "noindex, nofollow"`, sinon
   rajoute-la à la main après

**Via SSH :**
```bash
mkdir -p ~/.htpasswds/apercu
htpasswd -c ~/.htpasswds/apercu/passwd ton_identifiant
# (demande de définir un mot de passe)
```

### Accès à l'aperçu

`https://legouterfrancais.com/apercu/` — demandera le login/mot de passe
défini ci-dessus. Le site n'est pas indexé par les moteurs de recherche
(`robots.txt` + meta noindex + header noindex).

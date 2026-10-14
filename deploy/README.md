# Infrastructure Le Goûter Français

Deux hébergements séparés, pour deux usages différents :

| Composant | Où | Pourquoi |
|---|---|---|
| Site vitrine public (`legouterfrancais.com`) | **WHC** (hébergement mutualisé existant) | Statique, zéro maintenance, HTTPS automatique — voir `whc-deploy.md` |
| Application de production / intranet (à venir, derrière login) | **VPS OVH** (`54.39.20.153`) | Nécessite un serveur dédié, une authentification, et tourne aux côtés d'OpenClaw |

## 0. Avant tout : régénère ta clé SSH du VPS

Tu as partagé ta clé privée en clair dans le chat — elle est donc compromise.
Sur ta machine :

```bash
ssh-keygen -t ed25519 -C "vps-legouterfrancais"
ssh-copy-id -i ~/.ssh/<nouvelle_cle>.pub ubuntu@54.39.20.153
```

Puis connecte-toi avec la nouvelle clé et retire l'ancienne clé publique
correspondante de `~/.ssh/authorized_keys` sur le VPS (`nano ~/.ssh/authorized_keys`).

## 1. Site public → WHC

Suis `deploy/whc-deploy.md` : upload de `index.html` et `images/` via le
Gestionnaire de fichiers cPanel ou FTP. Ne touche pas au VPS pour ça.

## 2. VPS → sécurisation de base (dès maintenant)

Le VPS ne sert rien publiquement pour l'instant (l'app n'existe pas encore),
donc on se contente de le durcir :

```bash
git clone https://github.com/malu-moose/legouterfrancais.git ~/legouterfrancais
cd ~/legouterfrancais
sudo bash deploy/harden-vps.sh
```

Ce script :
- met à jour le système et active les mises à jour de sécurité automatiques
- configure le pare-feu (UFW) : **seul SSH est ouvert** (pas de 80/443 tant
  qu'il n'y a rien à servir publiquement)
- installe fail2ban (bannit les IP qui tentent de forcer le SSH)
- durcit SSH (désactive la connexion par mot de passe et le login root)

## 3. Déploiement futur : app.legouterfrancais.com (quand l'app existe)

À faire le moment venu, pas maintenant :

1. Chez OVH, ajoute un enregistrement DNS :
   `A  app  54.39.20.153`
2. Installe nginx + Certbot sur le VPS, avec un reverse proxy vers l'app et
   un certificat HTTPS pour `app.legouterfrancais.com` uniquement (jamais
   l'apex `legouterfrancais.com`, qui reste sur WHC).
3. Ouvre 80/443 dans UFW : `sudo ufw allow 80/tcp && sudo ufw allow 443/tcp`
4. Mets l'authentification en place **avant** d'ouvrir le port 443 au public
   — soit dans l'app elle-même (login), soit en amont avec une
   authentification basique nginx ou un accès restreint par IP/VPN le temps
   que l'app ait son propre système de login. Pas d'app accessible sans
   authentification, même temporairement.
5. On écrira la config nginx dédiée à ce moment-là (dépend de la techno de
   l'app : reverse proxy vers quel port, etc.)

## Sécurité : ce qui est couvert, ce qui ne l'est pas

Couvert par `harden-vps.sh` :
- Pare-feu minimal (SSH uniquement pour l'instant)
- Anti brute-force SSH (fail2ban)
- SSH par clé uniquement, pas de login root
- Mises à jour de sécurité automatiques

Pas encore couvert (normal, à faire au moment du déploiement de l'app) :
- HTTPS / nginx / reverse proxy pour `app.legouterfrancais.com`
- Authentification de l'application elle-même

À faire toi-même, régulièrement :
- Garder une sauvegarde de ta clé SSH privée en lieu sûr (gestionnaire de mots
  de passe), ne jamais la recoller dans un chat ou un ticket
- Vérifier de temps en temps `sudo fail2ban-client status sshd` et
  `sudo ufw status`

## Cohabitation avec OpenClaw sur le même VPS

Ce VPS héberge aussi OpenClaw (agent IA, contrôlé via Telegram). Points à
retenir :
- OpenClaw ne communique qu'en sortant (polling de l'API Telegram) : aucun
  port entrant à ouvrir pour lui, il n'entre pas en conflit avec le pare-feu.
- Il tourne sous un utilisateur Linux dédié, séparé de celui de l'app et sans
  droits sudo — bonne pratique déjà en place, à conserver. Quand l'app
  existera, vérifie qu'OpenClaw n'a pas accès en écriture à son dossier.
- Un agent IA autonome sur une machine qui sert aussi une app de production
  est un risque à garder en tête : s'il est compromis, un attaquant qui
  obtiendrait l'accès à son compte isolé ne devrait trouver ni droits root,
  ni accès aux fichiers de l'app — c'est exactement ce que l'isolation par
  utilisateur empêche. Garde ses identifiants Telegram/API hors de tout
  dépôt git et surveille ses logs.

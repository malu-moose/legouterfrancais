# Mise en ligne de legouterfrancais.com sur le VPS OVH

Ces fichiers sont faits pour être exécutés **depuis ton propre ordinateur**
(là où ta connexion SSH vers le VPS fonctionne), pas depuis cette session cloud
qui n'a pas d'accès SSH sortant.

## 0. Avant tout : régénère ta clé SSH

Tu as partagé ta clé privée en clair dans le chat — elle est donc compromise.
Sur ta machine :

```bash
ssh-keygen -t ed25519 -C "vps-legouterfrancais"
ssh-copy-id -i ~/.ssh/<nouvelle_cle>.pub ubuntu@54.39.20.153
```

Puis connecte-toi avec la nouvelle clé et retire l'ancienne clé publique
correspondante de `~/.ssh/authorized_keys` sur le VPS (`nano ~/.ssh/authorized_keys`).

## 1. DNS chez OVH

Dans le manager OVH, zone DNS de `legouterfrancais.com` :

| Type | Nom | Cible          |
|------|-----|----------------|
| A    | @   | 54.39.20.153   |
| A    | www | 54.39.20.153   |

Attends la propagation (quelques minutes à quelques heures). Vérifie avec :

```bash
dig +short legouterfrancais.com
```

## 2. Copier ces fichiers de déploiement sur le VPS

```bash
scp -r deploy ubuntu@54.39.20.153:~/
```

## 3. Lancer la configuration du serveur (une seule fois)

```bash
ssh ubuntu@54.39.20.153
cd deploy
sudo bash setup-vps.sh
```

Ce script :
- met à jour le système et active les mises à jour de sécurité automatiques
- installe nginx + Certbot (HTTPS gratuit, renouvellement automatique)
- configure le pare-feu (UFW) : seuls SSH, HTTP et HTTPS sont ouverts
- installe fail2ban (bannit les IP qui tentent de forcer le SSH)
- durcit SSH (désactive la connexion par mot de passe et le login root)
- demande le certificat HTTPS pour legouterfrancais.com (nécessite que le DNS
  pointe déjà vers le VPS, voir étape 1)
- installe la config nginx durcie (en-têtes de sécurité, blocage des fichiers
  cachés, mise en cache des images)

## 4. Déployer le site

Depuis la racine du dépôt, sur ta machine :

```bash
bash deploy/deploy-site.sh
```

Relance cette commande chaque fois que tu modifies `index.html` ou les images.

## 5. Vérifier

```bash
curl -I https://legouterfrancais.com
```

Tu dois voir `HTTP/2 200` et les en-têtes de sécurité (`strict-transport-security`, etc.).

## Sécurité : ce qui est couvert, ce qui ne l'est pas

Couvert par `setup-vps.sh` :
- HTTPS forcé + renouvellement auto du certificat
- Pare-feu minimal (22/80/443 uniquement)
- Anti brute-force SSH (fail2ban)
- SSH par clé uniquement, pas de login root
- Mises à jour de sécurité automatiques
- En-têtes HTTP de sécurité (HSTS, CSP, X-Frame-Options, etc.)

À faire toi-même, régulièrement :
- Garder une sauvegarde de ta clé SSH privée en lieu sûr (gestionnaire de mots
  de passe), ne jamais la recoller dans un chat ou un ticket
- Vérifier de temps en temps `sudo fail2ban-client status sshd` et
  `sudo ufw status`
- Si tu ajoutes un jour un backend (ex. formulaire newsletter avec stockage
  des emails), il faudra une configuration additionnelle (reverse proxy vers
  l'appli, validation des entrées, etc.) — à faire au moment venu

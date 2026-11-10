# Strasbourg Piscines

Intégration Home Assistant qui suit l'ouverture, l'affluence et les horaires
du jour des piscines publiques de l'Eurométropole de Strasbourg.

> Projet communautaire, non affilié à l'Eurométropole de Strasbourg. Les
> données utilisées sont publiées par son portail Open Data officiel.

## Fonctionnalités

- Sélection des piscines pendant la configuration ; aucun compte ni clé API.
- Capteur **Affluence** : le code temps réel exactement publié par la source
  (`GREEN`, `ORANGE`, `RED`, `BLACK` ou `CLOSED`).
- Capteur binaire **Ouverte** utilisable dans les automatisations.
- Capteur **Horaires du jour**, y compris les créneaux séparés de la journée.
- Une requête commune pour toutes les piscines choisies.
- Actualisation configurable de 3 à 15 minutes ; jamais plus fréquente que le
  plancher de trois minutes fixé par l'intégration.

## Entités créées

Chaque piscine choisie devient un appareil Home Assistant contenant :

- `Affluence` : code couleur public en temps réel ;
- `Ouverte` : état d'ouverture explicitement publié ;
- `Horaires du jour` : plages d'ouverture du jour, lorsqu'elles sont fournies.

Les entités exposent également les attributs `occupation` (valeur brute de la
source), `today_schedule`, `source_updated_at` (horodatage fourni par
l'Eurométropole) et `data_fetched_at` (réception de la réponse par Home
Assistant). Ces deux horodatages restent volontairement distincts.

## Installation avec HACS

Tant que le dépôt n'est pas dans le catalogue HACS par défaut :

1. Dans **HACS → Intégrations**, ouvrez le menu ⋮ puis **Dépôts personnalisés**.
2. Ajoutez `https://github.com/hehrstein/strasbourg-piscines`, catégorie
   **Integration**.
3. Installez **Strasbourg Piscines**, puis redémarrez Home Assistant.
4. Dans **Paramètres → Appareils et services**, ajoutez l'intégration et
   sélectionnez les piscines à suivre.

## Source et fraîcheur

Les états temps réel viennent du jeu de données officiel
[Fréquentation en temps réel des piscines](https://data.strasbourg.eu/explore/dataset/frequentation-en-temps-reel-des-piscines/)
de l'Eurométropole. Les informations de lieu et d'horaires sont publiées dans
le jeu connexe [Lieux - Piscines](https://data.strasbourg.eu/explore/dataset/lieux_piscines/).

L'intégration ne transforme pas le code d'affluence en pourcentage ni en
nombre de baigneurs : la source ne documente pas ces deux interprétations.

## Développement

```bash
python -m pip install -r requirements_test.txt
pytest
```

La suite couvre le parsing de la source, la sélection, l'indisponibilité du
flux d'options, le plancher d'actualisation et les traductions anglaises de
secours.

## Licence

Le code est distribué sous [licence MIT](LICENSE). La réutilisation des données
reste soumise aux conditions publiées par l'Eurométropole de Strasbourg.

# TikTok Video Generator

Chaîne de production automatisée pour des **séries TikTok interactives** (format vertical 1080×1920, ~1:20, choix A/B en fin d'épisode), pensée pour tourner sur un Mac sans le saturer.

À partir d'un simple texte de narration, l'outil génère :
- une **voix off française** neuronale avec horodatage mot par mot ;
- des **sous-titres synchronisés** (1 à 2 mots, mots-clés en couleur) ;
- l'habillage : **titre de la série, numéro d'épisode, HUD horloge/lieu, étiquettes** ;
- les **effets horreur** : brouillard, grain, vignettage, étalonnage froid, glitchs, néons qui grésillent, caméra à l'épaule ;
- une **bande-son** synthétisée (drone, bruitages) mixée avec ducking et normalisée à −14 LUFS ;
- la **carte interactive A/B** finale.

Les décors sont dessinés par le code (maquette animée). Chaque plan peut être remplacé par une **image ou un clip réaliste généré par IA** : il suffit de le déposer dans `epNN/scenes/`.

## Première série : [6H17](6h17/README.md)

> *À 6 h 17 du matin, Emma a vu son mari mort frapper à la vitre d'une supérette…*

- Bible de production (personnages, décors, charte, prompts IA plan par plan) : [6h17/bible/BIBLE.md](6h17/bible/BIBLE.md)

## Installation (macOS)

```bash
brew install ffmpeg python@3.13
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd 6h17
./tools/make_episode.sh ep01        # → ep01/build/6h17_ep01_tiktok.mp4
```

Prérequis : macOS (polices système, encodeur VideoToolbox), ffmpeg et une connexion internet pour la voix (service Microsoft Edge TTS).

## Publication TikTok

Activez l'étiquette « Contenu généré par IA » (voix de synthèse, images IA). Les vidéos de plus d'une minute sont éligibles au Creator Rewards Program.

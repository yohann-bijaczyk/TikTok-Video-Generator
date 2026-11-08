# 6H17 — chaîne de production TikTok

```
6h17/
├─ bible/BIBLE.md        personnages, décors, charte, prompts IA plan par plan
├─ tools/
│  ├─ make_episode.sh    tout-en-un : voix → bande-son → image → mixage
│  ├─ tts.py             voix française neuronale + horodatage mot par mot
│  ├─ render.py          moteur image (caméra, brouillard, grain, HUD, sous-titres)
│  ├─ gfx.py / timeline.py
└─ ep01/
   ├─ narration.txt      texte lu par la voix
   ├─ episode.py         découpage des plans + décors + carte A/B
   ├─ sound.py           musique et bruitages synthétisés
   ├─ scenes/            ← déposez ici vos images/clips réalistes (S09_vitre_thomas.jpg…)
   └─ build/6h17_ep01_tiktok.mp4   ← fichier à publier
```

## Commandes

```bash
./tools/make_episode.sh ep01             # tout refaire
./tools/make_episode.sh ep01 --no-tts    # après avoir ajouté des images dans ep01/scenes/
./tools/make_episode.sh ep01 --mix-only  # retoucher seulement le son
../.venv/bin/python tools/render.py ep01 --stills 5,30,60   # images de contrôle
VOICE=fr-FR-RemyMultilingualNeural ./tools/make_episode.sh ep01   # autre voix
```

## Ménager le Mac

Tout tourne en `nice -n 10` avec 2 threads au maximum. Une seule image est en mémoire à la fois et l'encodage passe par la puce vidéo (VideoToolbox). Le pic de RAM mesuré est d'environ 1 Go (pendant le calcul du gros plan sur l'œil).

## Nouvel épisode

Copiez `ep01/` vers `ep02/`, réécrivez `narration.txt`, adaptez les repères (`T("mot", n°)`) dans `episode.py` et `sound.py`, puis changez `EPISODE = 2` et `EP_TITLE`.

# 6H17 — Bible de production

Série TikTok d'horreur interactive. Format vertical 1080×1920, 30 i/s, environ 1:20 par épisode (plus d'une minute, donc éligible au programme de rémunération TikTok). Chaque épisode se termine sur un choix A/B voté en commentaire.

---

## 1. Charte graphique (identique dans tous les épisodes)

| Élément | Règle |
|---|---|
| **Titre** | « 6H17 » en Impact, rouge `#E61E1E`, ouverture de 0 à 2,9 s avec glitch, puis badge rouge « 6H17 \| ÉPISODE N » en haut |
| **HUD** | Horloge du récit (`06:17:04`) + lieu, en monospace, point rouge clignotant, en haut à environ 200 px |
| **Sous-titres** | 1 à 2 mots à la fois, Impact 138 px, blanc avec contour noir, mots-clés en rouge, petit effet « pop » ; centrés à y ≈ 1250 |
| **Étiquettes** | Pastilles ambre `#FFB020` en monospace (« ADAM · 6 ANS », « +30 SECONDES »…) |
| **Étalonnage** | Bleu froid, noirs écrasés, grain, vignettage, brouillard qui dérive ; flash-backs désaturés et sépia |
| **Fin** | Carte « ET VOUS, QUE FERIEZ-VOUS ? » avec les options A (rouge) et B (bleu), suivie de « Écrivez A ou B en commentaire » et « La suite dans l'épisode N+1 » |
| **Zones sûres TikTok** | Rien d'important à droite de x = 950 (boutons) ni sous y = 1520 (description) |
| **Son** | Voix fr-FR-HenriNeural, drone grave, tic-tac sous la question finale, normalisation à −14 LUFS |

## 2. Personnages : fiches de référence (à réutiliser mot pour mot dans les prompts)

**EMMA MOREAU** — 34 ans, mère d'Adam, veuve de Thomas depuis 3 jours.
> French woman, 34, shoulder-length dark brown hair tied in a loose low bun, pale tired face, light freckles, red-rimmed green eyes, wearing a beige trench coat over a black turtleneck, **deep red wool scarf**, small silver wedding ring.

**ADAM MOREAU** — 6 ans.
> French boy, 6, messy light-brown hair, big dark eyes, **navy blue hoodie**, grey backpack with a small reflective strip, red sneakers, holding his mother's hand.

**THOMAS MOREAU** — 37 ans, mari d'Emma, enterré il y a 3 jours.
> French man, 37, short dark-brown hair, three-day stubble, grey-green eyes, **dark navy wool coat over a grey crew-neck sweater**, wedding ring, pale skin, calm expression.

**LES IMMOBILES** — les habitants figés.
> Ordinary Parisians in winter coats frozen mid-step, then turning their heads in unison; **eyes entirely black, glossy, no iris, no white**.

> **Astuce continuité :** générez d'abord une planche de personnage (face, profil, dos) pour chaque rôle, puis utilisez-la comme référence (`--cref` sur Midjourney, « character reference » sur Kling/Runway, ou un LoRA Flux) pour tous les plans.

## 3. Lieux

- **Rue Oberkampf, Paris 11e, 6h16-6h17, novembre** : façades haussmanniennes, chaussée mouillée, lampadaires au sodium orangés, brouillard bas, ciel bleu nuit qui commence à pâlir.
- **La supérette « SUPÉRETTE · OUVERT 24/24 »** : enseigne vert pâle, néons froids, rayonnages serrés, comptoir avec TPE, vitrine embuée avec l'autocollant « OUVERT 24H/24 », porte métallique grise « RÉSERVE — PRIVÉ » au fond, poignée à levier en inox.
- **Cimetière (flash-back)** : stèle de granit gris « THOMAS — 1989-2026 — Mari et papa adoré », terre fraîche, couronne rouge et blanche, pluie fine, arbres nus.

Suffixe de style commun à ajouter à chaque prompt :
> *cinematic horror still, vertical 9:16, shot on ARRI Alexa, 35mm anamorphic, cold teal and sodium-orange lighting, thick low fog, wet reflective pavement, film grain, high contrast, deep shadows, photorealistic, no text*

## 4. Épisode 1 « Les Immobiles » : plans à remplacer par des images ou clips réalistes

Le rendu actuel utilise des décors procéduraux (dessinés par le code) comme **maquette animée**. Pour chaque plan, déposez une image (`.jpg`/`.png`) ou un clip (`.mp4`, 5 s ou plus, 9:16) portant **exactement** le nom ci-dessous dans `ep01/scenes/`, puis relancez `./tools/make_episode.sh ep01 --no-tts`. Le moteur applique automatiquement le recadrage, les mouvements de caméra, le brouillard, le grain, l'étalonnage, les sous-titres et le HUD.

| Fichier | Durée | Prompt image | Mouvement (image → vidéo) |
|---|---|---|---|
| `S01_vitre_hook` | 0-5,5 s | View from inside a Paris convenience store at dawn: Thomas (fiche) standing outside, one palm pressed flat on the fogged glass, other fist knocking, face half in shadow, mirrored red sticker "OUVERT 24H/24" | Fist knocks 3 times, glass vibrates, slow push-in |
| `S02_rembobinage` | 5,5-10,7 s | Wide street-level shot of rue Oberkampf at 6am, traffic and pedestrians moving, tail lights, fog | Fast reverse motion (rewind), then normal speed |
| `S03_rue_figee` | 10,7-14,4 s | Same street, every pedestrian and car frozen mid-motion, eerie stillness, fog | Very slow dolly forward, nothing moves |
| `S04_conducteurs` | 14,4-16,6 s | Close shot through a car windshield: driver frozen, hands on wheel, staring blankly, dashboard glow | Static, a slight handheld shake |
| `S05_passants` | 16,6-19,8 s | Pedestrians frozen on a crosswalk, one foot lifted mid-step, coats in the wind but bodies still | Slow lateral tracking |
| `S06_emma_adam` | 19,8-24,1 s | From behind: Emma and Adam (fiches) walking hand in hand between frozen people and stopped cars | Slow follow shot from behind |
| `S07_reprise` | 24,1-28,3 s | The frozen crowd begins to turn their heads toward camera, Emma pulling Adam close | Heads turn in unison, jerky motion |
| `S08_yeux_noirs` | 28,3-31,2 s | Extreme close-up of a human eye, iris turning completely black as ink spreads over the white | Ink spreads over 1.5 s |
| `S09_foule` | 31,2-33,8 s | Dozens of Parisians in fog all staring directly at camera, eyes entirely black | Slow push-in, a few heads tilt |
| `S10_superette` | 33,8-38,0 s | Emma dragging Adam running toward a glowing 24/7 convenience store, black-eyed silhouettes in fog behind | Running, camera shake |
| `S11_vitre_thomas` | 38,0-43,1 s | As S01, now face revealed by flickering neon: it is clearly Thomas, pale, calm | Neon flicker reveals the face |
| `S12_enterrement` | 43,1-46,4 s | Fresh grave in the rain, granite headstone "THOMAS 1989-2026 Mari et papa adoré", red-white wreath | Rain, slow push-in |
| `S13_vitre_ouvre` | 46,4-48,6 s | Close-up of Thomas's face against the glass, mouthing "ouvre" | Lips move, knocks |
| `S14_telephone` | 48,6-57,7 s | Emma's trembling hand holding a phone in a dark store, lock screen 6:17, notification from "Thomas" | Phone vibrates, notification slides in |
| `S15_reserve` | 57,7-61,1 s | Long store aisle toward a grey metal door "RÉSERVE — PRIVÉ", flickering fluorescent tube, light under the door with two feet shadows | Slow push-in toward the door |
| `S16_poignee` | 61,1-64,3 s | Macro of a stainless lever door handle on a grey metal door | Handle turns slowly downward |
| `S17_deux_thomas` | 64,3-67,8 s | *(composé automatiquement : haut = S11, bas = S15)* | — |
| `S18_question` | 67,8 s-fin | *(carte de choix générée par le code ; ne pas remplacer)* | — |

> ⚠️ **Le texte à l'écran (téléphone, stèle) est mieux rendu par le code** : pour S12 et S14, générez des images **sans texte**, ou gardez les versions procédurales.

## 5. Règles TikTok à respecter

- Activez l'étiquette **« Contenu généré par IA »** à la publication dès que des images ou clips IA réalistes sont utilisés, ainsi que pour la voix de synthèse. TikTok l'exige pour les contenus réalistes.
- Durée supérieure à 1 minute et contenu original : condition de base du Creator Rewards Program.
- Titre de post suggéré : *« 6H17 — Épisode 1 : à 6h17, tout Paris s'est figé… sauf eux. A ou B ? 👇 #6h17 #horreur #histoire #seriestiktok #paris »*
- Épinglez un commentaire « A = ouvrir à Thomas dehors / B = aller voir la réserve » pour lancer le vote.

## 6. Continuité pour la suite

- Horloge du récit : gel à 06:16:20, reprise 30 s plus tard, coups sur la vitre à 06:17:04. L'épisode 2 reprend à 06:17:35.
- Emma porte **toujours** l'écharpe rouge et Adam le sweat bleu marine, pour qu'on les repère dans la foule.
- Le Thomas de dehors a des yeux **normaux** (ambiguïté volontaire). Le Thomas de la réserve n'a pas encore été vu.

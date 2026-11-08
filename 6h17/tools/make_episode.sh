#!/bin/zsh
# Fabrique un épisode complet : voix -> bande-son -> image -> mixage final.
#   ./tools/make_episode.sh ep01            (tout)
#   ./tools/make_episode.sh ep01 --no-tts   (garde la voix existante)
#   ./tools/make_episode.sh ep01 --mix-only (re-mixe seulement le son)
# Tout tourne en priorité basse (nice) avec peu de threads pour ne pas saturer le Mac.
set -e
cd "$(dirname "$0")/.."
EP=${1:-ep01}; shift || true
PY=../.venv/bin/python
export OMP_NUM_THREADS=2
VOICE=${VOICE:-fr-FR-HenriNeural}

if [[ " $* " != *" --no-tts "* && " $* " != *" --mix-only "* ]]; then
  echo "▶ Voix ($VOICE)"
  nice -n 10 $PY tools/tts.py $EP/narration.txt $EP/audio/voice.mp3 $EP/audio/words.json $VOICE "+0%" "-4Hz"
fi
if [[ " $* " != *" --mix-only "* ]]; then
  echo "▶ Bande-son"
  nice -n 10 $PY $EP/sound.py
  echo "▶ Image"
  nice -n 10 $PY tools/render.py $EP
fi

echo "▶ Mixage final (voix traitée + ducking de la musique + normalisation -14 LUFS)"
OUT=$EP/build/6h17_${EP}_tiktok.mp4
nice -n 10 ffmpeg -y -v error -threads 2 \
  -i $EP/build/video_noaudio.mp4 -i $EP/audio/voice.mp3 -i $EP/audio/music_sfx.wav \
  -filter_complex "\
[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0,highpass=f=70,equalizer=f=180:t=q:w=1:g=2,equalizer=f=3200:t=q:w=1.2:g=2.5,\
acompressor=threshold=-20dB:ratio=3:attack=5:release=90:makeup=2,aecho=0.85:0.4:45|90:0.10|0.06,apad=pad_dur=4,asplit=2[v][sc];\
[2:a][sc]sidechaincompress=threshold=0.04:ratio=5:attack=15:release=350[m];\
[v][m]amix=inputs=2:normalize=0:weights=1 0.85,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart $OUT
echo "✔ $OUT"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 $OUT

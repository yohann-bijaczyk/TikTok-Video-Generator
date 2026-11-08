"""Narration TTS (edge-tts) + horodatage mot par mot -> audio.mp3 + words.json"""
import asyncio, json, sys, edge_tts

async def main(txt, out_mp3, out_json, voice, rate, pitch):
    text = open(txt, encoding="utf-8").read().replace("\n", " ")
    com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    words = []
    with open(out_mp3, "wb") as f:
        async for c in com.stream():
            if c["type"] == "audio":
                f.write(c["data"])
            elif c["type"] == "WordBoundary":
                words.append({"w": c["text"], "s": c["offset"] / 1e7, "e": (c["offset"] + c["duration"]) / 1e7})
    json.dump(words, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(words), "mots, fin", words[-1]["e"], "s")

if __name__ == "__main__":
    a = sys.argv
    asyncio.run(main(a[1], a[2], a[3], a[4] if len(a) > 4 else "fr-FR-HenriNeural",
                     a[5] if len(a) > 5 else "+0%", a[6] if len(a) > 6 else "+0Hz"))

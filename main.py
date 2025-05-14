from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
import ffmpeg
import os
import uuid

app = FastAPI()

class MediaRequest(BaseModel):
    images: list[str]
    audios: list[str]

@app.post("/assemble")
async def assemble_video(req: MediaRequest):
    # Download images and audios
    os.makedirs("tmp", exist_ok=True)
    image_files = []
    audio_files = []
    for idx, url in enumerate(req.images):
        img_path = f"tmp/img_{idx}.jpg"
        with open(img_path, "wb") as f:
            f.write(requests.get(url).content)
        image_files.append(img_path)
    for idx, url in enumerate(req.audios):
        audio_path = f"tmp/audio_{idx}.mp3"
        with open(audio_path, "wb") as f:
            f.write(requests.get(url).content)
        audio_files.append(audio_path)

    # Assemble video using ffmpeg (simple concat, 1 image per audio)
    video_segments = []
    for i, (img, aud) in enumerate(zip(image_files, audio_files)):
        seg = f"tmp/seg_{i}.mp4"
        (
            ffmpeg
            .input(img, loop=1, t=ffmpeg.probe(aud)['format']['duration'])
            .output(aud, vcodec='libx264', acodec='aac', strict='experimental', shortest=None, y=seg)
            .run(overwrite_output=True)
        )
        video_segments.append(seg)

    # Concatenate segments
    concat_file = "tmp/concat.txt"
    with open(concat_file, "w") as f:
        for seg in video_segments:
            f.write(f"file '{seg}'\n")
    output_path = f"tmp/output_{uuid.uuid4().hex}.mp4"
    ffmpeg.input(concat_file, format='concat', safe=0).output(output_path, c='copy', y=None).run(overwrite_output=True)

    # (Optional) Upload output_path to a file host and return the URL
    # For now, just return the local path
    return {"video_path": output_path}
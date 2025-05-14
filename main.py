from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import ffmpeg
import os
import uuid
import shutil

app = FastAPI()

class MediaRequest(BaseModel):
    images: list[str]
    audios: list[str]

@app.get("/")
async def root():
    return {"message": "Service is running"}

@app.post("/assemble")
async def assemble_video(req: MediaRequest):
    try:
        # Create tmp directory
        os.makedirs("tmp", exist_ok=True)
        image_files = []
        audio_files = []

        # Download images
        for idx, url in enumerate(req.images):
            img_path = f"tmp/img_{idx}.jpg"
            with open(img_path, "wb") as f:
                f.write(requests.get(url).content)
            image_files.append(img_path)

        # Download audios
        for idx, url in enumerate(req.audios):
            audio_path = f"tmp/audio_{idx}.mp3"
            with open(audio_path, "wb") as f:
                f.write(requests.get(url).content)
            audio_files.append(audio_path)

        # Assemble video using ffmpeg
        video_segments = []
        for i, (img, aud) in enumerate(zip(image_files, audio_files)):
            seg = f"tmp/seg_{i}.mp4"
            try:
                audio_duration = float(ffmpeg.probe(aud)['format']['duration'])
                (
                    ffmpeg
                    .input(img, loop=1, t=audio_duration)
                    .output(aud, vcodec='libx264', acodec='aac', strict='experimental', shortest=None, y=seg)
                    .run(overwrite_output=True)
                )
                video_segments.append(seg)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"FFmpeg error: {str(e)}")

        # Concatenate segments
        concat_file = "tmp/concat.txt"
        with open(concat_file, "w") as f:
            for seg in video_segments:
                f.write(f"file '{seg}'\n")
        output_path = f"tmp/output_{uuid.uuid4().hex}.mp4"
        try:
            ffmpeg.input(concat_file, format='concat', safe=0).output(output_path, c='copy', y=None).run(overwrite_output=True)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"FFmpeg concatenation error: {str(e)}")

        # Return the local path for now
        return {"video_path": output_path}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

    finally:
        # Cleanup temporary files
        if os.path.exists("tmp"):
            shutil.rmtree("tmp")
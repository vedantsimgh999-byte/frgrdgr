import streamlit as st
import os, subprocess, json, re, tempfile
from pathlib import Path

st.set_page_config(page_title="ClipForge AI", page_icon="✂️", layout="wide")

st.markdown("""
<style>
.stApp {background:#101116;}
h1,h2,h3,p,label {color:#f5f5f7;}
div[data-testid="stMetric"] {background:#1b1b23;padding:14px;border-radius:12px;}
</style>
""", unsafe_allow_html=True)

st.title("✂️ ClipForge AI")
st.caption("Local AI clipping studio • Prototype 1.0")

st.info("Use videos you own or have permission to edit and publish. This prototype processes uploaded files locally.")

with st.sidebar:
    st.header("Clip settings")
    clip_len = st.slider("Clip length (seconds)", 15, 90, 35)
    max_clips = st.slider("Maximum clips", 1, 20, 5)
    vertical = st.checkbox("Vertical 9:16 crop", True)
    captions = st.checkbox("Burn subtitles into clips", True)
    model_size = st.selectbox("Speech AI model", ["tiny", "base", "small"], index=0)
    st.caption("Smaller models run faster on most computers.")

uploaded = st.file_uploader("Upload a video", type=["mp4", "mov", "mkv", "webm", "avi"])

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def ffmpeg_exists():
    return run(["ffmpeg", "-version"]).returncode == 0

def safe_title(text):
    words = re.findall(r"[A-Za-z0-9']+", text)
    title = " ".join(words[:9])
    return (title[:65] or "Interesting moment") + ("..." if len(title) > 65 else "")

def analyze_video(path, model_size):
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        st.error("Speech AI package is missing. Install requirements first.")
        return None
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(path, word_timestamps=True, vad_filter=True)
    rows = []
    for seg in segments:
        rows.append({"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()})
    return rows

def make_srt(segments, start, end, output):
    selected = [s for s in segments if s["end"] > start and s["start"] < end]
    def stamp(sec):
        sec=max(0,sec)
        h=int(sec//3600); m=int((sec%3600)//60); s=int(sec%60); ms=int((sec-int(sec))*1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    with open(output, "w", encoding="utf-8") as f:
        for i,seg in enumerate(selected,1):
            a=max(start,seg["start"])-start
            b=min(end,seg["end"])-start
            txt=seg["text"].replace("-->","").strip()
            f.write(f"{i}\\n{stamp(a)} --> {stamp(b)}\\n{txt}\\n\\n")

def score_windows(segments, duration, clip_len, max_clips):
    # Heuristic scoring: speech density, emphatic words, and sentence changes.
    if duration <= clip_len:
        return [(0, duration)]
    windows=[]
    step=max(8,clip_len//3)
    hype=re.compile(r"\\b(wow|what|no way|crazy|insane|wait|bro|oh my god|unbelievable|win|lost|never|secret|amazing|finally|help|why|how)\\b", re.I)
    for start in range(0, max(1,int(duration-clip_len)), step):
        end=min(duration,start+clip_len)
        texts=[s["text"] for s in segments if s["end"]>start and s["start"]<end]
        joined=" ".join(texts)
        word_count=len(joined.split())
        hits=len(hype.findall(joined))
        # Encourage conversational density; this is a simple first-pass heuristic.
        score=word_count/clip_len + hits*0.45
        if joined.strip():
            windows.append((score,start,end,joined))
    windows.sort(reverse=True)
    chosen=[]
    for score,start,end,txt in windows:
        if all(abs(start-old[0])>clip_len*0.75 for old in chosen):
            chosen.append((start,end,txt))
        if len(chosen)>=max_clips: break
    chosen.sort()
    return chosen or [(0,min(duration,clip_len),"")]

if uploaded:
    st.write(f"Selected: **{uploaded.name}**")
    if st.button("🚀 Analyze & create clips", type="primary"):
        if not ffmpeg_exists():
            st.error("FFmpeg not found. Install it and restart the app. See README.")
            st.stop()
        work = Path("clipforge_work")
        work.mkdir(exist_ok=True)
        source = work / uploaded.name
        source.write_bytes(uploaded.getbuffer())
        probe = run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(source)])
        if probe.returncode:
            st.error("Could not read this video. Check that FFmpeg/FFprobe is installed.")
            st.stop()
        duration=float(probe.stdout.strip())
        st.write(f"Video duration: **{duration/60:.1f} minutes**")
        with st.spinner("Transcribing speech with local AI…"):
            segs=analyze_video(str(source),model_size)
        if not segs:
            st.stop()
        st.success(f"Transcribed {len(segs)} speech segments.")
        candidates=score_windows(segs,duration,clip_len,max_clips)
        outdir=work/"clips"
        outdir.mkdir(exist_ok=True)
        progress=st.progress(0)
        created=[]
        for idx,item in enumerate(candidates,1):
            start,end,txt=item
            name=f"clip_{idx:02d}"
            output=outdir/f"{name}.mp4"
            srt=outdir/f"{name}.srt"
            make_srt(segs,start,end,str(srt))
            filters=[]
            if vertical:
                filters.append("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920")
            if captions:
                # Escape path for FFmpeg subtitles filter
                sp=str(srt.resolve()).replace("\\\\","/").replace(":","\\\\:")
                filters.append(f"subtitles='{sp}'")
            cmd=["ffmpeg","-y","-ss",str(start),"-i",str(source),"-t",str(end-start),"-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac"]
            if filters:
                cmd += ["-vf",",".join(filters)]
            cmd += ["-movflags","+faststart",str(output)]
            res=run(cmd)
            if res.returncode==0 and output.exists():
                title=safe_title(txt)
                created.append((output,title,start,end,txt))
            else:
                st.warning(f"Could not render clip {idx}. FFmpeg error: {res.stderr[-500:]}")
            progress.progress(idx/len(candidates))
        st.session_state["created"]=created
        st.session_state["segments"]=segs
        st.session_state["outdir"]=str(outdir)
        st.success(f"Done! Created {len(created)} clips.")

if "created" in st.session_state:
    st.header("🎬 Your clips")
    clips=st.session_state["created"]
    for i,(path,title,start,end,txt) in enumerate(clips,1):
        with st.expander(f"Clip {i}: {title}", expanded=True):
            st.video(str(path))
            st.write(f"**Suggested title:** {title}")
            st.write(f"**Time:** {start:.1f}s – {end:.1f}s")
            if txt:
                st.caption(txt)
            with open(path,"rb") as f:
                st.download_button(f"⬇️ Download clip {i}",f.read(),file_name=path.name,mime="video/mp4",key=f"dl{i}")
    zip_path=Path(st.session_state["outdir"])/"all_clips.zip"
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as z:
        for p, *_ in clips: z.write(p,arcname=p.name)
    with open(zip_path,"rb") as f:
        st.download_button("📦 Download all clips (ZIP)",f.read(),file_name="ClipForge_clips.zip",mime="application/zip")

st.divider()
st.markdown("**Next version roadmap:** authorized live-stream monitoring → highlight scoring → auto titles & thumbnails → YouTube OAuth upload → posting schedule.")

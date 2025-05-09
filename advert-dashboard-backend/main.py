"""
main.py – Advertising Dashboard MVP (v2.1)
──────────────────────────────────────────
Run:
    uvicorn main:app --reload
"""

# ───────── imports ─────────
import os, uuid, datetime, shutil, base64, logging, requests
from typing import List, Dict
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from jose import jwt
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from openai import OpenAI

# ───────── env & paths ─────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set")
client = OpenAI(api_key=OPENAI_API_KEY)

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
UPLOADS   = os.path.join(BASE_DIR, "uploads")
GENERATED = os.path.join(BASE_DIR, "generated")
os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(GENERATED, exist_ok=True)

# ───────── FastAPI ─────────
app = FastAPI(title="AlemX Advertising Dashboard – API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
app.mount("/static/uploads",   StaticFiles(directory=UPLOADS),   name="uploads")
app.mount("/static/generated", StaticFiles(directory=GENERATED), name="generated")

# ───────── auth (mock) ─────────
SECRET, ALG = "CHANGE-ME", "HS256"
oauth2 = OAuth2PasswordBearer(tokenUrl="login")
_FAKE_USERS = {"demo@alemx.com": {"password": "demo123", "name": "Demo"}}

def _issue(email: str) -> str:
    return jwt.encode(
        {"sub": email, "iat": datetime.datetime.utcnow().timestamp()},
        SECRET,
        algorithm=ALG,
    )

def _user(tok: str = Depends(oauth2)):
    try:
        return _FAKE_USERS[jwt.decode(tok, SECRET, [ALG])["sub"]]
    except:  # noqa: E722  (demo only)
        raise HTTPException(401, "Invalid token")

@app.post("/login")
async def login(f: OAuth2PasswordRequestForm = Depends()):
    u = _FAKE_USERS.get(f.username)
    if not u or u["password"] != f.password:
        raise HTTPException(401, "Bad credentials")
    return {"access_token": _issue(f.username), "token_type": "bearer"}

# ───────── models ─────────
class Targeting(BaseModel):
    age_min: int
    age_max: int
    location: str
    interests: List[str]

    @field_validator("age_max")
    @classmethod
    def _chk(cls, v, info):
        if v < info.data["age_min"]:
            raise ValueError("age_max ≥ age_min")
        return v

class CampaignRequest(BaseModel):
    name: str
    prompt: str
    use_reference: bool                         # ← edit-with-image flag
    derive_prompt_from_reference: bool | None = False  # ← NEW flag
    targeting: Targeting
    reference_filename: str | None = None      # ← filename from /upload_reference

class Campaign(BaseModel):
    id: str
    name: str
    prompt: str
    reference_filename: str | None
    generated_filename: str
    ad_copy: str
    created_at: datetime.datetime
    status: str
    targeting: Targeting
    impressions: int
    clicks: int
    ctr: float

# ───────── store (in-memory) ─────────
CAMPAIGNS: Dict[str, Campaign] = {}

# ───────── helpers ─────────
def _dl(url: str, dest: str):
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    with open(dest, "wb") as f:
        f.write(r.content)

def _describe_image(path: str, max_tokens: int = 60) -> str:
    """
    Return a short GPT-4o Vision description of the image so the model
    can later re-imagine it without needing the original file.
    """
    import mimetypes
    mime, _ = mimetypes.guess_type(path)
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    data_url = f"data:{mime};base64,{b64}"
    rsp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Very briefly describe the main visual elements in this "
                            "image so an artist could recreate it. ≤20 words."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        max_tokens=max_tokens,
    )
    return rsp.choices[0].message.content.strip()

# ───────── uploads ─────────
@app.post("/upload_reference")
async def upload_reference(file: UploadFile = File(...), user = Depends(_user)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(400, "PNG/JPG only")
    fname = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOADS, fname), "wb") as buf:
        shutil.copyfileobj(file.file, buf)
    return {"filename": fname, "url": f"/static/uploads/{fname}"}

@app.post("/upload_reference_url")
async def upload_reference_url(url: str, user = Depends(_user)):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(400, f"Fetch failed: {e}")
    if "image" not in r.headers.get("content-type", ""):
        raise HTTPException(400, "URL not an image")
    ext = ".png" if "png" in r.headers["content-type"] else ".jpg"
    fname = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOADS, fname), "wb") as f:
        f.write(r.content)
    return {"filename": fname, "url": f"/static/uploads/{fname}"}

# ───────── create campaign ─────────
@app.post("/campaigns", response_model = Campaign)
async def create_campaign(req: CampaignRequest, user = Depends(_user)):
    cid      = f"cmp_{uuid.uuid4().hex[:8]}"
    gen_name = f"{uuid.uuid4().hex}.png"
    gen_path = os.path.join(GENERATED, gen_name)

    # 0. Optional: derive prompt from the uploaded reference image
    img_description = ""
    if (
        req.derive_prompt_from_reference
        and req.reference_filename
        and os.path.exists(os.path.join(UPLOADS, req.reference_filename))
    ):
        try:
            img_path = os.path.join(UPLOADS, req.reference_filename)
            img_description = _describe_image(img_path)
        except Exception as e:
            logging.warning(f"Vision describe error: {e}")

    # 1. Build final prompt
    tgt = req.targeting
    audience = f"{tgt.age_min}-{tgt.age_max} y/o in {tgt.location}"
    if tgt.interests:
        audience += f" interested in {', '.join(tgt.interests)}"
    base_prompt = req.prompt.strip()
    if img_description:
        base_prompt = f"{base_prompt}. Visual cues: {img_description}"
    full_prompt = f"{base_prompt}. 1024×1024 banner for {audience}."

    # 2. Generate or edit the image
    try:
        if req.use_reference and req.reference_filename:
            # Mode A – edit the reference image
            ref_path = os.path.join(UPLOADS, req.reference_filename)
            with open(ref_path, "rb") as img_fp:
                rsp = client.images.edit(
                    model = "gpt-image-1",
                    image = [img_fp],
                    prompt = full_prompt,
                )
        else:
            # Mode B or C – pure generation (may include auto-description)
            rsp = client.images.generate(
                model  = "gpt-image-1",
                prompt = full_prompt,
                n      = 1,
                size   = "1024x1024",
            )
        dat = rsp.data[0]
        if getattr(dat, "url", None):
            _dl(dat.url, gen_path)
        else:
            with open(gen_path, "wb") as f:
                f.write(base64.b64decode(dat.b64_json))
    except Exception as e:
        raise HTTPException(502, f"OpenAI image error: {e}")

    # 3. Generate ad copy (headline)
    try:
        chat = client.chat.completions.create(
            model   = "gpt-4o-mini",
            messages = [
                {
                    "role": "user",
                    "content": (
                        f"Write a catchy one-sentence headline for '{req.prompt}' "
                        f"targeting {audience}. Respond with only the headline."
                    ),
                }
            ],
            max_tokens = 25,
        )
        ad_copy = chat.choices[0].message.content.strip()
    except Exception as e:
        ad_copy = "Your perfect headline here!"
        logging.warning(e)

    # 4. Mock metrics
    impressions = int(50_000 + 50_000 * (uuid.uuid4().int % 100) / 100)
    clicks      = int(impressions * 0.018 + (uuid.uuid4().int % 500))
    ctr         = round(clicks / impressions * 100, 2)

    # 5. Persist in memory
    camp = Campaign(
        id = cid,
        name = req.name,
        prompt = req.prompt,
        reference_filename = req.reference_filename,
        generated_filename = gen_name,
        ad_copy = ad_copy,
        created_at = datetime.datetime.utcnow(),
        status = "submitted",
        targeting = req.targeting,
        impressions = impressions,
        clicks = clicks,
        ctr = ctr,
    )
    CAMPAIGNS[cid] = camp
    return camp

# ───────── retrieval routes ─────────
@app.get("/campaigns", response_model = List[Campaign])
async def list_campaigns(user = Depends(_user)):
    return sorted(CAMPAIGNS.values(), key = lambda c: c.created_at, reverse = True)

@app.get("/campaigns/{cid}", response_model = Campaign)
async def get_campaign(cid: str, user = Depends(_user)):
    camp = CAMPAIGNS.get(cid)
    if not camp:
        raise HTTPException(404, "Not found")
    return camp

@app.get("/")
async def root():
    return {"msg": "API ready"}

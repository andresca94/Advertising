"""
main.py  –  Advertising-Dashboard MVP for AlemX
==============================================

Run with:
$ uvicorn main:app --reload
"""

# ───────────── imports ─────────────
import os, uuid, datetime, shutil, requests
from typing import List, Dict

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from jose import jwt
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
import openai

# ───────────── env & paths ─────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in .env")
openai.api_key = OPENAI_API_KEY

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
UPLOADS       = os.path.join(BASE_DIR, "uploads")      # user files
GENERATED     = os.path.join(BASE_DIR, "generated")    # GPT images
os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(GENERATED, exist_ok=True)

# ───────────── app ─────────────────
app = FastAPI(title="AlemX Advertising Dashboard – API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.mount("/static/uploads",   StaticFiles(directory=UPLOADS),   name="uploads")
app.mount("/static/generated", StaticFiles(directory=GENERATED), name="generated")

# ───────────── auth (mock) ─────────
SECRET = "CHANGE-ME"
ALG    = "HS256"
oauth2 = OAuth2PasswordBearer(tokenUrl="login")

_FAKE_USERS = {"demo@alemx.com": {"password": "demo123", "name": "Demo"}}

def _issue_token(email: str) -> str:
    payload = {"sub": email, "iat": datetime.datetime.utcnow().timestamp()}
    return jwt.encode(payload, SECRET, algorithm=ALG)

def _current_user(token: str = Depends(oauth2)):
    try:
        email = jwt.decode(token, SECRET, algorithms=[ALG])["sub"]
        return _FAKE_USERS[email]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = _FAKE_USERS.get(form.username)
    if not user or user["password"] != form.password:
        raise HTTPException(status_code=401, detail="Bad credentials")
    return {"access_token": _issue_token(form.username), "token_type": "bearer"}

# ───────────── models ──────────────
class Targeting(BaseModel):
    age_min: int
    age_max: int
    location: str
    interests: List[str]

    @field_validator("age_max")
    @classmethod
    def _check(cls, v, info):
        if v < info.data["age_min"]:
            raise ValueError("age_max must be >= age_min")
        return v

class CampaignRequest(BaseModel):
    name: str
    prompt: str
    targeting: Targeting
    reference_filename: str | None = None

class Campaign(BaseModel):
    id: str
    name: str
    prompt: str
    reference_filename: str | None
    generated_filename: str
    created_at: datetime.datetime
    status: str
    targeting: Targeting
    impressions: int
    clicks: int

# ───────────── storage ─────────────
CAMPAIGNS: Dict[str, Campaign] = {}
MOCK_INTERESTS = ["sports", "gaming", "fashion", "tech", "travel", "music"]

# ───────────── helpers ─────────────
def _dl(url: str, dest: str):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    with open(dest, "wb") as f:
        f.write(r.content)

# ───────────── file upload ─────────
@app.post("/upload_reference")
async def upload_reference(file: UploadFile = File(...),
                           user=Depends(_current_user)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="PNG/JPG only")
    fname = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOADS, fname), "wb") as buf:
        shutil.copyfileobj(file.file, buf)
    return {"filename": fname, "url": f"/static/uploads/{fname}"}

@app.post("/upload_reference_url")
async def upload_reference_url(url: str, user=Depends(_current_user)):
    try:
        r = requests.get(url, timeout=10); r.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Fetch failed: {e}")
    if "image" not in r.headers.get("content-type", ""):
        raise HTTPException(status_code=400, detail="URL not an image")
    ext = ".png" if "png" in r.headers["content-type"] else ".jpg"
    fname = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOADS, fname), "wb") as f:
        f.write(r.content)
    return {"filename": fname, "url": f"/static/uploads/{fname}"}

# ───────────── bonus endpoints ─────
@app.get("/mock_interests")
async def mock_interests():
    return {"interests": MOCK_INTERESTS}

class CopyReq(BaseModel):
    product: str
    targeting: Targeting

@app.post("/generate_ad_copy")
async def generate_ad_copy(req: CopyReq, user=Depends(_current_user)):
    prompt = (f"Write one catchy banner line for '{req.product}' aimed at "
              f"{req.targeting.age_min}-{req.targeting.age_max} year-olds in "
              f"{req.targeting.location} who like {', '.join(req.targeting.interests)}.")
    res = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=25,
    )
    return {"headline": res.choices[0].message.content.strip()}

# ───────────── create campaign ─────
@app.post("/campaigns", response_model=Campaign)
async def create_campaign(req: CampaignRequest, user=Depends(_current_user)):
    cid = f"cmp_{uuid.uuid4().hex[:8]}"
    try:
        img = openai.images.generate(
            model="gpt-image-1", prompt=req.prompt, n=1, size="1024x1024"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {e}")
    gen_name = f"{cid}.png"
    _dl(img.data[0].url, os.path.join(GENERATED, gen_name))

    impr = int(10_000 + 90_000 * (uuid.uuid4().int % 100) / 100)
    clk  = int(impr * 0.02)

    camp = Campaign(
        id=cid, name=req.name, prompt=req.prompt,
        reference_filename=req.reference_filename,
        generated_filename=gen_name,
        created_at=datetime.datetime.now(), status="submitted",
        targeting=req.targeting, impressions=impr, clicks=clk,
    )
    CAMPAIGNS[cid] = camp
    print(f"📤 campaign {cid} created")
    return camp

@app.get("/campaigns", response_model=List[Campaign])
async def list_campaigns(user=Depends(_current_user)):
    return sorted(CAMPAIGNS.values(), key=lambda c: c.created_at, reverse=True)

@app.get("/campaigns/{cid}", response_model=Campaign)
async def get_campaign(cid: str, user=Depends(_current_user)):
    camp = CAMPAIGNS.get(cid)
    if not camp:
        raise HTTPException(status_code=404, detail="Not found")
    return camp

# ───────────── health check ────────
@app.get("/")
async def root():
    return {"msg": "AlemX advertising dashboard API ready"}

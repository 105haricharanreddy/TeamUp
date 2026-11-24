import os, sqlite3, hashlib, secrets, json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("DATABASE_PATH", str(ROOT / "teamup.db"))
SECRET = os.getenv("SECRET_KEY", "change-this-secret-before-deploying")
serializer = URLSafeTimedSerializer(SECRET, salt="teamup-auth")
app = FastAPI(title="TeamUp API", version="1.0.0", description="Student project collaboration platform")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
          email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS profiles (
          user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
          college TEXT NOT NULL DEFAULT '', department TEXT NOT NULL DEFAULT '',
          year TEXT NOT NULL DEFAULT '', skills TEXT NOT NULL DEFAULT '',
          interests TEXT NOT NULL DEFAULT '', bio TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS projects (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
          description TEXT NOT NULL, owner_id INTEGER NOT NULL REFERENCES users(id),
          team_size INTEGER NOT NULL DEFAULT 4, skills TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS join_requests (
          id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          status TEXT NOT NULL DEFAULT 'Pending', created_at TEXT NOT NULL,
          UNIQUE(project_id,user_id)
        );
        CREATE TABLE IF NOT EXISTS connections (
          id INTEGER PRIMARY KEY AUTOINCREMENT, from_user INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          to_user INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          status TEXT NOT NULL DEFAULT 'Pending', created_at TEXT NOT NULL,
          UNIQUE(from_user,to_user), CHECK(from_user <> to_user)
        );
        """)
init_db()

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
class LoginIn(BaseModel):
    email: EmailStr
    password: str
class ProfileIn(BaseModel):
    college: str = ""; department: str = ""; year: str = ""
    skills: str = ""; interests: str = ""; bio: str = ""
class ProjectIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=3000)
    team_size: int = Field(default=4, ge=2, le=10)
    skills: str = Field(min_length=1, max_length=500)
class StatusIn(BaseModel):
    status: str

def hash_password(password):
    salt=secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,310000)
    import base64
    return base64.b64encode(salt+digest).decode()
def verify_password(password, stored):
    import base64, hmac
    raw=base64.b64decode(stored.encode())
    return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256",password.encode(),raw[:16],310000),raw[16:])
def token_for(user):
    return serializer.dumps({"uid":user["id"],"email":user["email"]})
def current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401,"Please log in.")
    try:
        data=serializer.loads(authorization.split(" ",1)[1],max_age=60*60*24*7)
    except (BadSignature,SignatureExpired):
        raise HTTPException(401,"Session expired. Please log in again.")
    with db() as c: user=c.execute("SELECT id,name,email FROM users WHERE id=?",(data["uid"],)).fetchone()
    if not user: raise HTTPException(401,"User not found.")
    return dict(user)
def project_json(row):
    d=dict(row); d["skills"]=[x.strip() for x in d.pop("skills","").split(",") if x.strip()]
    d["owner"]=d.pop("owner_name"); d["owner_email"]=d.pop("owner_email")
    return d

@app.get("/api/health")
def health(): return {"status":"ok","service":"TeamUp API"}
@app.post("/api/auth/register")
def register(body:RegisterIn):
    email=body.email.lower()
    with db() as c:
        try:
            cur=c.execute("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",
                          (body.name.strip(),email,hash_password(body.password),datetime.now(timezone.utc).isoformat()))
            uid=cur.lastrowid
        except sqlite3.IntegrityError: raise HTTPException(409,"An account with this email already exists.")
        c.execute("INSERT INTO profiles(user_id) VALUES(?)",(uid,))
        user={"id":uid,"name":body.name.strip(),"email":email}
    return {"token":token_for(user),"user":user}
@app.post("/api/auth/login")
def login(body:LoginIn):
    with db() as c: user=c.execute("SELECT * FROM users WHERE email=?",(body.email.lower(),)).fetchone()
    if not user or not verify_password(body.password,user["password_hash"]): raise HTTPException(401,"Incorrect email or password.")
    u={"id":user["id"],"name":user["name"],"email":user["email"]}
    return {"token":token_for(u),"user":u}
@app.get("/api/me")
def me(user=Depends(current_user)): return user

@app.get("/api/profile")
def get_profile(user=Depends(current_user)):
    with db() as c: row=c.execute("SELECT * FROM profiles WHERE user_id=?",(user["id"],)).fetchone()
    return dict(row) if row else {}
@app.put("/api/profile")
def save_profile(body:ProfileIn,user=Depends(current_user)):
    with db() as c:
        c.execute("""INSERT INTO profiles(user_id,college,department,year,skills,interests,bio)
        VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET college=excluded.college,
        department=excluded.department,year=excluded.year,skills=excluded.skills,
        interests=excluded.interests,bio=excluded.bio""",
        (user["id"],body.college,body.department,body.year,body.skills,body.interests,body.bio))
    return {"message":"Profile saved successfully."}
@app.get("/api/students")
def students(user=Depends(current_user)):
    with db() as c:
        rows=c.execute("""SELECT u.id,u.name,u.email,p.college,p.department,p.year,p.skills,p.interests,p.bio
        FROM users u JOIN profiles p ON p.user_id=u.id WHERE u.id<>? ORDER BY u.name""",(user["id"],)).fetchall()
    return [dict(r) for r in rows]

@app.get("/api/projects")
def list_projects(user=Depends(current_user)):
    with db() as c:
        rows=c.execute("""SELECT p.*,u.name owner_name,u.email owner_email FROM projects p
        JOIN users u ON u.id=p.owner_id ORDER BY p.id DESC""").fetchall()
    return [project_json(r) for r in rows]
@app.post("/api/projects")
def create_project(body:ProjectIn,user=Depends(current_user)):
    with db() as c:
        cur=c.execute("INSERT INTO projects(name,description,owner_id,team_size,skills,created_at) VALUES(?,?,?,?,?,?)",
        (body.name,body.description,user["id"],body.team_size,body.skills,datetime.now(timezone.utc).isoformat()))
        pid=cur.lastrowid
        row=c.execute("SELECT p.*,u.name owner_name,u.email owner_email FROM projects p JOIN users u ON u.id=p.owner_id WHERE p.id=?",(pid,)).fetchone()
    return project_json(row)
@app.get("/api/projects/{project_id}")
def project_detail(project_id:int,user=Depends(current_user)):
    with db() as c:
        row=c.execute("""SELECT p.*,u.name owner_name,u.email owner_email FROM projects p
        JOIN users u ON u.id=p.owner_id WHERE p.id=?""",(project_id,)).fetchone()
        if not row: raise HTTPException(404,"Project not found.")
        requests=c.execute("""SELECT jr.id,jr.status,jr.user_id,u.name,u.email FROM join_requests jr
        JOIN users u ON u.id=jr.user_id WHERE jr.project_id=?""",(project_id,)).fetchall()
    d=project_json(row); d["requests"]=[dict(x) for x in requests] if row["owner_id"]==user["id"] else []
    return d
@app.post("/api/projects/{project_id}/join")
def join_project(project_id:int,user=Depends(current_user)):
    with db() as c:
        p=c.execute("SELECT * FROM projects WHERE id=?",(project_id,)).fetchone()
        if not p: raise HTTPException(404,"Project not found.")
        if p["owner_id"]==user["id"]: raise HTTPException(400,"You already own this project.")
        try:c.execute("INSERT INTO join_requests(project_id,user_id,created_at) VALUES(?,?,?)",(project_id,user["id"],datetime.now(timezone.utc).isoformat()))
        except sqlite3.IntegrityError: raise HTTPException(409,"You have already requested to join this project.")
    return {"message":"Join request sent."}
@app.patch("/api/join-requests/{request_id}")
def update_join_request(request_id:int,body:StatusIn,user=Depends(current_user)):
    if body.status not in ("Accepted","Rejected"): raise HTTPException(400,"Invalid status.")
    with db() as c:
        row=c.execute("""SELECT jr.id,p.owner_id FROM join_requests jr JOIN projects p ON p.id=jr.project_id WHERE jr.id=?""",(request_id,)).fetchone()
        if not row: raise HTTPException(404,"Request not found.")
        if row["owner_id"]!=user["id"]: raise HTTPException(403,"Only the project owner can review requests.")
        if body.status == "Accepted":
            info=c.execute("SELECT p.team_size, COUNT(jr.id) AS accepted_count FROM projects p LEFT JOIN join_requests jr ON jr.project_id=p.id AND jr.status='Accepted' WHERE p.id=(SELECT project_id FROM join_requests WHERE id=?) GROUP BY p.id",(request_id,)).fetchone()
            if info and info["accepted_count"] >= info["team_size"] - 1:
                raise HTTPException(409,"This project has reached its maximum team size.")
        c.execute("UPDATE join_requests SET status=? WHERE id=?",(body.status,request_id))
    return {"message":f"Request {body.status.lower()}."}
@app.get("/api/my-work")
def my_work(user=Depends(current_user)):
    with db() as c:
        created=c.execute("""SELECT p.*,u.name owner_name,u.email owner_email FROM projects p JOIN users u ON u.id=p.owner_id WHERE p.owner_id=? ORDER BY p.id DESC""",(user["id"],)).fetchall()
        req=c.execute("""SELECT jr.id request_id,jr.status,p.id project_id,p.name,p.description FROM join_requests jr JOIN projects p ON p.id=jr.project_id WHERE jr.user_id=? ORDER BY jr.id DESC""",(user["id"],)).fetchall()
        created_items=[]
        for p in created:
            project=project_json(p)
            project["requests"]=[dict(x) for x in c.execute(
                "SELECT jr.id,jr.status,jr.user_id,u.name,u.email FROM join_requests jr JOIN users u ON u.id=jr.user_id WHERE jr.project_id=?",
                (p["id"],)).fetchall()]
            created_items.append(project)
        requested_items=[dict(x) for x in req]
    return {"created":created_items,"requested":requested_items}
@app.post("/api/connections/{student_id}")
def connect(student_id:int,user=Depends(current_user)):
    if student_id==user["id"]: raise HTTPException(400,"You cannot connect with yourself.")
    with db() as c:
        if not c.execute("SELECT id FROM users WHERE id=?",(student_id,)).fetchone(): raise HTTPException(404,"Student not found.")
        try:c.execute("INSERT INTO connections(from_user,to_user,created_at) VALUES(?,?,?)",(user["id"],student_id,datetime.now(timezone.utc).isoformat()))
        except sqlite3.IntegrityError: raise HTTPException(409,"A connection request already exists.")
    return {"message":"Connection request sent."}
@app.get("/api/connections")
def get_connections(user=Depends(current_user)):
    with db() as c:
        incoming=c.execute("""SELECT c.id,c.status,u.id user_id,u.name,u.email FROM connections c JOIN users u ON u.id=c.from_user WHERE c.to_user=? AND c.status='Pending'""",(user["id"],)).fetchall()
        accepted=c.execute("""SELECT c.id,c.status,u.name,u.email FROM connections c JOIN users u ON u.id=CASE WHEN c.from_user=? THEN c.to_user ELSE c.from_user END WHERE (c.from_user=? OR c.to_user=?) AND c.status='Accepted'""",(user["id"],user["id"],user["id"])).fetchall()
    return {"incoming":[dict(x) for x in incoming],"accepted":[dict(x) for x in accepted]}
@app.patch("/api/connections/{connection_id}")
def update_connection(connection_id:int,body:StatusIn,user=Depends(current_user)):
    if body.status not in ("Accepted","Rejected"): raise HTTPException(400,"Invalid status.")
    with db() as c:
        row=c.execute("SELECT * FROM connections WHERE id=? AND to_user=?",(connection_id,user["id"])).fetchone()
        if not row: raise HTTPException(404,"Request not found.")
        c.execute("UPDATE connections SET status=? WHERE id=?",(body.status,connection_id))
    return {"message":"Connection request updated."}

# Serve the existing multi-page frontend from the same service.
app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
@app.get("/")
def home(): return FileResponse(ROOT/"frontend"/"index.html")

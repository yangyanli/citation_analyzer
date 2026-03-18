"""FastAPI backend server for Citation Analyzer.

Provides REST endpoints wrapping the database layer. Authentication context
is provided via internal HTTP headers set by the Next.js frontend proxy.
"""

from __future__ import annotations
import json
import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Depends, Query
from pydantic import BaseModel

# Database modules
from backend.database.connection import get_db_connection
from backend.database import auth as db_auth
from backend.database import admin as db_admin
from backend.database import targets as db_targets
from backend.database import schema as db_schema

app = FastAPI(title="Citation Analyzer API")

# Ensure DB is initialized
db_schema.init_db()

# --- Dependencies & Auth ---

def get_current_user(request: Request) -> dict | None:
    """Extract user context from proxy headers."""
    user_id = request.headers.get("x-user-id")
    if not user_id:
        return None
    
    role = request.headers.get("x-user-role", "viewer")
    groups_str = request.headers.get("x-user-groups", "[]")
    groups = []
    try:
        groups = json.loads(groups_str)
    except json.JSONDecodeError:
        pass
        
    return {
        "id": int(user_id),
        "role": role,
        "groups": groups
    }

def require_roles(allowed_roles: list[str]):
    """Dependency factory for checking user roles."""
    def role_checker(user: dict | None = Depends(get_current_user)) -> dict:
        if not user or user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Unauthorized")
        return user
    return role_checker

# --- Models ---

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class PasswordUpdateRequest(BaseModel):
    newPassword: str

class GroupRequest(BaseModel):
    name: str | None = None
    is_public: bool | None = None

class GroupUserRequest(BaseModel):
    userId: int

class UserRoleRequest(BaseModel):
    userId: int
    role: str

class TargetIdRequest(BaseModel):
    target_id: str

class CitationUpdateRequest(BaseModel):
    score: int | None = None
    usage_classification: str | None = None
    positive_comment: str | None = None
    sentiment_evidence: str | None = None
    is_seminal: bool | None = None
    seminal_evidence: str | None = None
    paper_homepage: str | None = None
    notable_authors: list | None = None
    revert_to_ai: bool | None = None
    citing_title: str | None = None
    year: int | None = None
    venue: str | None = None
    authors: list | None = None

class VerifyRequest(BaseModel):
    author_name: str
    new_evidence: str | None = None
    new_homepage: str | None = None

class FallbackSubmitRequest(BaseModel):
    runFolder: str
    responseFile: str
    responseContent: str

# --- Targets API ---

@app.get("/api/targets")
def get_targets(user: dict | None = Depends(get_current_user)):
    with get_db_connection() as conn:
        columns = [c["name"] for c in conn.execute("PRAGMA table_info(analysis_targets)").fetchall()]
        has_status = "status" in columns

        query = "SELECT t.*, g.name as group_name, g.is_public FROM analysis_targets t LEFT JOIN groups g ON t.group_id = g.id"
        params = []

        if not user or user["role"] == "viewer":
            query += " WHERE g.is_public = 1"
        elif user["role"] in ("editor", "admin"):
            group_ids = [g["id"] for g in user["groups"]]
            if group_ids:
                placeholders = ",".join("?" for _ in group_ids)
                query += f" WHERE g.is_public = 1 OR t.group_id IN ({placeholders})"
                params.extend(group_ids)
            else:
                query += " WHERE g.is_public = 1"
        
        rows = conn.execute(query, params).fetchall()
        
        targets_map = {}
        scholar_target_ids = []
        for row in rows:
            r = dict(row)
            tid = r["target_id"]
            if r["mode"] == "scholar":
                scholar_target_ids.append(tid)
                
            targets_map[tid] = {
                "mode": r["mode"],
                "name": r["name"],
                "url": r["url"],
                "interests": json.loads(r["interests"]) if r.get("interests") else [],
                "evaluation_criteria": json.loads(r["evaluation_criteria"]) if r.get("evaluation_criteria") else None,
                "status": r["status"] if has_status else "completed",
                "progress": r["progress"] if has_status else 100,
                "error": r["error"] if has_status else None,
                "total_citations": r.get("total_citations", 0),
                "s2_total_citations": r.get("s2_total_citations", 0),
                "user_id": tid if r["mode"] == "scholar" else None,
                "title": tid if r["mode"] == "paper" else None,
                "s2_url": r["url"] if r["mode"] == "paper" else None,
                "group_id": r.get("group_id"),
                "group_name": r.get("group_name"),
                "is_public": bool(r.get("is_public")),
                "p2_est_batches": r.get("p2_est_batches", 0),
                "p2_est_cost": r.get("p2_est_cost", 0.0),
                "p3_est_batches": r.get("p3_est_batches", 0),
                "p3_est_cost": r.get("p3_est_cost", 0.0),
                "p4_est_batches": r.get("p4_est_batches", 0),
                "p4_est_cost": r.get("p4_est_cost", 0.0),
                "p5_est_batches": r.get("p5_est_batches", 0),
                "p5_est_cost": r.get("p5_est_cost", 0.0),
            }

        derived_papers = []
        if scholar_target_ids:
            placeholders = ",".join("?" for _ in scholar_target_ids)
            paper_rows = conn.execute(
                f"""SELECT cited_title, target_id, COUNT(*) as citation_count 
                 FROM citations 
                 WHERE target_id IN ({placeholders}) 
                 GROUP BY cited_title, target_id 
                 ORDER BY citation_count DESC""",
                scholar_target_ids
            ).fetchall()
            
            for pr in paper_rows:
                derived_papers.append({
                    "cited_title": pr["cited_title"],
                    "source_target_id": pr["target_id"],
                    "citation_count": pr["citation_count"]
                })

        return {"targets": targets_map, "derived_papers": derived_papers}

@app.delete("/api/targets/{target_id}")
def delete_target(target_id: str, user: dict = Depends(require_roles(["admin", "super_admin"]))):
    if db_targets.delete_analysis_target(target_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Target not found")

@app.post("/api/targets/pause")
def pause_target(req: TargetIdRequest, user: dict = Depends(require_roles(["admin", "super_admin"]))):
    with get_db_connection() as conn:
        target = conn.execute("SELECT status, group_id FROM analysis_targets WHERE target_id = ?", (req.target_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")
            
        if user["role"] == "admin":
            if not any(g["id"] == target["group_id"] for g in user["groups"]):
                raise HTTPException(status_code=403, detail="Unauthorized: You are not an admin of this group")
                
        if target["status"] in ("completed", "failed"):
            raise HTTPException(status_code=400, detail="Cannot pause a completed or failed task")
            
        conn.execute("UPDATE analysis_targets SET status = 'paused' WHERE target_id = ?", (req.target_id,))
    return {"success": True, "message": "Target paused successfully"}

@app.post("/api/targets/cancel")
def cancel_target(req: TargetIdRequest, user: dict = Depends(require_roles(["admin", "super_admin"]))):
    with get_db_connection() as conn:
        target = conn.execute("SELECT status, group_id FROM analysis_targets WHERE target_id = ?", (req.target_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")
            
        if user["role"] == "admin":
            if not any(g["id"] == target["group_id"] for g in user["groups"]):
                raise HTTPException(status_code=403, detail="Unauthorized: You are not an admin of this group")
                
        conn.execute("UPDATE analysis_targets SET status = 'cancelled' WHERE target_id = ?", (req.target_id,))
    return {"success": True, "message": "Target cancelled successfully"}

# --- Citations API ---

@app.get("/api/citations")
def get_citations(target_id: str = Query(...), user: dict | None = Depends(get_current_user)):
    with get_db_connection() as conn:
        target_row = conn.execute(
            """SELECT t.*, g.is_public 
               FROM analysis_targets t 
               LEFT JOIN groups g ON t.group_id = g.id 
               WHERE t.target_id = ?""",
            (target_id,)
        ).fetchone()
        
        if not target_row:
            raise HTTPException(status_code=404, detail="Target not found")
            
        is_public = bool(target_row["is_public"])
        has_access = is_public
        
        if not has_access and user and user["role"] != "super_admin":
            if user["role"] in ("editor", "admin") and target_row["group_id"]:
                if any(g["id"] == target_row["group_id"] for g in user["groups"]):
                    has_access = True
                    
        if not has_access and (not user or user["role"] != "super_admin"):
            raise HTTPException(status_code=403, detail="Unauthorized")

        eval_criteria = json.loads(target_row["evaluation_criteria"]) if target_row["evaluation_criteria"] else None
        
        if target_row["mode"] == "paper":
            paper_title = target_row["name"]
            s2_cache = conn.execute("SELECT paper_id FROM s2_search_cache WHERE title = ?", (paper_title,)).fetchone()
            paper_id = s2_cache["paper_id"] if s2_cache else None
            
            if paper_id:
                rows = conn.execute("SELECT * FROM citations WHERE target_id = ? OR cited_title = ? OR cited_paper_id = ?", (target_id, paper_title, paper_id)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM citations WHERE target_id = ? OR cited_title = ?", (target_id, paper_title)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM citations WHERE target_id = ?", (target_id,)).fetchall()

        mapped = []
        for r in rows:
            row = dict(r)
            mapped.append({
                "citation_id": row["citation_id"],
                "target_id": row["target_id"],
                "cited_title": row["cited_title"],
                "citing_title": row["citing_title"],
                "url": row["url"],
                "paper_homepage": row["paper_homepage"],
                "citing_citation_count": row["citing_citation_count"],
                "year": row["year"],
                "venue": row["venue"],
                "is_self_citation": bool(row["is_self_citation"]),
                "is_seminal": bool(row["is_seminal"]),
                "seminal_evidence": row["seminal_evidence"],
                "usage_classification": row["usage_classification"],
                "score": row["score"],
                "positive_comment": row["positive_comment"],
                "sentiment_evidence": row["sentiment_evidence"],
                "raw_contexts": json.loads(row["raw_contexts"]) if row.get("raw_contexts") else [],
                "contexts": json.loads(row["raw_contexts"]) if row.get("raw_contexts") else [],
                "authors": json.loads(row["authors"]) if row.get("authors") else [],
                "notable_authors": json.loads(row["notable_authors"]) if row.get("notable_authors") else [],
                "is_human_verified": bool(row["is_human_verified"]),
                "ai_score": row["ai_score"],
                "ai_usage_classification": row["ai_usage_classification"],
                "ai_positive_comment": row["ai_positive_comment"],
                "ai_sentiment_evidence": row["ai_sentiment_evidence"],
                "ai_is_seminal": bool(row["ai_is_seminal"]) if row["ai_is_seminal"] is not None else None,
                "ai_seminal_evidence": row["ai_seminal_evidence"],
                "research_domain": row.get("research_domain"),
            })
            
        return {"evaluation_criteria": eval_criteria, "records": mapped}

@app.delete("/api/citations/{citation_id}")
def delete_citation(citation_id: str, target_id: str = Query(...), user: dict = Depends(require_roles(["admin", "super_admin"]))):
    with get_db_connection() as conn:
        if not conn.execute("SELECT 1 FROM citations WHERE citation_id = ? AND target_id = ?", (citation_id, target_id)).fetchone():
            raise HTTPException(status_code=404, detail="Citation not found")
        conn.execute("DELETE FROM citations WHERE citation_id = ? AND target_id = ?", (citation_id, target_id))
    return {"success": True, "message": "Citation deleted"}

@app.get("/api/citations/domains")
def get_citation_domains(target_id: str = Query(...), user: dict | None = Depends(get_current_user)):
    """Return aggregated domain distribution for a target."""
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT research_domain, COUNT(*) as count FROM citations WHERE target_id = ? AND research_domain IS NOT NULL GROUP BY research_domain ORDER BY count DESC",
            (target_id,),
        ).fetchall()
        domains = {row["research_domain"]: row["count"] for row in rows}
        return {"domains": domains}


@app.put("/api/citations/{citation_id}")
def update_citation(citation_id: str, req: CitationUpdateRequest, target_id: str = Query(...), user: dict = Depends(require_roles(["admin", "editor", "super_admin"]))):
    with get_db_connection() as conn:
        if not conn.execute("SELECT 1 FROM citations WHERE citation_id = ? AND target_id = ?", (citation_id, target_id)).fetchone():
            raise HTTPException(status_code=404, detail="Citation not found")
            
        if req.revert_to_ai:
            conn.execute("""
                UPDATE citations SET
                    score = ai_score,
                    usage_classification = ai_usage_classification,
                    positive_comment = ai_positive_comment,
                    sentiment_evidence = ai_sentiment_evidence,
                    is_seminal = ai_is_seminal,
                    seminal_evidence = ai_seminal_evidence,
                    is_human_verified = 0
                WHERE citation_id = ? AND target_id = ?
            """, (citation_id, target_id))
        else:
            conn.execute("""
                UPDATE citations SET
                    score = COALESCE(?, score),
                    usage_classification = COALESCE(?, usage_classification),
                    positive_comment = COALESCE(?, positive_comment),
                    sentiment_evidence = COALESCE(?, sentiment_evidence),
                    is_seminal = COALESCE(?, is_seminal),
                    seminal_evidence = COALESCE(?, seminal_evidence),
                    paper_homepage = COALESCE(?, paper_homepage),
                    notable_authors = COALESCE(?, notable_authors),
                    citing_title = COALESCE(?, citing_title),
                    year = COALESCE(?, year),
                    venue = COALESCE(?, venue),
                    authors = COALESCE(?, authors),
                    is_human_verified = 1
                WHERE citation_id = ? AND target_id = ?
            """, (
                req.score, req.usage_classification, req.positive_comment, req.sentiment_evidence,
                1 if req.is_seminal else (0 if req.is_seminal is False else None),
                req.seminal_evidence, req.paper_homepage,
                json.dumps(req.notable_authors) if req.notable_authors is not None else None,
                req.citing_title, req.year, req.venue,
                json.dumps(req.authors) if req.authors is not None else None,
                citation_id, target_id
            ))
    return {"success": True, "message": "Citation updated"}

# --- Authors & Verify API ---

@app.delete("/api/authors/{name}")
def delete_author(name: str, user: dict = Depends(require_roles(["admin", "super_admin"]))):
    with get_db_connection() as conn:
        if not conn.execute("SELECT 1 FROM authors WHERE name = ?", (name,)).fetchone():
            raise HTTPException(status_code=404, detail="Author not found")
        conn.execute("DELETE FROM authors WHERE name = ?", (name,))
    return {"success": True, "message": "Author deleted"}

@app.post("/api/verify")
def verify_author(req: VerifyRequest, user: dict = Depends(require_roles(["editor", "admin", "super_admin"]))):
    if not req.new_evidence and req.new_homepage is None:
        raise HTTPException(status_code=400, detail="Missing update fields")
        
    final_evidence = req.new_evidence or ""
    if final_evidence and "[AI Verified]" not in final_evidence and "[User Verified]" not in final_evidence:
        final_evidence = f"{final_evidence.strip()} [User Verified]"
        
    updated = False
    with get_db_connection() as conn:
        if final_evidence and req.new_homepage is not None:
            cur = conn.execute(
                "UPDATE authors SET is_notable = 1, evidence = ?, homepage = ?, is_human_verified = 1 WHERE name = ?",
                (final_evidence, req.new_homepage or None, req.author_name)
            )
            if cur.rowcount > 0: updated = True
        elif final_evidence:
            cur = conn.execute(
                "UPDATE authors SET is_notable = 1, evidence = ?, is_human_verified = 1 WHERE name = ?",
                (final_evidence, req.author_name)
            )
            if cur.rowcount > 0: updated = True
        elif req.new_homepage is not None:
            cur = conn.execute(
                "UPDATE authors SET homepage = ?, is_human_verified = 1 WHERE name = ?",
                (req.new_homepage or None, req.author_name)
            )
            if cur.rowcount > 0: updated = True

        rows = conn.execute("SELECT citation_id, target_id, notable_authors FROM citations WHERE notable_authors LIKE ?", (f"%{req.author_name}%",)).fetchall()
        for row in rows:
            if row["notable_authors"]:
                authors = json.loads(row["notable_authors"])
                changed = False
                for a in authors:
                    if a.get("name") == req.author_name:
                        if final_evidence:
                            a["evidence"] = final_evidence
                            changed = True
                        if req.new_homepage is not None:
                            a["homepage"] = req.new_homepage or None
                            changed = True
                if changed:
                    conn.execute("UPDATE citations SET notable_authors = ? WHERE citation_id = ? AND target_id = ?", (json.dumps(authors), row["citation_id"], row["target_id"]))
                    updated = True

    if updated:
        return {"success": True, "evidence": final_evidence}
    raise HTTPException(status_code=404, detail="Author not found in database")

# --- Admin Groups API ---

@app.get("/api/admin/groups")
def get_groups(user: dict = Depends(require_roles(["super_admin"]))):
    return {"groups": db_admin.list_groups()}

@app.post("/api/admin/groups")
def create_group(req: GroupRequest, user: dict = Depends(require_roles(["super_admin"]))):
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="Valid group name is required.")
    try:
        gid = db_admin.create_group(req.name, req.is_public or False)
        return {"success": True, "groupId": gid}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Group name already exists.")

@app.put("/api/admin/groups/{group_id}")
def update_group(group_id: int, req: GroupRequest, user: dict = Depends(require_roles(["super_admin"]))):
    if req.is_public is None:
        raise HTTPException(status_code=400, detail="Valid is_public boolean is required.")
    db_admin.update_group_visibility(group_id, req.is_public)
    return {"success": True}

@app.delete("/api/admin/groups/{group_id}")
def delete_group(group_id: int, user: dict = Depends(require_roles(["super_admin"]))):
    try:
        db_admin.delete_group(group_id)
        return {"success": True, "message": "Group deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/admin/groups/{group_id}/users")
def add_user_to_group(group_id: int, req: GroupUserRequest, user: dict = Depends(require_roles(["super_admin"]))):
    try:
        db_admin.add_user_to_group(group_id, req.userId)
        return {"success": True}
    except sqlite3.IntegrityError as e:
        emsg = str(e).lower()
        if "unique" in emsg or "primary key" in emsg:
            raise HTTPException(status_code=409, detail="User is already in this group.")
        raise HTTPException(status_code=404, detail="Invalid user or group ID.")

@app.delete("/api/admin/groups/{group_id}/users/{user_id}")
def remove_user_from_group(group_id: int, user_id: int, user: dict = Depends(require_roles(["super_admin"]))):
    db_admin.remove_user_from_group(group_id, user_id)
    return {"success": True}

# --- Admin Users & Logs API ---

@app.get("/api/admin/users")
def get_admin_users(user: dict = Depends(require_roles(["admin", "super_admin"]))):
    return {"users": db_auth.list_users()}

@app.put("/api/admin/users")
def update_user_role(req: UserRoleRequest, user: dict = Depends(require_roles(["admin", "super_admin"]))):
    if req.role not in ['viewer', 'editor', 'admin', 'super_admin']:
        raise HTTPException(status_code=400, detail="Invalid role.")
    if req.userId == user["id"]:
        raise HTTPException(status_code=400, detail="You cannot change your own role.")
    db_auth.update_user_role(req.userId, req.role)
    return {"success": True}

@app.get("/api/admin/llm-logs")
def get_llm_logs(limit: int = 100, offset: int = 0, fallback_only: bool = False, user: dict = Depends(require_roles(["admin", "super_admin"]))):
    with get_db_connection() as conn:
        if not conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='llm_logs'").fetchone():
            return {"logs": [], "total": 0}
            
        q = "SELECT * FROM llm_logs WHERE 1=1"
        cq = "SELECT COUNT(*) as count FROM llm_logs WHERE 1=1"
        p = []
        if fallback_only:
            q += " AND is_fallback = 1"
            cq += " AND is_fallback = 1"
            
        q += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        rows = conn.execute(q, p + [limit, offset]).fetchall()
        total = conn.execute(cq, p).fetchone()["count"]
        return {"logs": [dict(r) for r in rows], "total": total}

# --- Auth API (DB Layer only, cookies handled by Next.js) ---

@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = db_auth.verify_credentials(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token, expires_at = db_auth.create_session(user["id"])
    return {
        "message": "Logged in successfully",
        "user": {"username": user["username"], "role": user["role"]},
        "token": token,
        "expires_at": expires_at
    }

@app.post("/api/auth/register")
def register(req: RegisterRequest):
    if len(req.username) < 3 or len(req.password) < 5:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters and password at least 5 characters.")
    try:
        user = db_auth.create_user(req.username, req.password, role="editor")
        token, expires_at = db_auth.create_session(user["id"])
        return {
            "success": True,
            "user": user,
            "token": token,
            "expires_at": expires_at
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username already exists.")

@app.post("/api/auth/logout")
def logout(request: Request):
    """Expects token in Authorization header if calling from proxy."""
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ")[1]
        db_auth.delete_session(token)
    return {"message": "Logged out successfully"}

@app.get("/api/auth/me")
def me(request: Request):
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ")[1]
        user = db_auth.get_user_by_session(token)
        if user:
            return {"user": user}
    return {"user": None}

@app.put("/api/auth/users")
def update_my_password(req: PasswordUpdateRequest, user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if len(req.newPassword) < 5:
        raise HTTPException(status_code=400, detail="Password must be at least 5 characters long.")
    db_auth.update_user_password(user["id"], req.newPassword)
    return {"success": True}

@app.delete("/api/auth/users")
def delete_me(user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    db_auth.delete_user(user["id"])
    return {"success": True}

# --- Fallback Runs API (Filesystem) ---

@app.get("/api/fallback-runs/pending")
def get_pending_runs(user: dict = Depends(require_roles(["admin", "super_admin"]))):
    runs_dir = Path(os.environ.get("LLM_CALLS_DIR", Path(__file__).parent.parent.parent / "llm_calls"))
    if not runs_dir.exists():
        return {"pendingRun": None}
        
    run_folders = sorted([f for f in runs_dir.iterdir() if f.is_dir() and f.name.startswith("run_")], reverse=True)
    
    for folder in run_folders:
        files = [f.name for f in folder.iterdir() if f.is_file()]
        prompt_files = sorted([f for f in files if "_prompt_" in f and f.endswith(".txt")], reverse=True)
        
        for pfile in prompt_files:
            base_name = pfile.replace("_prompt_", "_response_").replace(".txt", "")
            if f"{base_name}.json" not in files and f"{base_name}.md" not in files:
                prompt_path = folder / pfile
                with open(prompt_path, "r", encoding="utf-8") as f:
                    content = f.read()
                expected_ext = ".json" if "json" in content.lower() else ".md"
                return {
                    "pendingRun": {
                        "runFolder": folder.name,
                        "promptFile": pfile,
                        "responseFile": f"{base_name}{expected_ext}",
                        "promptContent": content
                    }
                }
    return {"pendingRun": None}

@app.post("/api/fallback-runs/submit")
def submit_fallback_run(req: FallbackSubmitRequest, user: dict = Depends(require_roles(["super_admin"]))):
    runs_dir = Path(os.environ.get("LLM_CALLS_DIR", Path(__file__).parent.parent.parent / "llm_calls"))
    
    safe_run_folder = Path(req.runFolder).name
    safe_response_file = Path(req.responseFile).name
    
    if not safe_response_file.endswith(".json") and not safe_response_file.endswith(".md"):
        raise HTTPException(status_code=400, detail="Invalid response file extension.")
        
    folder_path = runs_dir / safe_run_folder
    if not folder_path.is_dir():
        raise HTTPException(status_code=404, detail="Run folder not found")
        
    file_path = folder_path / safe_response_file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(req.responseContent)
        
    return {"success": True, "message": "Fallback response saved successfully. Pipeline resumed."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["backend"],
    )

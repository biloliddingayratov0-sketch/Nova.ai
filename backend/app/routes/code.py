import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.code import CodeProject
from app.models.user import User
from app.models.billing import CreditTransaction
from app.services.code_service import (
    build_full_project,
    debug_code,
    execute_sandboxed_code,
    generate_code_solution,
    review_code,
)

router = APIRouter(prefix="/api/code", tags=["AI Code Assistant"])


class CodeGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=2)
    language: str = "python"
    framework: Optional[str] = None


class CodeDebugRequest(BaseModel):
    code: str = Field(..., min_length=1)
    error_message: str = Field(..., min_length=1)
    language: str = "python"


class CodeReviewRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: str = "python"


class ProjectBuilderRequest(BaseModel):
    description: str = Field(..., min_length=5)
    tech_stack: str = Field(default="FastAPI + React + PostgreSQL")


class ExecuteCodeRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: str = "python"


class SaveProjectRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""
    language: str = "python"
    code: str = ""
    project_structure: Optional[str] = ""
    files: Optional[List[dict]] = None


@router.post("/generate")
def api_generate_code(
    req: CodeGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.credits < 1:
        raise HTTPException(status_code=402, detail="Insufficient credits for code generation.")

    result = generate_code_solution(req.prompt, req.language, req.framework)
    user.credits -= 1
    db.add(CreditTransaction(
        user_id=user.id,
        amount=-1,
        balance_after=user.credits,
        service="code",
        description=f"Generated {req.language} code solution",
    ))
    db.commit()
    result["remaining_credits"] = user.credits
    return result


@router.post("/debug")
def api_debug_code(
    req: CodeDebugRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.credits < 1:
        raise HTTPException(status_code=402, detail="Insufficient credits for code debugging.")

    result = debug_code(req.code, req.error_message, req.language)
    user.credits -= 1
    db.add(CreditTransaction(
        user_id=user.id,
        amount=-1,
        balance_after=user.credits,
        service="code",
        description=f"Debugged {req.language} code",
    ))
    db.commit()
    result["remaining_credits"] = user.credits
    return result


@router.post("/review")
def api_review_code(
    req: CodeReviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.credits < 1:
        raise HTTPException(status_code=402, detail="Insufficient credits for code review.")

    result = review_code(req.code, req.language)
    user.credits -= 1
    db.add(CreditTransaction(
        user_id=user.id,
        amount=-1,
        balance_after=user.credits,
        service="code",
        description=f"Reviewed {req.language} code",
    ))
    db.commit()
    result["remaining_credits"] = user.credits
    return result


@router.post("/build-project")
def api_build_project(
    req: ProjectBuilderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.credits < 3:
        raise HTTPException(status_code=402, detail="Building a complete project requires 3 credits.")

    result = build_full_project(req.description, req.tech_stack)
    user.credits -= 3
    db.add(CreditTransaction(
        user_id=user.id,
        amount=-3,
        balance_after=user.credits,
        service="code",
        description=f"Built project blueprint: {req.description[:30]}...",
    ))
    db.commit()
    result["remaining_credits"] = user.credits
    return result


@router.post("/execute")
def api_execute_code(
    req: ExecuteCodeRequest,
    user: User = Depends(get_current_user),
):
    # Safe isolated execution
    return execute_sandboxed_code(req.code, req.language)


@router.post("/projects")
def save_code_project(
    req: SaveProjectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    proj = CodeProject(
        user_id=user.id,
        title=req.title,
        description=req.description or "",
        language=req.language,
        code=req.code,
        project_structure=req.project_structure or "",
        files_json=json.dumps(req.files or []),
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return {
        "id": proj.id,
        "title": proj.title,
        "language": proj.language,
        "created_at": proj.created_at,
    }


@router.get("/projects")
def list_code_projects(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    projects = db.query(CodeProject).filter(
        CodeProject.user_id == user.id
    ).order_by(CodeProject.updated_at.desc()).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "language": p.language,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
        for p in projects
    ]


@router.get("/projects/{project_id}")
def get_code_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.query(CodeProject).filter(
        CodeProject.id == project_id, CodeProject.user_id == user.id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "language": p.language,
        "code": p.code,
        "project_structure": p.project_structure,
        "files": json.loads(p.files_json or "[]"),
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


@router.delete("/projects/{project_id}")
def delete_code_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    p = db.query(CodeProject).filter(
        CodeProject.id == project_id, CodeProject.user_id == user.id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(p)
    db.commit()
    return {"success": True, "message": "Code project deleted"}


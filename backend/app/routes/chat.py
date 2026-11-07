import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.chat import ChatMessage, Conversation
from app.models.user import User
from app.models.billing import CreditTransaction
from app.services.chat_service import generate_chat_response, stream_chat_response

router = APIRouter(prefix="/api/chat", tags=["AI Chat"])


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"
    model: Optional[str] = "gpt-4o-mini"


class RenameConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)
    model: Optional[str] = "gpt-4o-mini"
    attachments: Optional[List[dict]] = None


@router.post("/conversations")
def create_conversation(
    req: CreateConversationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = Conversation(
        user_id=user.id,
        title=req.title or "New Conversation",
        model=req.model or "gpt-4o-mini",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {
        "id": conv.id,
        "title": conv.title,
        "model": conv.model,
        "created_at": conv.created_at,
    }


@router.get("/conversations")
def list_conversations(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Conversation).filter(Conversation.user_id == user.id)
    if search:
        q = q.filter(Conversation.title.ilike(f"%{search}%"))
    conversations = q.order_by(Conversation.updated_at.desc()).all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "model": c.model,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "message_count": len(c.messages),
        }
        for c in conversations
    ]


@router.get("/conversations/{conv_id}")
def get_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id, Conversation.user_id == user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "id": conv.id,
        "title": conv.title,
        "model": conv.model,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "attachments": json.loads(m.attachments_json or "[]"),
                "created_at": m.created_at,
            }
            for m in conv.messages
        ],
    }


@router.patch("/conversations/{conv_id}")
def rename_conversation(
    conv_id: int,
    req: RenameConversationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id, Conversation.user_id == user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.title = req.title.strip()
    db.commit()
    return {"id": conv.id, "title": conv.title}


@router.delete("/conversations/{conv_id}")
def delete_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id, Conversation.user_id == user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return {"success": True, "message": "Conversation deleted"}


@router.post("/conversations/{conv_id}/messages")
def send_message(
    conv_id: int,
    req: SendMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id, Conversation.user_id == user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if user.credits < 1:
        raise HTTPException(status_code=402, detail="Out of AI credits. Upgrade your subscription to continue chatting.")

    # 1. Save user message
    user_msg = ChatMessage(
        conversation_id=conv.id,
        user_id=user.id,
        role="user",
        content=req.content,
        attachments_json=json.dumps(req.attachments or []),
    )
    db.add(user_msg)
    
    # Auto-generate title from first message if default
    if conv.title in ("New Conversation", "Untitled") and len(conv.messages) == 0:
        conv.title = req.content[:35] + ("..." if len(req.content) > 35 else "")

    # 2. Gather history
    history = [
        {"role": m.role, "content": m.content}
        for m in conv.messages
    ]
    history.append({"role": "user", "content": req.content})

    # 3. Generate response
    ai_content = generate_chat_response(history, req.model or conv.model)

    # 4. Save assistant message
    ai_msg = ChatMessage(
        conversation_id=conv.id,
        user_id=user.id,
        role="assistant",
        content=ai_content,
        attachments_json="[]",
    )
    db.add(ai_msg)

    # 5. Deduct credit (1 credit per chat turn)
    user.credits -= 1
    db.add(CreditTransaction(
        user_id=user.id,
        amount=-1,
        balance_after=user.credits,
        service="chat",
        description=f"AI Chat query in conversation {conv.id}",
    ))
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ai_msg)

    return {
        "user_message": {
            "id": user_msg.id,
            "role": user_msg.role,
            "content": user_msg.content,
            "created_at": user_msg.created_at,
        },
        "assistant_message": {
            "id": ai_msg.id,
            "role": ai_msg.role,
            "content": ai_msg.content,
            "created_at": ai_msg.created_at,
        },
        "remaining_credits": user.credits,
    }


@router.get("/conversations/{conv_id}/export")
def export_conversation(
    conv_id: int,
    format: str = Query("markdown", pattern="^(markdown|json|text)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id, Conversation.user_id == user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if format == "json":
        data = {
            "title": conv.title,
            "created_at": str(conv.created_at),
            "messages": [{"role": m.role, "content": m.content, "timestamp": str(m.created_at)} for m in conv.messages],
        }
        return data

    # Markdown format
    lines = [f"# {conv.title}\n", f"*Exported on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*\n", "---\n"]
    for m in conv.messages:
        role_label = "**User**" if m.role == "user" else "**NOVA AI**"
        lines.append(f"### {role_label} ({m.created_at.strftime('%H:%M:%S')}):\n")
        lines.append(f"{m.content}\n\n")
    
    return {"content": "".join(lines), "filename": f"{conv.title.replace(' ', '_')}.md"}

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ...store.database import ModelRecord, get_session
from ..schemas import ModelCreate, ModelOut

router = APIRouter(prefix="/models", tags=["models"])


@router.post("/", response_model=ModelOut)
def register_model(payload: ModelCreate, session: Session = Depends(get_session)):
    existing = session.exec(
        select(ModelRecord).where(ModelRecord.model_id == payload.model_id)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Model '{payload.model_id}' already exists")

    record = ModelRecord(model_id=payload.model_id, description=payload.description)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@router.get("/", response_model=list[ModelOut])
def list_models(session: Session = Depends(get_session)):
    return session.exec(select(ModelRecord)).all()


@router.get("/{model_id}", response_model=ModelOut)
def get_model(model_id: str, session: Session = Depends(get_session)):
    record = session.exec(
        select(ModelRecord).where(ModelRecord.model_id == model_id)
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return record


@router.delete("/{model_id}")
def delete_model(model_id: str, session: Session = Depends(get_session)):
    record = session.exec(
        select(ModelRecord).where(ModelRecord.model_id == model_id)
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    session.delete(record)
    session.commit()
    return {"deleted": model_id}
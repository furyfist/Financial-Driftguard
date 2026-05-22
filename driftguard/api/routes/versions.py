from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ...store.database import ModelRecord, ModelVersion, get_session
from ..schemas import ModelVersionCreate, ModelVersionOut

router = APIRouter(prefix="/models", tags=["versions"])


@router.post("/{model_id}/versions", response_model=ModelVersionOut)
def create_version(
    model_id: str,
    payload: ModelVersionCreate,
    session: Session = Depends(get_session),
):
    model = session.exec(
        select(ModelRecord).where(ModelRecord.model_id == model_id)
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    duplicate = session.exec(
        select(ModelVersion).where(
            ModelVersion.model_id == model_id,
            ModelVersion.version_label == payload.version_label,
        )
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail=f"Version '{payload.version_label}' already exists for model '{model_id}'",
        )

    version = ModelVersion(
        model_id=model_id,
        version_label=payload.version_label,
        description=payload.description,
        is_active=False,
    )
    session.add(version)
    session.commit()
    session.refresh(version)
    return version


@router.get("/{model_id}/versions", response_model=list[ModelVersionOut])
def list_versions(
    model_id: str,
    session: Session = Depends(get_session),
):
    model = session.exec(
        select(ModelRecord).where(ModelRecord.model_id == model_id)
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    versions = session.exec(
        select(ModelVersion)
        .where(ModelVersion.model_id == model_id)
        .order_by(ModelVersion.created_at)
    ).all()
    return versions


@router.post("/{model_id}/versions/{version_label}/promote", response_model=ModelVersionOut)
def promote_version(
    model_id: str,
    version_label: str,
    session: Session = Depends(get_session),
):
    model = session.exec(
        select(ModelRecord).where(ModelRecord.model_id == model_id)
    ).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    target = session.exec(
        select(ModelVersion).where(
            ModelVersion.model_id == model_id,
            ModelVersion.version_label == version_label,
        )
    ).first()
    if not target:
        raise HTTPException(
            status_code=404,
            detail=f"Version '{version_label}' not found for model '{model_id}'",
        )

    # Demote current champion
    current_active = session.exec(
        select(ModelVersion).where(
            ModelVersion.model_id == model_id,
            ModelVersion.is_active == True,  # noqa: E712
        )
    ).first()
    if current_active and current_active.id != target.id:
        current_active.is_active = False
        current_active.demoted_at = datetime.now(timezone.utc)
        session.add(current_active)

    target.is_active = True
    target.promoted_at = datetime.now(timezone.utc)
    target.demoted_at = None
    session.add(target)
    session.commit()
    session.refresh(target)
    return target

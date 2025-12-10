"""
Collection CRUD API endpoints
Based on exact DB schema: id, user_id, name, description, metadata, config, created_at, updated_at
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from uuid import UUID

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.collection import Collection
from backend.models.document import Document
from backend.schemas.collection import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionListResponse
)
from backend.core.exceptions import http_404_not_found, http_400_bad_request

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    collection: CollectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new collection

    **Unique constraint**: (user_id, name) must be unique

    Args:
        collection: Collection data (name, description, metadata, config)
        db: Database session
        current_user: Authenticated user

    Returns:
        CollectionResponse: Created collection

    Raises:
        HTTPException: 400 if collection name already exists for user
    """
    # Check for duplicate name (using exact column names: user_id, name)
    existing = db.query(Collection).filter(
        Collection.user_id == current_user.id,
        Collection.name == collection.name
    ).first()

    if existing:
        raise http_400_bad_request(f"Collection '{collection.name}' already exists")

    # Create collection (using exact column names)
    db_collection = Collection(
        user_id=current_user.id,
        name=collection.name,
        description=collection.description,
        metadata_=collection.metadata or {},
        config=collection.config or {}
    )

    db.add(db_collection)
    db.commit()
    db.refresh(db_collection)

    # Get document count (using relationship name: documents)
    document_count = db.query(func.count(Document.id)).filter(
        Document.collection_id == db_collection.id
    ).scalar()

    # Build response (using exact column names)
    response = CollectionResponse(
        id=db_collection.id,
        user_id=db_collection.user_id,
        name=db_collection.name,
        description=db_collection.description,
        metadata=db_collection.metadata_,
        config=db_collection.config,
        document_count=document_count,
        created_at=db_collection.created_at,
        updated_at=db_collection.updated_at
    )

    return response


@router.get("", response_model=CollectionListResponse)
async def list_collections(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all collections for current user

    Args:
        limit: Max number of collections to return (default: 20, max: 100)
        offset: Number of collections to skip (for pagination)
        db: Database session
        current_user: Authenticated user

    Returns:
        CollectionListResponse: Paginated list of collections
    """
    # Enforce max limit
    limit = min(limit, 100)

    # Get total count (using exact column name: user_id)
    total = db.query(func.count(Collection.id)).filter(
        Collection.user_id == current_user.id
    ).scalar()

    # Get collections (using exact column name: user_id)
    collections = db.query(Collection).filter(
        Collection.user_id == current_user.id
    ).offset(offset).limit(limit).all()

    # Build responses with document counts
    collection_responses = []
    for col in collections:
        doc_count = db.query(func.count(Document.id)).filter(
            Document.collection_id == col.id
        ).scalar()

        collection_responses.append(CollectionResponse(
            id=col.id,
            user_id=col.user_id,
            name=col.name,
            description=col.description,
            metadata=col.metadata_,
            config=col.config,
            document_count=doc_count,
            created_at=col.created_at,
            updated_at=col.updated_at
        ))

    return CollectionListResponse(
        data=collection_responses,
        pagination={
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total
        }
    )


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get collection by ID

    Args:
        collection_id: Collection UUID
        db: Database session
        current_user: Authenticated user

    Returns:
        CollectionResponse: Collection details

    Raises:
        HTTPException: 404 if collection not found or not owned by user
    """
    # Get collection (using exact column names: id, user_id)
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()

    if not collection:
        raise http_404_not_found("Collection not found")

    # Get document count
    document_count = db.query(func.count(Document.id)).filter(
        Document.collection_id == collection.id
    ).scalar()

    return CollectionResponse(
        id=collection.id,
        user_id=collection.user_id,
        name=collection.name,
        description=collection.description,
        metadata=collection.metadata_,
        config=collection.config,
        document_count=document_count,
        created_at=collection.created_at,
        updated_at=collection.updated_at
    )


@router.patch("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: UUID,
    collection_update: CollectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update collection metadata

    Args:
        collection_id: Collection UUID
        collection_update: Fields to update (all optional)
        db: Database session
        current_user: Authenticated user

    Returns:
        CollectionResponse: Updated collection

    Raises:
        HTTPException: 404 if collection not found
        HTTPException: 400 if new name conflicts with existing collection
    """
    # Get collection (using exact column names: id, user_id)
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()

    if not collection:
        raise http_404_not_found("Collection not found")

    # Check for name conflict if name is being updated
    if collection_update.name and collection_update.name != collection.name:
        existing = db.query(Collection).filter(
            Collection.user_id == current_user.id,
            Collection.name == collection_update.name
        ).first()

        if existing:
            raise http_400_bad_request(f"Collection '{collection_update.name}' already exists")

    # Update fields (using exact column names: name, description, metadata, config)
    update_data = collection_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        # Map 'metadata' to 'metadata_' (SQLAlchemy reserves 'metadata')
        if field == 'metadata':
            setattr(collection, 'metadata_', value)
        else:
            setattr(collection, field, value)

    db.commit()
    db.refresh(collection)

    # Get document count
    document_count = db.query(func.count(Document.id)).filter(
        Document.collection_id == collection.id
    ).scalar()

    return CollectionResponse(
        id=collection.id,
        user_id=collection.user_id,
        name=collection.name,
        description=collection.description,
        metadata=collection.metadata_,
        config=collection.config,
        document_count=document_count,
        created_at=collection.created_at,
        updated_at=collection.updated_at
    )


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete collection and all its documents (cascade delete)

    Args:
        collection_id: Collection UUID
        db: Database session
        current_user: Authenticated user

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if collection not found
    """
    # Get collection (using exact column names: id, user_id)
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()

    if not collection:
        raise http_404_not_found("Collection not found")

    # Delete (cascade will delete all documents)
    db.delete(collection)
    db.commit()

    return None

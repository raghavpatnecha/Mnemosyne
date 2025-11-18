"""
Document CRUD API endpoints
Based on exact DB schema: id, collection_id, user_id, title, filename, content_type,
size_bytes, content_hash, unique_identifier_hash, status, metadata, processing_info,
created_at, updated_at
"""

from fastapi import APIRouter, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
import hashlib
import json

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.document import Document
from backend.models.collection import Collection
from backend.schemas.document import (
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
    DocumentStatusResponse
)
from backend.core.exceptions import http_404_not_found, http_400_bad_request
from backend.storage import storage_backend
from backend.tasks.process_document import process_document_task

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_document(
    collection_id: UUID = Form(..., description="Collection ID"),
    file: UploadFile = File(..., description="File to upload"),
    metadata: Optional[str] = Form("{}", description="JSON metadata"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload document (metadata only in Week 1, processing in Week 2)

    **Week 1**: Stores metadata, sets status="pending" (no processing)
    **Week 2**: Will add Celery task for processing

    Args:
        collection_id: Collection to add document to
        file: File to upload
        metadata: Optional JSON metadata
        db: Database session
        current_user: Authenticated user

    Returns:
        DocumentResponse: Created document with status="pending"

    Raises:
        HTTPException: 404 if collection not found
        HTTPException: 400 if duplicate content_hash or invalid metadata
    """
    # Verify collection ownership (using exact column names: id, user_id)
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()

    if not collection:
        raise http_404_not_found("Collection not found")

    # Read file content
    content = await file.read()

    # Calculate content hash (SHA-256) for deduplication
    content_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate (using exact column name: content_hash)
    existing = db.query(Document).filter(
        Document.content_hash == content_hash
    ).first()

    if existing:
        raise http_400_bad_request(
            f"Document with same content already exists (document_id: {existing.id})"
        )

    # Parse metadata JSON
    try:
        metadata_dict = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError:
        raise http_400_bad_request("Invalid JSON metadata")

    # Create document (using exact column names)
    document = Document(
        collection_id=collection_id,
        user_id=current_user.id,
        title=file.filename,
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=len(content),
        content_hash=content_hash,
        status="pending",
        metadata=metadata_dict,
        processing_info={}
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    # Save file to storage with user-scoped path
    file_path = storage_backend.save(
        file=content,
        user_id=current_user.id,
        collection_id=collection_id,
        document_id=document.id,
        filename=file.filename,
        content_type=file.content_type
    )

    # Update document with storage path
    document.processing_info = {"file_path": file_path}
    db.commit()
    db.refresh(document)

    # Trigger async processing (Week 2)
    process_document_task.delay(str(document.id))

    # Build response (using exact column names)
    return DocumentResponse(
        id=document.id,
        collection_id=document.collection_id,
        user_id=document.user_id,
        title=document.title,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        content_hash=document.content_hash,
        unique_identifier_hash=document.unique_identifier_hash,
        status=document.status,
        metadata=document.metadata_,
        processing_info=document.processing_info,
        created_at=document.created_at,
        updated_at=document.updated_at
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    collection_id: UUID,
    limit: int = 20,
    offset: int = 0,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List documents in a collection

    Args:
        collection_id: Collection UUID
        limit: Max number of documents to return (default: 20, max: 100)
        offset: Number of documents to skip (for pagination)
        status_filter: Filter by status (pending, processing, completed, failed)
        db: Database session
        current_user: Authenticated user

    Returns:
        DocumentListResponse: Paginated list of documents

    Raises:
        HTTPException: 404 if collection not found
    """
    # Verify collection ownership (using exact column names: id, user_id)
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.user_id == current_user.id
    ).first()

    if not collection:
        raise http_404_not_found("Collection not found")

    # Enforce max limit
    limit = min(limit, 100)

    # Build query (using exact column name: collection_id)
    query = db.query(Document).filter(Document.collection_id == collection_id)

    # Apply status filter if provided (using exact column name: status)
    if status_filter:
        query = query.filter(Document.status == status_filter)

    # Get total count
    total = query.count()

    # Get documents
    documents = query.offset(offset).limit(limit).all()

    # Build responses (using exact column names)
    document_responses = [
        DocumentResponse(
            id=doc.id,
            collection_id=doc.collection_id,
            user_id=doc.user_id,
            title=doc.title,
            filename=doc.filename,
            content_type=doc.content_type,
            size_bytes=doc.size_bytes,
            content_hash=doc.content_hash,
            unique_identifier_hash=doc.unique_identifier_hash,
            status=doc.status,
            metadata=doc.metadata_,
            processing_info=doc.processing_info,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        )
        for doc in documents
    ]

    return DocumentListResponse(
        data=document_responses,
        pagination={
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total
        }
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get document by ID

    Args:
        document_id: Document UUID
        db: Database session
        current_user: Authenticated user

    Returns:
        DocumentResponse: Document details

    Raises:
        HTTPException: 404 if document not found or not owned by user
    """
    # Get document (using exact column names: id, user_id)
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        raise http_404_not_found("Document not found")

    # Build response (using exact column names)
    return DocumentResponse(
        id=document.id,
        collection_id=document.collection_id,
        user_id=document.user_id,
        title=document.title,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        content_hash=document.content_hash,
        unique_identifier_hash=document.unique_identifier_hash,
        status=document.status,
        metadata=document.metadata_,
        processing_info=document.processing_info,
        created_at=document.created_at,
        updated_at=document.updated_at
    )


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    document_update: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update document metadata

    Args:
        document_id: Document UUID
        document_update: Fields to update (title, metadata)
        db: Database session
        current_user: Authenticated user

    Returns:
        DocumentResponse: Updated document

    Raises:
        HTTPException: 404 if document not found
    """
    # Get document (using exact column names: id, user_id)
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        raise http_404_not_found("Document not found")

    # Update fields (using exact column names: title, metadata)
    update_data = document_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(document, field, value)

    db.commit()
    db.refresh(document)

    # Build response (using exact column names)
    return DocumentResponse(
        id=document.id,
        collection_id=document.collection_id,
        user_id=document.user_id,
        title=document.title,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        content_hash=document.content_hash,
        unique_identifier_hash=document.unique_identifier_hash,
        status=document.status,
        metadata=document.metadata_,
        processing_info=document.processing_info,
        created_at=document.created_at,
        updated_at=document.updated_at
    )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get document processing status

    Args:
        document_id: Document UUID
        db: Database session
        current_user: Authenticated user

    Returns:
        DocumentStatusResponse: Processing status and details

    Raises:
        HTTPException: 404 if document not found
    """
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        raise http_404_not_found("Document not found")

    return DocumentStatusResponse(
        document_id=document.id,
        status=document.status,
        chunk_count=document.chunk_count or 0,
        total_tokens=document.total_tokens or 0,
        error_message=document.error_message,
        processing_info=document.processing_info or {},
        created_at=document.created_at,
        processed_at=document.processed_at
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete document

    Args:
        document_id: Document UUID
        db: Database session
        current_user: Authenticated user

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if document not found
    """
    # Get document (using exact column names: id, user_id)
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        raise http_404_not_found("Document not found")

    # Delete document and file
    if document.processing_info and "file_path" in document.processing_info:
        try:
            storage_backend.delete(
                storage_path=document.processing_info["file_path"],
                user_id=current_user.id
            )
        except Exception:
            pass

    db.delete(document)
    db.commit()

    return None


@router.get("/{document_id}/url", response_model=dict)
async def get_document_url(
    document_id: UUID,
    expires_in: int = 3600,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get access URL for document file (pre-signed URL for S3, file path for local)

    Args:
        document_id: Document UUID
        expires_in: URL expiration time in seconds (default: 3600 = 1 hour)
        db: Database session
        current_user: Authenticated user

    Returns:
        dict: {"url": "accessible-url", "expires_in": seconds}

    Raises:
        HTTPException: 404 if document not found
        HTTPException: 400 if file not found in storage
    """
    # Get document (verify ownership)
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        raise http_404_not_found("Document not found")

    # Get file path from processing_info
    if not document.processing_info or "file_path" not in document.processing_info:
        raise http_400_bad_request("Document file not found")

    file_path = document.processing_info["file_path"]

    # Generate accessible URL
    try:
        url = storage_backend.get_url(
            storage_path=file_path,
            user_id=current_user.id,
            expires_in=expires_in
        )

        return {
            "url": url,
            "expires_in": expires_in,
            "filename": document.filename,
            "content_type": document.content_type
        }
    except FileNotFoundError:
        raise http_404_not_found("Document file not found in storage")
    except PermissionError as e:
        raise http_400_bad_request(str(e))

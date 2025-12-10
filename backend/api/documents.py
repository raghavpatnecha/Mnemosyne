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
from backend.utils.content_type import detect_content_type
from backend.services.lightrag_service import get_lightrag_manager
from backend.processors import VALID_DOCUMENT_TYPES
from backend.config import settings
import logging

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_document(
    collection_id: UUID = Form(..., description="Collection ID"),
    file: UploadFile = File(..., description="File to upload"),
    metadata: Optional[str] = Form("{}", description="JSON metadata"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload document and trigger async processing

    Stores document metadata and file, then triggers Celery task for processing
    (chunking, embedding, indexing).

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

    # Enforce maximum file size (Issue #10 fix)
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise http_400_bad_request(
            f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.1f}MB, "
            f"got {len(content) / 1024 / 1024:.1f}MB"
        )

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

    # Parse and validate metadata JSON (Issue #5 fix)
    try:
        metadata_dict = json.loads(metadata) if metadata else {}

        # Validate that metadata is a dictionary, not array/string/number
        if not isinstance(metadata_dict, dict):
            raise http_400_bad_request(
                f"Metadata must be a JSON object/dict, got {type(metadata_dict).__name__}"
            )

        # Validate metadata size (prevent DoS)
        if len(json.dumps(metadata_dict)) > 10000:
            raise http_400_bad_request("Metadata too large (max 10KB)")

        # Validate metadata depth and value types
        def validate_metadata_values(obj, depth=0, max_depth=3):
            if depth > max_depth:
                raise ValueError("Metadata nesting too deep (max 3 levels)")

            if isinstance(obj, dict):
                for key, value in obj.items():
                    if not isinstance(key, str) or len(key) > 100:
                        raise ValueError(f"Invalid metadata key: {key}")
                    validate_metadata_values(value, depth + 1, max_depth)
            elif isinstance(obj, list):
                if len(obj) > 100:
                    raise ValueError("Metadata arrays limited to 100 items")
                for item in obj:
                    validate_metadata_values(item, depth + 1, max_depth)
            elif isinstance(obj, str):
                if len(obj) > 1000:
                    raise ValueError("Metadata string values limited to 1000 chars")
            elif not isinstance(obj, (int, float, bool, type(None))):
                raise ValueError(f"Invalid metadata value type: {type(obj).__name__}")

        validate_metadata_values(metadata_dict)

        # Validate document_type if provided (for domain processor selection)
        if "document_type" in metadata_dict:
            doc_type = metadata_dict["document_type"]
            if doc_type not in VALID_DOCUMENT_TYPES:
                raise http_400_bad_request(
                    f"Invalid document_type '{doc_type}'. "
                    f"Valid types: {', '.join(sorted(VALID_DOCUMENT_TYPES))}"
                )

    except json.JSONDecodeError:
        raise http_400_bad_request("Invalid JSON metadata")
    except ValueError as e:
        raise http_400_bad_request(f"Invalid metadata: {e}")

    # Detect content type using extension-first strategy (fixes application/octet-stream issue)
    detected_content_type = detect_content_type(
        filename=file.filename,
        content=content,
        client_content_type=file.content_type
    )
    logger.info(f"Detected content type for {file.filename}: {detected_content_type} (client sent: {file.content_type})")

    # Create document (using exact column names)
    document = Document(
        collection_id=collection_id,
        user_id=current_user.id,
        title=file.filename,
        filename=file.filename,
        content_type=detected_content_type,
        size_bytes=len(content),
        content_hash=content_hash,
        status="pending",
        metadata_=metadata_dict,  # Use metadata_ (SQLAlchemy reserves 'metadata')
        processing_info={}
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    file_path = None
    try:
        # Save file to storage with user-scoped path
        file_path = storage_backend.save(
            file=content,
            user_id=current_user.id,
            collection_id=collection_id,
            document_id=document.id,
            filename=file.filename,
            content_type=detected_content_type
        )

        # Update document with storage path
        document.processing_info = {"file_path": file_path}
        db.commit()
        db.refresh(document)

        # Trigger async processing - if this fails, we need to clean up
        process_document_task.delay(str(document.id))

    except Exception as e:
        logger.error(f"Failed to complete document upload for {document.id}: {e}")

        # Rollback database transaction
        db.rollback()

        # Clean up: delete file from storage if it was saved
        if file_path:
            try:
                storage_backend.delete(
                    storage_path=file_path,
                    user_id=current_user.id
                )
                logger.info(f"Cleaned up file: {file_path}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up file {file_path}: {cleanup_error}")

        # Delete document record from database
        try:
            db.delete(document)
            db.commit()
            logger.info(f"Deleted document record: {document.id}")
        except Exception as db_error:
            logger.error(f"Failed to delete document record: {db_error}")
            db.rollback()

        # Re-raise the original exception
        raise http_400_bad_request(
            f"Failed to process document upload: {str(e)}"
        )

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
        # Map 'metadata' to 'metadata_' (SQLAlchemy reserves 'metadata')
        if field == 'metadata':
            setattr(document, 'metadata_', value)
        else:
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

    # Delete from LightRAG if enabled (Issue #12 fix)
    if settings.LIGHTRAG_ENABLED:
        try:
            logger.info(f"Cleaning up LightRAG data for document {document_id}")
            lightrag_manager = get_lightrag_manager()
            # Note: LightRAG doesn't have document-level deletion API yet
            # This is a placeholder for when that functionality is added
            # For now, log the intent and continue with deletion
            logger.warning(
                f"LightRAG document deletion not yet implemented. "
                f"Document {document_id} data remains in graph."
            )
        except Exception as e:
            logger.error(f"LightRAG cleanup failed (non-critical): {e}")

    # Delete document file from storage
    if document.processing_info and "file_path" in document.processing_info:
        try:
            storage_backend.delete(
                storage_path=document.processing_info["file_path"],
                user_id=current_user.id
            )
        except Exception as e:
            logger.error(f"Failed to delete document file: {e}")

    # Delete document from database (cascades to chunks)
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

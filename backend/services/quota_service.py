"""
Quota Management Service

Tracks and enforces per-user quotas for documents, retrievals, and chat messages.
Prevents abuse and ensures fair resource allocation.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.models.user import User
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QuotaService:
    """
    Track and enforce user quotas

    Quotas (defined in User model):
    - quota_documents: Max documents per month
    - quota_retrievals: Max retrievals per month
    - usage_documents: Current document count
    - usage_retrievals: Current retrieval count

    Plan Limits:
    - Free: 1000 docs, 10000 retrievals
    - Pro: 10000 docs, 100000 retrievals
    - Enterprise: Custom limits
    """

    def __init__(self, db: Session):
        """Initialize quota service with database session"""
        self.db = db

    def check_quota(
        self,
        user_id: UUID,
        quota_type: str,
        amount: int = 1
    ) -> bool:
        """
        Check if user has quota available

        Args:
            user_id: User UUID
            quota_type: Type of quota ('documents', 'retrievals', 'chat')
            amount: Amount to check (default 1)

        Returns:
            True if quota available

        Raises:
            HTTPException 429 if quota exceeded
        """
        user = self._get_user(user_id)

        if quota_type == "documents":
            available = user.quota_documents - user.usage_documents
            if available < amount:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "quota_exceeded",
                        "message": f"Document quota exceeded. Limit: {user.quota_documents}, Used: {user.usage_documents}",
                        "quota_type": "documents",
                        "limit": user.quota_documents,
                        "used": user.usage_documents,
                        "available": available
                    }
                )

        elif quota_type == "retrievals":
            available = user.quota_retrievals - user.usage_retrievals
            if available < amount:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "quota_exceeded",
                        "message": f"Retrieval quota exceeded. Limit: {user.quota_retrievals}, Used: {user.usage_retrievals}",
                        "quota_type": "retrievals",
                        "limit": user.quota_retrievals,
                        "used": user.usage_retrievals,
                        "available": available
                    }
                )

        logger.debug(
            f"Quota check PASSED for user {user_id}: {quota_type} "
            f"(amount={amount})"
        )
        return True

    def increment_usage(
        self,
        user_id: UUID,
        quota_type: str,
        amount: int = 1
    ) -> bool:
        """
        Increment usage counter

        Args:
            user_id: User UUID
            quota_type: Type of quota
            amount: Amount to increment

        Returns:
            True if incremented successfully
        """
        user = self._get_user(user_id)

        if quota_type == "documents":
            user.usage_documents += amount
        elif quota_type == "retrievals":
            user.usage_retrievals += amount

        self.db.commit()

        logger.debug(
            f"Incremented {quota_type} usage for user {user_id} by {amount}"
        )
        return True

    def get_usage(self, user_id: UUID) -> dict:
        """
        Get current usage for user

        Returns:
            Dictionary with usage statistics
        """
        user = self._get_user(user_id)

        return {
            "documents": {
                "used": user.usage_documents,
                "limit": user.quota_documents,
                "available": user.quota_documents - user.usage_documents,
                "percentage": (user.usage_documents / user.quota_documents * 100) if user.quota_documents > 0 else 0
            },
            "retrievals": {
                "used": user.usage_retrievals,
                "limit": user.quota_retrievals,
                "available": user.quota_retrievals - user.usage_retrievals,
                "percentage": (user.usage_retrievals / user.quota_retrievals * 100) if user.quota_retrievals > 0 else 0
            }
        }

    def reset_usage(self, user_id: UUID, quota_type: Optional[str] = None) -> bool:
        """
        Reset usage counters (typically called monthly)

        Args:
            user_id: User UUID
            quota_type: Specific quota type or None for all

        Returns:
            True if reset successfully
        """
        user = self._get_user(user_id)

        if quota_type is None or quota_type == "documents":
            user.usage_documents = 0

        if quota_type is None or quota_type == "retrievals":
            user.usage_retrievals = 0

        self.db.commit()

        logger.info(
            f"Reset usage for user {user_id}: "
            f"{quota_type or 'all quotas'}"
        )
        return True

    def update_quota_limits(
        self,
        user_id: UUID,
        documents: Optional[int] = None,
        retrievals: Optional[int] = None
    ) -> bool:
        """
        Update quota limits (typically when user upgrades plan)

        Args:
            user_id: User UUID
            documents: New document limit
            retrievals: New retrieval limit

        Returns:
            True if updated successfully
        """
        user = self._get_user(user_id)

        if documents is not None:
            user.quota_documents = documents

        if retrievals is not None:
            user.quota_retrievals = retrievals

        self.db.commit()

        logger.info(
            f"Updated quota limits for user {user_id}: "
            f"docs={documents}, retrievals={retrievals}"
        )
        return True

    def check_and_increment(
        self,
        user_id: UUID,
        quota_type: str,
        amount: int = 1
    ) -> bool:
        """
        Check quota and increment usage atomically

        Args:
            user_id: User UUID
            quota_type: Type of quota
            amount: Amount to use

        Returns:
            True if quota available and incremented

        Raises:
            HTTPException 429 if quota exceeded
        """
        self.check_quota(user_id, quota_type, amount)
        return self.increment_usage(user_id, quota_type, amount)

    def is_quota_warning(
        self,
        user_id: UUID,
        quota_type: str,
        threshold: float = 0.8
    ) -> bool:
        """
        Check if user is approaching quota limit

        Args:
            user_id: User UUID
            quota_type: Type of quota
            threshold: Warning threshold (0-1, default 0.8 = 80%)

        Returns:
            True if usage >= threshold * limit
        """
        usage = self.get_usage(user_id)
        percentage = usage[quota_type]["percentage"]

        return percentage >= (threshold * 100)

    def _get_user(self, user_id: UUID) -> User:
        """Get user by ID"""
        user = self.db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        return user

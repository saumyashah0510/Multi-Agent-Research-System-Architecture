"""Audit Logging Service Layer for persisting and retrieving review execution events.

Assignee Task (Issue BE-17):
- Implement record_review_event(): persists a structured ReviewLog row into Neon DB.
- Implement get_review_audit_timeline(): fetches chronological logs for a review session.
- Implement record_execution_event(): persists global ExecutionLog rows.
"""

import inspect
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log import ExecutionLog, ReviewLog

logger = logging.getLogger(__name__)


class AuditService:
    """Service for managing persistent agent audit logs and system execution logs."""

    @staticmethod
    async def record_review_event(
        db: AsyncSession,
        review_id: int,
        agent_name: str,
        status: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[ReviewLog]:
        """Insert a new agent execution milestone record into Neon DB."""
        try:
            log_entry = ReviewLog(
                review_id=review_id,
                agent_name=agent_name,
                status=status,
                message=message,
                payload=payload or {},
            )
            db.add(log_entry)
            await db.commit()
            if hasattr(db, "refresh"):
                res = db.refresh(log_entry)
                if inspect.isawaitable(res):
                    await res
            if getattr(log_entry, "created_at", None) is None:
                log_entry.created_at = datetime.now(timezone.utc)
            return log_entry
        except Exception as exc:
            try:
                res = db.rollback()
                if inspect.isawaitable(res):
                    await res
            except Exception:
                pass
            logger.warning("Failed to record review log for review %s: %s", review_id, exc)
            return None

    @staticmethod
    async def get_review_audit_timeline(
        db: AsyncSession,
        review_id: int,
    ) -> List[ReviewLog]:
        """Fetch all audit logs for a review session in chronological order."""
        stmt = (
            select(ReviewLog)
            .where(ReviewLog.review_id == review_id)
            .order_by(ReviewLog.created_at.asc(), ReviewLog.id.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def record_execution_event(
        db: AsyncSession,
        agent_name: str,
        message: str,
    ) -> Optional[ExecutionLog]:
        """Insert a system-wide execution event into Neon DB."""
        try:
            log_entry = ExecutionLog(agent_name=agent_name, message=message)
            db.add(log_entry)
            await db.commit()
            if hasattr(db, "refresh"):
                res = db.refresh(log_entry)
                if inspect.isawaitable(res):
                    await res
            if getattr(log_entry, "timestamp", None) is None:
                log_entry.timestamp = datetime.now(timezone.utc)
            return log_entry
        except Exception as exc:
            try:
                res = db.rollback()
                if inspect.isawaitable(res):
                    await res
            except Exception:
                pass
            logger.warning("Failed to record system execution log: %s", exc)
            return None

    @staticmethod
    async def get_system_execution_logs(
        db: AsyncSession,
        limit: int = 50,
    ) -> List[ExecutionLog]:
        """Fetch recent system-wide execution diagnostic logs."""
        stmt = select(ExecutionLog).order_by(ExecutionLog.timestamp.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

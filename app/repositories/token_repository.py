import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_verification_token import EmailVerificationToken
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self) -> None:
        super().__init__(RefreshToken)

    async def get_by_token(self, db: AsyncSession, token: str) -> RefreshToken | None:
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        return result.scalar_one_or_none()

    async def revoke_token(self, db: AsyncSession, token: str) -> None:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token == token)
            .values(revoked=True)
        )

    async def revoke_all_for_user(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
            )
            .values(revoked=True)
        )


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    def __init__(self) -> None:
        super().__init__(PasswordResetToken)

    async def get_by_token(
        self, db: AsyncSession, token: str
    ) -> PasswordResetToken | None:
        result = await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token == token)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, db: AsyncSession, token: str) -> None:
        await db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.token == token)
            .values(used=True)
        )


class EmailVerificationTokenRepository(BaseRepository[EmailVerificationToken]):
    def __init__(self) -> None:
        super().__init__(EmailVerificationToken)

    async def get_by_token(
        self, db: AsyncSession, token: str
    ) -> EmailVerificationToken | None:
        result = await db.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token == token)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, db: AsyncSession, token: str) -> None:
        await db.execute(
            update(EmailVerificationToken)
            .where(EmailVerificationToken.token == token)
            .values(used=True)
        )


refresh_token_repository = RefreshTokenRepository()
password_reset_token_repository = PasswordResetTokenRepository()
email_verification_token_repository = EmailVerificationTokenRepository()

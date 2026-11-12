from __future__ import annotations

from contextlib import AsyncExitStack
from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.database.engine import database


class UnitOfWork:
    """Transaction boundary shared by vertical slices.

    A slice uses it as an async context manager and accesses the session
    through ``uow.session``. The transaction commits when the block exits
    successfully and rolls back when an exception propagates.
    """

    def __init__(self) -> None:
        self._exit_stack = AsyncExitStack()
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> UnitOfWork:
        """Open a session and start a transaction."""
        self._session = await self._exit_stack.enter_async_context(database.session())
        await self._session.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Commit or roll back the transaction and release the session."""
        session = self.session
        try:
            if exc_type is None:
                await session.commit()
            else:
                await session.rollback()
        finally:
            self._session = None
            await self._exit_stack.aclose()

    @property
    def session(self) -> AsyncSession:
        """Return the active session."""
        if self._session is None:
            raise RuntimeError("UnitOfWork is not active. Use it inside 'async with'.")
        return self._session

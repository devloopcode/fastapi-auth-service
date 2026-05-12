from fastapi import Query


class PaginationParams:
    """Reusable dependency for page / per_page query parameters."""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Page number (1-based)"),
        per_page: int = Query(
            default=20, ge=1, le=100, description="Number of items per page"
        ),
    ) -> None:
        self.page = page
        self.per_page = per_page
        self.offset = (page - 1) * per_page

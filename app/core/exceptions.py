from fastapi import status


class AppException(Exception):
    """Base exception for all application-level errors."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(f"{resource} not found.", status.HTTP_404_NOT_FOUND)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Not authenticated.") -> None:
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Permission denied.") -> None:
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class ConflictException(AppException):
    def __init__(self, message: str = "Resource already exists.") -> None:
        super().__init__(message, status.HTTP_409_CONFLICT)


class BadRequestException(AppException):
    def __init__(self, message: str = "Bad request.") -> None:
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class TokenExpiredException(UnauthorizedException):
    def __init__(self) -> None:
        super().__init__("Token has expired.")


class InvalidTokenException(UnauthorizedException):
    def __init__(self) -> None:
        super().__init__("Invalid or revoked token.")


class AccountNotVerifiedException(ForbiddenException):
    def __init__(self) -> None:
        super().__init__("Email address has not been verified.")


class AccountDisabledException(ForbiddenException):
    def __init__(self) -> None:
        super().__init__("This account has been disabled.")

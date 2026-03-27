from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class NotFoundError(HTTPException):
    def __init__(self, resource: str, id: str):
        super().__init__(status_code=404, detail=f"{resource} '{id}' not found.")


class BadRequestError(HTTPException):
    def __init__(self, message: str):
        super().__init__(status_code=400, detail=message)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
        })
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs for details."},
    )

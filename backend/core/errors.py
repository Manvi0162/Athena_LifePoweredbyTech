"""Turn database errors from her SQL functions into clear API errors."""

from fastapi import HTTPException
from postgrest.exceptions import APIError


def db_error(exc: APIError) -> HTTPException:
    message = exc.message or "Database error"
    if exc.code == "42501" or "Unauthorized household" in message:
        status, code = 403, "forbidden"
    elif "Recipe not accessible" in message:
        status, code = 404, "recipe_not_found"
    elif message.startswith("Insufficient ingredient") or "Operation ID already used" in message:
        status, code = 409, "conflict"
    elif exc.code == "22023" or message.startswith(("Invalid", "Recipe", "Ingredient", "Each")):
        status, code = 422, "invalid_input"
    else:
        status, code = 400, "database_error"
    return HTTPException(status_code=status, detail={"code": code, "message": message})

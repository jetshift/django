from rest_framework.exceptions import ValidationError


class BaseValidationError(ValidationError):
    def __init__(self, message, code=None):
        super().__init__({
            "success": False,
            "message": message,
            "data": {}
        })
        self.code = code

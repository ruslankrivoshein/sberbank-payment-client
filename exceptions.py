class SberbankAcquiringException(Exception):
    def __init__(self, message: str, code: int = None):
        self.message = message
        self.code = code


class ActionException(SberbankAcquiringException):
    pass


class BadRequestException(SberbankAcquiringException):
    pass


class BadResponseException(SberbankAcquiringException):
    pass


class NetworkException(SberbankAcquiringException):
    pass


class InvalidRequestArguments(SberbankAcquiringException):
    pass

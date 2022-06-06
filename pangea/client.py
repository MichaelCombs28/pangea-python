from pangea.services import Audit, Locate, Sanitize, Redact


class PangeaClient(object):
    def __init__(self, token=""):
        self.default_token = token

        self.__audit = None
        self.__redact = None
        self.__locate = None
        self.__sanitize = None

    @property
    def audit(self):
        if not self.__audit:
            self.__audit = Audit(token=self.default_token)
        return self.__audit

    @property
    def redact(self):
        if not self.__redact:
            self.__redact = Redact(token=self.default_token)
        return self.__redact

    @property
    def locate(self):
        if not self.__locate:
            self.__locate = Locate(token=self.default_token)
        return self.__locate

    @property
    def sanitize(self):
        if not self.__sanitize:
            self.__sanitize = Sanitize(token=self.default_token)
        return self.__sanitize

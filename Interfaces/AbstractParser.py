from abc import ABC, abstractmethod


class AParser(ABC):

    @abstractmethod
    def _make_url(self):
        pass

    @abstractmethod
    def start_console(self):
        pass

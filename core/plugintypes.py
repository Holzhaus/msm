import logging
from abc import ABCMeta, abstractmethod
from yapsy.IPlugin import IPlugin


class AbstractMSMPlugin(IPlugin):
    __metaclass__ = ABCMeta

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        super(self.__class__, self).__init__()

    def activate(self):
        if self.is_available():
            super(self.__class__, self).activate()

    def is_available(self):
        return True


class ContractExportFormatter(AbstractMSMPlugin):
    CATEGORY = "contract-export-format"
    FILE_EXT = "*"

    def __init__(self):
        super(AbstractMSMPlugin, self).__init__()

    @abstractmethod
    def write(self, contracts, output_file, encoding='utf-8'):
        pass

    def write_all(self, *args, **kwargs):
        for x in self.write(*args, **kwargs):
            pass


class BookingImporter(AbstractMSMPlugin):
    CATEGORY = "booking-importer"
    FILE_EXT = "*"

    def __init__(self):
        super(AbstractMSMPlugin, self).__init__()

    @abstractmethod
    def read(self, input_file):
        pass

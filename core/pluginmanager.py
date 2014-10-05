import os
import logging
import operator
import imp
from distutils.spawn import find_executable
import configparser

from core import plugintypes
from yapsy.PluginManager import PluginManager
from yapsy.PluginInfo import PluginInfo
from yapsy.FilteredPluginManager import FilteredPluginManager

# FIXME: These Two values should not be hardcoded
CURRENT_MSMVERSION = (1, 0, 0)
NETWORK_AVAILABLE = True


class MSMPluginInfo(PluginInfo):

    def __init__(self, plugin_name, plugin_path):
        self._logger = logging.getLogger(__name__)
        super(MSMPluginInfo, self).__init__(plugin_name, plugin_path)

    @property
    def slug(self):
        try:
            value = self.details.get('Documentation', 'Slug')
        except (configparser.NoSectionError, configparser.NoOptionError):
            # FIXME: We should probably use the slugify module here
            value = self.name.lower().replace(' ', '-')
        return value

    @property
    def priority(self):
        try:
            value = self.details.get('Documentation', 'Priority')
        except (configparser.NoSectionError, configparser.NoOptionError):
            value = 0
        return value

    @property
    def depends_msmversion(self):
        try:
            versionstr = self.details.get('Dependencies', 'MSMVersion')
        except (configparser.NoSectionError, configparser.NoOptionError):
            value = (2, 0, 0)
        else:
            value = tuple(int(n) for n in versionstr.split('.'))
        return value

    @property
    def depends_network(self):
        try:
            value = self.details.get('Dependencies', 'Network')
        except (configparser.NoSectionError, configparser.NoOptionError):
            value = False
        return value

    @property
    def depends_executables(self):
        try:
            csvlst = self.details.get('Dependencies', 'Binaries')
        except (configparser.NoSectionError, configparser.NoOptionError):
            value = []
        else:
            value = [item.strip() for item in csvlst.split(',')]
        return value

    @property
    def depends_modules(self):
        try:
            csvlst = self.details.get('Dependencies', 'Modules')
        except (configparser.NoSectionError, configparser.NoOptionError):
            value = []
        else:
            value = [item.strip() for item in csvlst.split(',')]
        return value

    @property
    def depends_plugins(self):
        try:
            csvlst = self.details.get('Dependencies', 'Plugins')
        except (configparser.NoSectionError, configparser.NoOptionError):
            value = []
        else:
            value = [item.strip() for item in csvlst.split(',')]
        return value

    @property
    def is_available(self):
        # Check MSMversion
        if self.depends_msmversion > CURRENT_MSMVERSION:
            needed_version_str = '.'.join(str(n) for n
                                          in self.depends_msmversion)
            current_version_str = '.'.join(str(n) for n
                                           in CURRENT_MSMVERSION)
            self._logger.info("Plugin '%s' rejected: " +
                              "Needs newer MSM version (%s > %s)",
                              self.name, needed_version_str,
                              current_version_str)
            return False

        # Check Network
        if self.depends_network and not NETWORK_AVAILABLE:
            self._logger.info("Plugin '%s' rejected: Needs network connection",
                              self.name)
            return False

        # Check executables
        for executable_name in self.depends_executables:
            if not find_executable(executable_name):
                self._logger.info("Plugin '%s' rejected: " +
                                  "Needs executable '%s'",
                                  self.name, executable_name)
                return False

        # Check modules
        for module_name in self.depends_modules:
            try:
                imp.find_module(module_name)
            except ImportError:
                self._logger.info("Plugin '%s' rejected: Needs module '%s'",
                                  self.name, module_name)
                return False

        # Everything worked, this module is available
        return True


class MSMPluginManager(PluginManager):
    PLUGIN_INFO_EXT = 'msmplugin'
    PLUGIN_DIRS = [os.path.join(os.path.dirname(__file__),
                                os.pardir,
                                "plugins")]
    PLUGIN_CATS = {plugintypes.ContractExportFormatter.CATEGORY:
                   plugintypes.ContractExportFormatter,
                   plugintypes.DirectDebitExportFormatter.CATEGORY:
                   plugintypes.DirectDebitExportFormatter,
                   plugintypes.BookingImporter.CATEGORY:
                   plugintypes.BookingImporter}

    def __init__(self):
        super(MSMPluginManager, self).__init__(
            categories_filter=self.PLUGIN_CATS,
            directories_list=self.PLUGIN_DIRS,
            plugin_info_ext=self.PLUGIN_INFO_EXT)
        locator = self.getPluginLocator()
        locator.setPluginInfoClass(MSMPluginInfo)

    def getPluginBySlug(self, slug, category="Default"):
        """
        Get the plugin correspoding to a given category and slug
        """
        for item in self.getPluginsOfCategory(category):
            if item.slug == slug:
                return item
        return None

    def getPluginsOfCategory(self, category_name):
        available_plugins = super(MSMPluginManager, self).getPluginsOfCategory(
            category_name)
        # sort on secondary key
        available_plugins.sort(key=operator.attrgetter('slug'))
        # now sort on primary key, descending
        available_plugins.sort(key=operator.attrgetter('priority'), reverse=True)
        return available_plugins


class MSMFilteredPluginManager(FilteredPluginManager):
    def isPluginOk(self, info):
        return info.is_available

# Singleton
PluginManagerSingleton = MSMFilteredPluginManager(MSMPluginManager())
PluginManagerSingleton.collectPlugins()

if __name__ == "__main__":
    for plugin in PluginManagerSingleton.getAllPlugins():
        print(plugin.name)
        print("  (%s)" % plugin.description)

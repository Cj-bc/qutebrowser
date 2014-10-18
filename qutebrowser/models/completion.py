# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2014 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""CompletionModels for different usages."""

from PyQt5.QtCore import Qt

from qutebrowser.config import config, configdata
from qutebrowser.models import basecompletion
from qutebrowser.utils import log, qtutils, objreg
from qutebrowser.commands import cmdutils
from qutebrowser.browser import quickmarks


class SettingSectionCompletionModel(basecompletion.BaseCompletionModel):

    """A CompletionModel filled with settings sections."""

    # pylint: disable=abstract-method

    def __init__(self, parent=None):
        super().__init__(parent)
        cat = self.new_category("Sections")
        for name in configdata.DATA.keys():
            desc = configdata.SECTION_DESC[name].splitlines()[0].strip()
            self.new_item(cat, name, desc)


class SettingOptionCompletionModel(basecompletion.BaseCompletionModel):

    """A CompletionModel filled with settings and their descriptions.

    Attributes:
        _misc_items: A dict of the misc. column items which will be set later.
    """

    # pylint: disable=abstract-method

    def __init__(self, section, parent=None):
        super().__init__(parent)
        cat = self.new_category(section)
        sectdata = configdata.DATA[section]
        self._misc_items = {}
        config.on_change(self.update_misc_column, section)
        for name in sectdata.keys():
            try:
                desc = sectdata.descriptions[name]
            except (KeyError, AttributeError):
                # Some stuff (especially ValueList items) don't have a
                # description.
                desc = ""
            else:
                desc = desc.splitlines()[0]
            value = config.get(section, name, raw=True)
            _valitem, _descitem, miscitem = self.new_item(cat, name, desc,
                                                          value)
            self._misc_items[name] = miscitem

    def update_misc_column(self, section, option):
        """Update misc column when config changed."""
        try:
            item = self._misc_items[option]
        except KeyError:
            log.completion.debug("Couldn't get item {}.{} from model!".format(
                section, option))
            # changed before init
            return
        val = config.get(section, option, raw=True)
        idx = item.index()
        qtutils.ensure_valid(idx)
        ok = self.setData(idx, val, Qt.DisplayRole)
        if not ok:
            raise ValueError("Setting data failed! (section: {}, option: {}, "
                             "value: {})".format(section, option, val))


class SettingValueCompletionModel(basecompletion.BaseCompletionModel):

    """A CompletionModel filled with setting values."""

    # pylint: disable=abstract-method

    def __init__(self, section, option=None, parent=None):
        super().__init__(parent)
        config.on_change(self.update_current_value, section, option)
        cur_cat = self.new_category("Current", sort=0)
        value = config.get(section, option, raw=True)
        if not value:
            value = '""'
        self.cur_item, _descitem, _miscitem = self.new_item(cur_cat, value,
                                                            "Current value")
        if hasattr(configdata.DATA[section], 'valtype'):
            # Same type for all values (ValueList)
            vals = configdata.DATA[section].valtype.complete()
        else:
            if option is None:
                raise ValueError("option may only be None for ValueList "
                                 "sections, but {} is not!".format(section))
            # Different type for each value (KeyValue)
            vals = configdata.DATA[section][option].typ.complete()
        if vals is not None:
            cat = self.new_category("Allowed", sort=1)
            for (val, desc) in vals:
                self.new_item(cat, val, desc)

    def update_current_value(self, section, option):
        """Update current value when config changed."""
        value = config.get(section, option, raw=True)
        if not value:
            value = '""'
        idx = self.cur_item.index()
        qtutils.ensure_valid(idx)
        ok = self.setData(idx, value, Qt.DisplayRole)
        if not ok:
            raise ValueError("Setting data failed! (section: {}, option: {}, "
                             "value: {})".format(section, option, value))


class CommandCompletionModel(basecompletion.BaseCompletionModel):

    """A CompletionModel filled with all commands and descriptions."""

    # pylint: disable=abstract-method

    def __init__(self, parent=None):
        super().__init__(parent)
        assert cmdutils.cmd_dict
        cmdlist = []
        for obj in set(cmdutils.cmd_dict.values()):
            if obj.hide or (obj.debug and not objreg.get('args').debug):
                pass
            else:
                cmdlist.append((obj.name, obj.desc))
        for name, cmd in config.section('aliases').items():
            cmdlist.append((name, "Alias for '{}'".format(cmd)))
        cat = self.new_category("Commands")
        for (name, desc) in sorted(cmdlist):
            self.new_item(cat, name, desc)


class HelpCompletionModel(basecompletion.BaseCompletionModel):

    """A CompletionModel filled with help topics."""

    # pylint: disable=abstract-method

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_commands()
        self._init_settings()

    def _init_commands(self):
        """Fill completion with :command entries."""
        assert cmdutils.cmd_dict
        cmdlist = []
        for obj in set(cmdutils.cmd_dict.values()):
            if obj.hide or (obj.debug and not objreg.get('args').debug):
                pass
            else:
                cmdlist.append((':' + obj.name, obj.desc))
        cat = self.new_category("Commands")
        for (name, desc) in sorted(cmdlist):
            self.new_item(cat, name, desc)

    def _init_settings(self):
        """Fill completion with section->option entries."""
        cat = self.new_category("Settings")
        for sectname, sectdata in configdata.DATA.items():
            for optname in sectdata.keys():
                try:
                    desc = sectdata.descriptions[optname]
                except (KeyError, AttributeError):
                    # Some stuff (especially ValueList items) don't have a
                    # description.
                    desc = ""
                else:
                    desc = desc.splitlines()[0]
                name = '{}->{}'.format(sectname, optname)
                self.new_item(cat, name, desc)


class QuickmarkCompletionModel(basecompletion.BaseCompletionModel):

    """A CompletionModel filled with all quickmarks."""

    # pylint: disable=abstract-method

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on_quickmarks_changed(self)

    def _on_quickmarks_changed(self, parent=None):

        qmlist = []
        for qm_name, qm_url in objreg.get('quickmark-manager').marks.items():
            qmlist.append((qm_url, qm_name))

        cat = self.new_category("Quickmarks")
        for (name, desc) in qmlist:
            self.new_item(cat, name, desc)


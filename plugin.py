import os
from typing import Optional

from os import path
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction, QMenu, QWidgetAction, QWidget, QVBoxLayout, QToolButton, QToolBar,
    QLabel, QComboBox
)
from .qgsmaptooladdlinebuffer import QgsMapToolAddLineBuffer

from qgis.core import QgsApplication, Qgis
from qgis.gui import QgisInterface, QgsDoubleSpinBox, QgsMapTool
from qgis.PyQt.QtCore import QTranslator, QCoreApplication

from .settings import DigitizrSettings
from . import about_dialog


class DigitizrPlugin:
    """QGIS Plugin Implementation."""

    PLUGIN_NAME = 'Digitizr'
    __translator: Optional[QTranslator]
    __toolbar: Optional[QToolBar]
    __tool_button: Optional[QToolButton]
    __about_action: Optional[QAction]
    __cap_combobox: Optional[QComboBox]
    __join_combobox: Optional[QComboBox]

    def __init__(self, iface: QgisInterface):
        self._iface = iface
        self.plugin_dir = path.dirname(__file__)

        self.__translator = None
        self.__toolbar = None
        self.__tool_button = None
        self.__about_action = None
        self.__cap_combobox = None
        self.__join_combobox = None

        self.__init_translator()

    def tr(self, message: str) -> str:
        return QgsApplication.translate(__class__.__name__, message)

    def initGui(self):
        settings = DigitizrSettings()

        self.__init_tool(settings)
        self.__init_toolbar(settings)

        canvas = self._iface.mapCanvas()
        assert canvas is not None
        canvas.mapToolSet.connect(self.__on_map_tool_set)

        self.toolAddLineBuffer.checkAvailability()

    def unload(self):
        self.__unload_toolbar()

    def activateToolAddLineBuffer(self, status):
        assert self.__tool_button is not None
        self.__tool_button.setChecked(True)
        canvas = self._iface.mapCanvas()
        assert canvas is not None
        canvas.setMapTool(self.toolAddLineBuffer)

    def __init_translator(self):
        # initialize locale
        locale = QgsApplication.instance().locale()

        def add_translator(locale_path):
            if not path.exists(locale_path):
                return
            translator = QTranslator()
            translator.load(locale_path)
            QCoreApplication.installTranslator(translator)
            self.__translator = translator  # Should be kept in memory

        add_translator(path.join(
            self.plugin_dir, 'i18n',
            f'digitizr_{locale}.qm'
        ))

    def __init_tool(self, settings: DigitizrSettings) -> None:
        self.toolAddLineBuffer = QgsMapToolAddLineBuffer(
            self._iface.mapCanvas(), self._iface.cadDockWidget()
        )
        self.toolAddLineBuffer.set_buffer_size(settings.buffer_size)
        self.toolAddLineBuffer.set_cap_style(settings.end_cap_style)
        self.toolAddLineBuffer.set_join_style(settings.join_style)

    def __init_toolbar(self, settings: DigitizrSettings):
        title = self.tr('{plugin_name} Toolbar') \
            .format(plugin_name=self.PLUGIN_NAME)
        self.__toolbar = self._iface.addToolBar(title)
        assert self.__toolbar is not None
        self.__toolbar.setToolTip(title)
        self.__toolbar.setObjectName('NGDigitizrToolBar')

        self.__init_tool_button(settings)
        self.__init_size_spin_box(settings)

    def __init_tool_button(self, settings: DigitizrSettings) -> None:
        assert self.__toolbar is not None

        root_dir = os.path.dirname(__file__)
        icons_dir = os.path.join(root_dir, "icons")

        tool_button = QToolButton(self.__toolbar)
        tool_button.setIcon(QIcon(os.path.join(icons_dir, "line_buffer.svg")))
        tool_button.setToolTip(self.tr("Add line buffer"))
        tool_button.setCheckable(True)
        tool_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        tool_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.MenuButtonPopup
        )
        tool_button.toggled.connect(self.activateToolAddLineBuffer)
        tool_button.setEnabled(self.toolAddLineBuffer.isAvalable())
        self.toolAddLineBuffer.availabilityChanged.connect(
            tool_button.setEnabled
        )
        self.__tool_button = tool_button

        self.__toolbar.addWidget(tool_button)

        vbox_layout = QVBoxLayout()

        vbox_layout.addWidget(QLabel(self.tr('End cap style')))
        self.__cap_combobox = self.__create_cap_combobox(settings)
        self.__cap_combobox.currentIndexChanged.connect(
            self.__on_cap_changed
        )
        vbox_layout.addWidget(self.__cap_combobox)

        vbox_layout.addWidget(QLabel(self.tr('Join style')))
        self.__join_combobox = self.__create_join_combobox(settings)
        self.__join_combobox.currentIndexChanged.connect(
            self.__on_join_changed
        )
        vbox_layout.addWidget(self.__join_combobox)

        tool_settings_widget = QWidget(tool_button)
        tool_settings_widget.setLayout(vbox_layout)

        digitizr_menu = QMenu(self.__toolbar)
        widget_action = QWidgetAction(digitizr_menu)
        widget_action.setDefaultWidget(tool_settings_widget)
        digitizr_menu.addAction(widget_action)
        digitizr_menu.addSeparator()
        self.__about_action = QAction(
            self.tr("About plugin…"), self._iface.mainWindow()
        )
        self.__about_action.triggered.connect(self.__open_about_dialog)
        digitizr_menu.addAction(self.__about_action)
        tool_button.setMenu(digitizr_menu)

    def __init_size_spin_box(self, settings: DigitizrSettings) -> None:
        assert self.__toolbar is not None
        size_spinbox = QgsDoubleSpinBox()
        size_spinbox.setDecimals(2)
        size_spinbox.setMaximum(99999999.99)
        size_spinbox.setValue(settings.buffer_size)
        size_spinbox.setToolTip(self.tr('Buffer size (meters)'))
        size_spinbox.valueChanged.connect(self.__on_width_changed)
        size_spinbox.setEnabled(self.toolAddLineBuffer.isAvalable())
        self.toolAddLineBuffer.availabilityChanged.connect(
            size_spinbox.setEnabled
        )
        self.__toolbar.addWidget(size_spinbox)

    def __create_cap_combobox(self, settings: DigitizrSettings) -> QComboBox:
        assert self.__toolbar is not None

        combobox = QComboBox()
        combobox.setToolTip(self.tr(
            'The end cap style parameter controls how line endings are handled'
            ' in the buffer'
        ))
        combobox.addItem(
            QgsApplication.getThemeIcon("cap_round.svg"),
            self.tr('Round'),
            Qgis.EndCapStyle.Round
        )
        combobox.addItem(
            QgsApplication.getThemeIcon("cap_square.svg"),
            self.tr('Square'),
            Qgis.EndCapStyle.Square
        )
        combobox.addItem(
            QgsApplication.getThemeIcon("cap_flat.svg"),
            self.tr('Flat'),
            Qgis.EndCapStyle.Flat
        )

        combobox.setCurrentIndex(combobox.findData(settings.end_cap_style))

        return combobox

    def __create_join_combobox(self, settings: DigitizrSettings) -> QComboBox:
        assert self.__toolbar is not None

        combobox = QComboBox()
        combobox.setToolTip(self.tr(
            'The join style parameter controls how segments joins are handled'
            ' when offsetting corners in a line'
        ))
        combobox.addItem(
            QgsApplication.getThemeIcon("join_round.svg"),
            self.tr('Round'),
            Qgis.JoinStyle.Round
        )
        combobox.addItem(
            QgsApplication.getThemeIcon("join_miter.svg"),
            self.tr('Miter'),
            Qgis.JoinStyle.Miter
        )
        combobox.addItem(
            QgsApplication.getThemeIcon("join_bevel.svg"),
            self.tr('Bevel'),
            Qgis.JoinStyle.Bevel
        )

        combobox.setCurrentIndex(combobox.findData(settings.join_style))

        return combobox

    def __unload_toolbar(self):
        assert self.__toolbar is not None
        self.__cap_combobox = None
        self.__join_combobox = None
        self.__toolbar.hide()
        self.__toolbar.deleteLater()
        self.__toolbar = None

    def __on_width_changed(self, value: float) -> None:
        self.toolAddLineBuffer.set_buffer_size(value)

        settings = DigitizrSettings()
        settings.buffer_size = value

    def __on_cap_changed(self, new_index: int) -> None:
        assert self.__cap_combobox is not None
        cap_style = self.__cap_combobox.itemData(new_index)

        self.toolAddLineBuffer.set_cap_style(cap_style)

        settings = DigitizrSettings()
        settings.end_cap_style = cap_style

    def __on_join_changed(self, new_index: int) -> None:
        assert self.__join_combobox is not None
        join_style = self.__join_combobox.itemData(new_index)

        self.toolAddLineBuffer.set_join_style(join_style)

        settings = DigitizrSettings()
        settings.join_style = join_style

    def __on_map_tool_set(
        self, new_tool: QgsMapTool, old_tool: QgsMapTool
    ) -> None:
        assert self.__tool_button is not None
        self.__tool_button.setChecked(new_tool == self.toolAddLineBuffer)

    def __open_about_dialog(self):
        dialog = about_dialog.AboutDialog(os.path.basename(self.plugin_dir))
        dialog.exec()

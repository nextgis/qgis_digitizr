import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgsmaptooladdlinebuffer import QgsMapToolAddLineBuffer

import settings

class DigitizrPlugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        self._iface = iface

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate('NGConnectPlugin', message)

    def initGui(self):
        self.toolAddLineBuffer = QgsMapToolAddLineBuffer(self._iface.mapCanvas(), self._iface.cadDockWidget())
        
        self.addToolAddLineBufferButton()

        self._iface.mapCanvas().mapToolSet.connect(self.disableTools)

    def unload(self):
        self.removeToolAddLineBufferButton()
    
    def disableTools(self, new_tool):
        if new_tool != self.toolAddLineBuffer:
            self.actionAddLineBuffer.setChecked(False)

    def activateToolAddLineBuffer(self, status):
        self.actionAddLineBuffer.setChecked(True)
        self._iface.mapCanvas().setMapTool(self.toolAddLineBuffer)

    def addToolAddLineBufferButton(self):
        self.toolAddLineBufferButton = QToolButton()
        self.toolAddLineBufferButton.setMenu(QMenu())
        self.toolAddLineBufferButton.setPopupMode(QToolButton.MenuButtonPopup)
        self._iface.addToolBarWidget(self.toolAddLineBufferButton)

        self.actionAddLineBuffer = QAction(self.tr("Add line buffer"), self._iface.mainWindow())
        self.actionAddLineBuffer.setIcon(QIcon(os.path.join(settings.icons_dir, "line_buffer.svg")))
        self.actionAddLineBuffer.setCheckable(True)
        self.actionAddLineBuffer.setEnabled(self.toolAddLineBuffer.isAvalable())
        self.actionAddLineBuffer.triggered.connect(self.activateToolAddLineBuffer)
        #self.toolAddLineBuffer.setAction(self.actionAddLineBuffer)
        self.toolAddLineBuffer.availabilityChange.connect(self.actionAddLineBuffer.setEnabled)

        self.actionAddLineBufferSettings = QAction(self.tr("Settings"), self._iface.mainWindow())
        self.actionAddLineBufferSettings.setIcon(QIcon(os.path.join(settings.icons_dir,"settings.svg")))
        self.actionAddLineBufferSettings.triggered.connect(self.showToolAddLineBufferButtonSettings)

        m = self.toolAddLineBufferButton.menu()
        # m.addAction(self.actionAddLineBuffer)
        m.addAction(self.actionAddLineBufferSettings)
        self.toolAddLineBufferButton.setDefaultAction(self.actionAddLineBuffer)

    def removeToolAddLineBufferButton(self):
        self._iface.removeToolBarIcon(self.actionAddLineBuffer)

    def showToolAddLineBufferButtonSettings(self):
        qgis_settings = QSettings()
        buffer_size, result = QInputDialog.getDouble(
            self._iface.mainWindow(),
            self.tr("Add line buffer settings"),
            self.tr("Buffer size (meters):"),
            qgis_settings.value(settings.buffer_size_key, type=float)
        )

        if result:
            qgis_settings.setValue(settings.buffer_size_key, buffer_size)

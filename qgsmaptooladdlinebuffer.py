from PyQt4.QtCore import *

from qgis.core import *
from qgis.gui import *

import settings

class QgsMapToolAddLineBuffer(QgsMapToolCapture):
    availabilityChange = pyqtSignal(bool)

    def __init__(self, canvas, cadDockWidget):
        QgsMapToolCapture.__init__(self, canvas, cadDockWidget, QgsMapToolAdvancedDigitizing.CaptureLine)
        self.mToolName = "Add line buffer"
        
        self.canvas().currentLayerChanged.connect(self.checkAvailability)
        self.canvas().mapCanvasRefreshed.connect(self.checkAvailability)

    def activate(self):
        super(QgsMapToolAddLineBuffer, self).activate()

    def cadCanvasReleaseEvent(self, event):
        vlayer = self.currentVectorLayer()

        if not vlayer:
            self.notifyNotVectorLayer()
            return;
        if not vlayer.isEditable():
            self.notifyNotEditableLayer()
            return;

        if event.button() == Qt.LeftButton:
            error = self.addVertex( event.mapPoint(), event.mapPointMatch() );
            #TODO Process error
            self.startCapturing();
            return
        elif event.button() != Qt.RightButton:
            self.deleteTempRubberBand()
            return

        line_wkt = self.captureCurve().curveToLine().asWkt()
        self.stopCapturing();

        g = QgsGeometry.fromWkt(line_wkt)

        qgis_settings = QSettings()
        buffer_size = qgis_settings.value(settings.buffer_size_key, type=float)
        buffer_size *= QGis.fromUnitToUnitFactor(QGis.Meters, vlayer.crs().mapUnits())
        
        buffer = g.buffer(buffer_size, -1)
        
        f = QgsFeature(vlayer.fields())
        f.setGeometry(buffer)
        
        vlayer.beginEditCommand( "Add line buffer" )
        res = vlayer.addFeature(f)

        vlayer.endEditCommand()
        self.canvas().refresh()

    def checkAvailability(self):
        self.availabilityChange.emit(self.isAvalable())

    def isAvalable(self):
        vlayer = self.currentVectorLayer()

        if not vlayer:
            return False

        if not vlayer.isEditable():
            return False

        if vlayer.geometryType() != QGis.Polygon:
            return False

        return True


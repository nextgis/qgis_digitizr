from __future__ import absolute_import
from qgis.PyQt.QtCore import pyqtSignal, Qt, QSettings

from qgis.core import QgsGeometry, QgsCoordinateTransform, QgsFeature, QgsWkbTypes, QgsProject
from qgis.gui import *

from . import settings

class QgsMapToolAddLineBuffer(QgsMapToolCapture):
    availabilityChange = pyqtSignal(bool)

    def __init__(self, canvas, cadDockWidget):
        QgsMapToolCapture.__init__(self, canvas, cadDockWidget, QgsMapToolCapture.CaptureMode.CaptureLine)        
        
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

        qgis_settings = QSettings()
        buffer_size = qgis_settings.value(settings.buffer_size_key)
        if buffer_size is None:
            buffer_size = 0.0
        buffer_size = float(buffer_size)

        g = QgsGeometry.fromWkt(line_wkt)
        transform_1 = QgsCoordinateTransform(vlayer.crs(), self.canvas().mapSettings().destinationCrs(), QgsProject.instance() )
        transform_2 = QgsCoordinateTransform(self.canvas().mapSettings().destinationCrs(), vlayer.crs(), QgsProject.instance())
        
        g.transform(transform_1)        
        buffer = g.buffer(buffer_size, -1)
        buffer.transform(transform_2)        

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

        if vlayer.geometryType() != QgsWkbTypes.GeometryType.PolygonGeometry:
            return False

        return True


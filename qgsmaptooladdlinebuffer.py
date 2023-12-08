from typing import Optional, cast

from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtWidgets import QAction

from qgis.core import (
    QgsGeometry, QgsCoordinateTransform, QgsFeature, QgsWkbTypes, QgsProject,
    QgsVectorDataProvider, Qgis, QgsVectorLayer, QgsDistanceArea
)
from qgis.gui import (
    QgsMapToolCapture, QgsMapCanvas, QgsAdvancedDigitizingDockWidget,
    QgsMapMouseEvent, QgisInterface
)
from qgis.utils import iface


iface = cast(QgisInterface, iface)


class QgsMapToolAddLineBuffer(QgsMapToolCapture):
    availabilityChanged = pyqtSignal(bool)

    __buffer_size: float
    __cap_style: Qgis.EndCapStyle
    __join_style: Qgis.JoinStyle

    def __init__(
        self,
        canvas: QgsMapCanvas,
        cadDockWidget: QgsAdvancedDigitizingDockWidget
    ) -> None:
        super().__init__(
            canvas, cadDockWidget, QgsMapToolCapture.CaptureMode.CaptureLine
        )

        self.__buffer_size = 10.0
        self.__cap_style = Qgis.EndCapStyle.Round
        self.__join_style = Qgis.JoinStyle.Round

        canvas.currentLayerChanged.connect(self.checkAvailability)

        main_window = iface.mainWindow()
        assert main_window is not None
        add_feature_action = main_window.findChild(
            QAction, 'mActionToggleEditing'
        )
        assert add_feature_action is not None
        add_feature_action.toggled.connect(
            self.checkAvailability,
            type=Qt.ConnectionType.QueuedConnection  # type: ignore
        )

    def set_buffer_size(self, size: float) -> None:
        self.__buffer_size = size

    def set_cap_style(self, cap_style: Qgis.EndCapStyle) -> None:
        self.__cap_style = cap_style

    def set_join_style(self, join_style: Qgis.JoinStyle) -> None:
        self.__join_style = join_style

    def convert_distance(self):
        project = QgsProject.instance()
        assert project is not None
        dist_calculator = QgsDistanceArea()
        dist_calculator.setSourceCrs(project.crs(), project.transformContext())
        dist_calculator.setEllipsoid(project.ellipsoid())
        result = dist_calculator.convertLengthMeasurement(
            self.__buffer_size, project.crs().mapUnits()
        )
        return result

    def cadCanvasReleaseEvent(self, event: Optional[QgsMapMouseEvent]) -> None:
        assert event is not None

        vlayer = self.currentVectorLayer()

        if vlayer is None:
            self.notifyNotVectorLayer()
            return
        if not vlayer.isEditable():
            self.notifyNotEditableLayer()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            error = self.addVertex(event.mapPoint(), event.mapPointMatch())
            # TODO Process error
            self.startCapturing()
            return
        elif event.button() != Qt.MouseButton.RightButton:
            self.deleteTempRubberBand()
            return

        line_wkt = self.captureCurve().curveToLine().asWkt()
        self.stopCapturing()

        line_geometry = QgsGeometry.fromWkt(line_wkt)
        transform = QgsCoordinateTransform(
            vlayer.crs(),
            self.canvas().mapSettings().destinationCrs(),
            QgsProject.instance()
        )

        lenght_buffer = self.convert_distance()

        line_geometry.transform(transform)
        buffer_geometry = line_geometry.buffer(
            distance=lenght_buffer,
            segments=10,
            endCapStyle=self.__cap_style,
            joinStyle=self.__join_style,
            miterLimit=2
        )

        buffer_geometry.transform(
            transform, QgsCoordinateTransform.ReverseTransform
        )

        f = QgsFeature(vlayer.fields())
        f.setGeometry(buffer_geometry)

        vlayer.beginEditCommand("Add line buffer")
        vlayer.addFeature(f)
        vlayer.endEditCommand()
        self.canvas().refresh()

    def checkAvailability(self):
        self.availabilityChanged.emit(self.isAvalable())

    def isAvalable(self):
        current_layer = self.currentVectorLayer()

        if current_layer is None:
            return False

        if not current_layer.isEditable():
            return False

        if not self.__is_layer_suitable(current_layer):
            return False

        return True

    def __is_layer_suitable(self, layer: QgsVectorLayer) -> bool:
        PolygonGeometry = QgsWkbTypes.GeometryType.PolygonGeometry
        if layer.geometryType() != PolygonGeometry:
            return False

        data_provider = layer.dataProvider()
        if data_provider is None:
            return False

        Capability = QgsVectorDataProvider.Capability
        if not bool(data_provider.capabilities() & Capability.AddFeatures):
            return False
        return True

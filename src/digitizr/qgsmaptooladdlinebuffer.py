from typing import cast

from qgis.core import (
    Qgis,
    QgsCompoundCurve,
    QgsCoordinateTransform,
    QgsDistanceArea,
    QgsFeature,
    QgsGeometry,
    QgsPoint,
    QgsProject,
    QgsVectorDataProvider,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import (
    QgisInterface,
    QgsAdvancedDigitizingDockWidget,
    QgsMapCanvas,
    QgsMapMouseEvent,
    QgsMapToolCapture,
    QgsRubberBand,
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import QAction
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
        cadDockWidget: QgsAdvancedDigitizingDockWidget,
    ) -> None:
        super().__init__(
            canvas, cadDockWidget, QgsMapToolCapture.CaptureMode.CaptureLine
        )

        self.__buffer_size = 10.0
        self.__cap_style = Qgis.EndCapStyle.Round
        self.__join_style = Qgis.JoinStyle.Round

        self.__rubber_band = QgsRubberBand(
            self.canvas(), QgsWkbTypes.PolygonGeometry
        )
        self.__rubber_band.setFillColor(self.digitizingFillColor())
        self.__rubber_band.setStrokeColor(self.digitizingStrokeColor())
        self.__rubber_band.setWidth(self.digitizingStrokeWidth())

        canvas.currentLayerChanged.connect(self.checkAvailability)

        main_window = iface.mainWindow()
        assert main_window is not None
        add_feature_action = main_window.findChild(
            QAction, "mActionToggleEditing"
        )
        assert add_feature_action is not None
        add_feature_action.toggled.connect(
            self.checkAvailability,
            type=Qt.ConnectionType.QueuedConnection,  # type: ignore
        )

    def set_buffer_size(self, size: float) -> None:
        self.__buffer_size = size
        self.__repaint_rubberband()

    def set_cap_style(self, cap_style: Qgis.EndCapStyle) -> None:
        self.__cap_style = cap_style
        self.__repaint_rubberband()

    def set_join_style(self, join_style: Qgis.JoinStyle) -> None:
        self.__join_style = join_style
        self.__repaint_rubberband()

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

    def cadCanvasMoveEvent(self, event: QgsMapMouseEvent) -> None:
        if not self.isCapturing():
            return

        self.__last_position = QgsPoint(event.mapPoint())
        self.__repaint_rubberband()
        super().cadCanvasMoveEvent(event)

    def cadCanvasReleaseEvent(self, event: QgsMapMouseEvent) -> None:
        vlayer = self.currentVectorLayer()

        if vlayer is None:
            self.notifyNotVectorLayer()
            return
        if not vlayer.isEditable():
            self.notifyNotEditableLayer()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.addVertex(event.mapPoint(), event.mapPointMatch())
            # TODO Process error
            self.startCapturing()
            line_geometry = QgsGeometry(self.captureCurve().curveToLine())
            self.__rubber_band.setToGeometry(
                self.__create_buffer(line_geometry), vlayer
            )
            return
        elif event.button() != Qt.MouseButton.RightButton:
            self.deleteTempRubberBand()
            return

        line_geometry = QgsGeometry(self.captureCurve().curveToLine())
        buffer_geometry = self.__create_buffer(line_geometry)
        self.stopCapturing()
        self.__rubber_band.reset()

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

    def __create_buffer(self, line_geometry: QgsGeometry) -> QgsGeometry:
        vlayer = self.currentVectorLayer()

        transform = QgsCoordinateTransform(
            vlayer.crs(),
            self.canvas().mapSettings().destinationCrs(),
            QgsProject.instance(),
        )

        lenght_buffer = self.convert_distance()

        line_geometry.transform(transform)
        buffer_geometry = line_geometry.buffer(
            distance=lenght_buffer,
            segments=10,
            endCapStyle=self.__cap_style,
            joinStyle=self.__join_style,
            miterLimit=2,
        )

        buffer_geometry.transform(
            transform, QgsCoordinateTransform.ReverseTransform
        )

        return buffer_geometry

    def __repaint_rubberband(self):
        if not self.isCapturing():
            return

        vlayer = self.currentVectorLayer()

        curve = QgsCompoundCurve(self.captureCurve())
        curve.addVertex(self.__last_position)
        line_geometry = QgsGeometry(curve)

        buffer_geometry = self.__create_buffer(line_geometry)
        self.__rubber_band.setToGeometry(buffer_geometry, vlayer)

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


from qgis.core import Qgis, QgsSettings


class DigitizrSettings:
    __settings: QgsSettings

    def __init__(self) -> None:
        self.__settings = QgsSettings()
        self.__migrate()

    @property
    def buffer_size(self) -> float:
        return self.__settings.value(
            f'{self.__plugin_group}/buffer_size', defaultValue=10.0, type=float
        )

    @buffer_size.setter
    def buffer_size(self, size: float) -> None:
        self.__settings.setValue(f'{self.__plugin_group}/buffer_size', size)

    @property
    def end_cap_style(self) -> Qgis.EndCapStyle:
        return Qgis.EndCapStyle(self.__settings.value(
            f'{self.__plugin_group}/end_cap_style',
            defaultValue=int(Qgis.EndCapStyle.Round),
            type=int
        ))

    @end_cap_style.setter
    def end_cap_style(self, cap_style: Qgis.EndCapStyle) -> None:
        self.__settings.setValue(
            f'{self.__plugin_group}/end_cap_style', int(cap_style)
        )

    @property
    def join_style(self) -> Qgis.JoinStyle:
        return Qgis.JoinStyle(self.__settings.value(
            f'{self.__plugin_group}/join_style',
            defaultValue=int(Qgis.JoinStyle.Round),
            type=int
        ))

    @join_style.setter
    def join_style(self, join_style: Qgis.JoinStyle) -> None:
        self.__settings.setValue(
            f'{self.__plugin_group}/join_style', int(join_style)
        )

    @property
    def __plugin_group(self) -> str:
        return 'NextGIS/Digitizr'

    def __migrate(self) -> None:
        old_size_key = '/ngdigitizr/addlinebuffer/buffer'
        old_buffer_size = self.__settings.value(old_size_key)
        if old_buffer_size is None:
            return

        self.__settings.setValue(
            f'{self.__plugin_group}/buffer_size', old_buffer_size
        )
        self.__settings.remove(old_size_key)

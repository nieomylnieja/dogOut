import geocoder
from kivy_garden.mapview import MapSource


class Map(MapSource):

    def __init__(self):
        ll = geocoder.ip("me").latlng
        super().__init__(lat=ll[0], lon=ll[1], name="map")

    def __key__(self):
        pass

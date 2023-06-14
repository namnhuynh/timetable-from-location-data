from enum import Enum

class pathsCols(Enum):
    lat = 'lat'
    lng = 'lng'
    RouteId = 'RouteId'
    RouteVarId = 'RouteVarId'

class stopsCols(Enum):
    Stops = 'Stops'
    StopsAttribs_StopId = 'StopId'
    StopsAttribs_Code = 'Code'
    StopsAttribs_Name = 'Name'
    StopsAttribs_Lng = 'Lng'
    StopsAttribs_Lat = 'Lat'
    RouteId = 'RouteId'
    RouteVarId = 'RouteVarId'

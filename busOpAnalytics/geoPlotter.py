import folium
from folium import FeatureGroup, LayerControl
import pandas as pd
import time

# ======================================================================================================================
def makeBaseMap():
    latlon = [10.77679, 106.705856]
    # m = folium.Map(location=latlon)
    m = folium.Map(location=latlon, tiles='cartodbpositron', zoom_start=11, prefer_canvas=True, control_scale=True,
                   zoom_control=False, png_enabled=True)
    # m = folium.Map(location=latlon, tiles='Stamen Terrain')
    # m = folium.Map(location=latlon, tiles='Stamen Toner')
    # m.save('hcmc.html')
    return m

# ======================================================================================================================
def plotStopsPaths(dfStops, dfPaths, myMap):
    dfStops['dirRoute'] = dfStops['RouteId'] + '_' + dfStops['RouteVarId']
    uDirRoutes = dfStops['dirRoute'].unique()

    tik = time.time()
    countPaths = 0
    for uDirRoute in uDirRoutes:
        routeLayer = FeatureGroup(name=uDirRoute, show=False)

        dfStopsDirR = dfStops.loc[dfStops['dirRoute']==uDirRoute]
        for idx, row in dfStopsDirR.iterrows():
            cMarker = folium.CircleMarker(location=[row['Lat'], row['Lng']],
                                          radius=2, color='red', weight=2, opacity=.3, fill_color='red',
                                          fill_opacity=.3,
                                          tooltip='StopId %d, Code %s, %s' % (row['StopId'], row['Code'], row['Name']))
            cMarker.add_to(routeLayer)

        [routeId, routeVarId] = uDirRoute.split('_')
        dfPathDirR = dfPaths.loc[(dfPaths['RouteId']==routeId) & (dfPaths['RouteVarId']==routeVarId)]
        pathCoords = [dfPathDirR['lat'].values[0], dfPathDirR['lng'].values[0]]
        pathRouteId = dfPathDirR['RouteId'].values[0]
        pathRouteVarId = dfPathDirR['RouteVarId'].values[0]

        for i in range(len(pathCoords[0])):
            cMarker = folium.CircleMarker(location=[pathCoords[0][i], pathCoords[1][i]],
                                          radius=1, color='blue', weight=2, opacity=.3, fill_color='blue',
                                          fill_opacity=.3,
                                          tooltip='[%.6f, %.6f], dirRoute %s_%s' %
                                                  (pathCoords[0][i], pathCoords[1][i], pathRouteId, pathRouteVarId))
            cMarker.add_to(routeLayer)

        path = [(pathCoords[0][i], pathCoords[1][i]) for i in range(len(pathCoords[0]))]
        pline = folium.PolyLine(path, color='blue', weight=2, opacity=.3,
                                popup='dirRoute %s_%s' % (pathRouteId, pathRouteVarId))
        pline.add_to(routeLayer)

        #countPaths += 1
        #if countPaths==3: break

        routeLayer.add_to(myMap)

    folium.GeoJson('../data/hcmc.geojson', control=False, show=True, name='HCMC').add_to(myMap)
    LayerControl().add_to(myMap)
    myMap.save('allStopsPaths.html')
    print('complete plotStopsPaths %.3f' % (time.time()-tik))
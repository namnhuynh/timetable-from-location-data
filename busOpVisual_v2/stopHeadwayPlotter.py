import time
import pandas as pd
import stopHeadway

import folium
from folium import features, FeatureGroup, LayerControl, Map, Marker, vector_layers
import branca

import altair as alt
from vega_datasets import data
alt.data_transformers.disable_max_rows()

from bokeh.plotting import figure, output_file, show, save
from bokeh.models import Legend, ColumnDataSource, HoverTool

def makeBubbleChart():
    dfHdwaySum = pd.read_csv('./pkl/dfHdwaySummaryAllRoutes.csv')
    dfHdwaySum['ActSchedMedHdwayRatio'] = dfHdwaySum['medActuHdway'] / dfHdwaySum['medSchedHdway']
    dfHdwaySumRoutes = dfHdwaySum.groupby(by=['DirRoute'])['ActSchedMedHdwayRatio'].mean().to_frame()
    dfHdwaySumRoutes.reset_index(inplace=True)
    dfHdwaySumRoutes.to_csv('./pkl/dfHdwaySumRoutes.csv')

    dfTimeDiffDays = pd.read_csv('dfTimeDiffDays.csv')
    dfTimeDiffDays.sort_values(by=['nTripsSched1Day'], inplace=True)
    dfTimeDiffDaysNoDupTmp = dfTimeDiffDays[['DirRoute', 'nTripsSched1Day', 'dist2nd_2ndLastStops']].drop_duplicates()
    tmpList = []
    for dirRoute in dfTimeDiffDaysNoDupTmp['DirRoute'].unique():
        dfSub = dfTimeDiffDaysNoDupTmp.loc[dfTimeDiffDaysNoDupTmp['DirRoute']==dirRoute]
        dfSub.sort_values(by=['nTripsSched1Day'], ascending=True, inplace=True)
        sub1stLine = dfSub.iloc[0][['DirRoute', 'nTripsSched1Day','dist2nd_2ndLastStops']].values.tolist()
        tmpList.append(sub1stLine)
    dfTimeDiffDaysNoDup = pd.DataFrame(tmpList, columns=['DirRoute', 'nTripsSched1Day','dist2nd_2ndLastStops'])
    #dfTimeDiffDaysNoDup.to_csv('dfTimeDiffDaysNoDup.csv')

    dfHdwaySumRoutes = dfHdwaySumRoutes.merge(dfTimeDiffDaysNoDup, on='DirRoute')
    print(dfHdwaySumRoutes.columns)
    source = ColumnDataSource(dfHdwaySumRoutes)
    p = figure(plot_width=1200, plot_height=600,  # x_axis_type="datetime",
               title='So sánh headway theo lịch và thực tế của các tuyến buýt', toolbar_location='below')
    p.scatter(x='dist2nd_2ndLastStops', y='ActSchedMedHdwayRatio',size='nTripsSched1Day', source=source,
                         alpha=.4, fill_color='#74add1')
    p.add_tools(HoverTool(tooltips=[('Directed route', '@DirRoute'),
                                    ('Number of daily scheduled trips', '@nTripsSched1Day')]))
    p.xaxis.axis_label = 'Chiều dài tuyến (ngoại trừ 2 trạm cuối) (m)'
    p.yaxis.axis_label = 'Chỉ số đo mức độ khác nhau của headway theo lịch và headway thực tế'
    output_file('../plots/bubblePlot.html')
    save(p)

# ======================================================================================================================
def makeBaseMap():
    latlon = [10.77679, 106.705856]
    tiles = 'cartodbpositron'  # or 'Stamen Terrain' or 'Stamen Toner'
    m = folium.Map(location=latlon, tiles=None, zoom_start=11, prefer_canvas=True, control_scale=True,
                   zoom_control=False, png_enabled=True)
    folium.TileLayer(tiles=tiles).add_to(m)
    #folium.TileLayer(tiles=tiles, name='Ngày %s, Thành phố Hồ Chí Minh' % selDateStr).add_to(m)
    #m.save('hcmc.html')
    return m

# ======================================================================================================================
def plotStopHdwayToBaseMap_v3():
    basemap = makeBaseMap()
    # dfHdwaysSummaryByStop = pd.read_csv('./pkl/dfHdwaysSummaryByStop.csv')
    dfHdwaySummaryAllRoutes = pd.read_csv('./pkl/dfHdwaySummaryAllRoutes.csv')
    dfHdwaySummaryAllRoutes['ActSchedMedHdwayRatio'] = dfHdwaySummaryAllRoutes['medActuHdway'] / \
                                                       dfHdwaySummaryAllRoutes['medSchedHdway']
    [uBnd, lBnd] = stopHeadway.getBounds(dfHdwaySummaryAllRoutes['ActSchedMedHdwayRatio'], 'all')
    # print('uBnd ActSchedMedHdwayRatio %.3f' % uBnd)
    dfHdwaySummaryAllRoutes = dfHdwaySummaryAllRoutes[dfHdwaySummaryAllRoutes['ActSchedMedHdwayRatio'] < max(uBnd, 10)]

    #nStops = len(dfHdwaySummaryAllRoutes['StopId'].unique().tolist())
    for stopId in dfHdwaySummaryAllRoutes['StopId'].unique():
        dfStopId = dfHdwaySummaryAllRoutes[dfHdwaySummaryAllRoutes['StopId']==stopId]
        dfStopId.sort_values(by=['ActSchedMedHdwayRatio'], ascending=False, inplace=True)
        for idx,row in dfStopId.iterrows():
            routeDesc = '%s, %s' % (row['DirRoute'], row['routeDesc'])
            print('stopId %d, route %s' % (stopId, routeDesc))
            popup = """<html>Chênh lệch headways: {val} lần</html><br> 
                    Trạm: {stopName} <br>
                    Tuyến: {routeDesc}
                    """.format(val = float("{:.3f}".format(row['ActSchedMedHdwayRatio'])),
                                stopName='%s (%d)' % (row['Name'], row['StopId']),
                                routeDesc=routeDesc)
            tooltip = """Trạm: {stopName} <br>
                        Tuyến: {routeDesc}
                        """.format(stopName='%s (%d)' % (row['Name'], row['StopId']),
                                   routeDesc=routeDesc)
            cMarker = vector_layers.CircleMarker(location=(row['Lat'], row['Lng']),
                                                 radius=row['ActSchedMedHdwayRatio'] * 2,
                                                 # to make circles more visible
                                                 popup=popup, tooltip=tooltip,
                                                 opacity=.5, fill_opacity=.5, fill_color='#74add1')
            cMarker.add_to(basemap)
    basemap.save('../plots/stopHdwayMapPlot_v3.html')


# ======================================================================================================================
def plotHdWayDetailstoBasemap():
    dfHdwaySummaryAllRoutes = pd.read_csv('./pkl/dfHdwaySummaryAllRoutes.csv')
    dfHdwaySummaryAllRoutes['ActSchedMedHdwayRatio'] = dfHdwaySummaryAllRoutes['medActuHdway'] / \
                                                       dfHdwaySummaryAllRoutes['medSchedHdway']
    dfHdwaySummaryAllRoutes['RouteId'] = dfHdwaySummaryAllRoutes['DirRoute'].apply(lambda x: x.split('_')[0])
    [uBnd, lBnd] = stopHeadway.getBounds(dfHdwaySummaryAllRoutes['ActSchedMedHdwayRatio'], 'all')
    # print('uBnd ActSchedMedHdwayRatio %.3f' % uBnd)
    dfHdwaySummaryAllRoutes = dfHdwaySummaryAllRoutes[dfHdwaySummaryAllRoutes['ActSchedMedHdwayRatio'] < max(uBnd, 10)]

    plottedRoutes = []
    nRoutes = len(dfHdwaySummaryAllRoutes['RouteId'].unique())
    tik = time.time()
    for routeId in dfHdwaySummaryAllRoutes['RouteId'].unique():
        basemap = makeBaseMap()
        if routeId in plottedRoutes: continue
        print('start plotting routeId %s' % routeId)
        dfHdwaySumRoute = dfHdwaySummaryAllRoutes[dfHdwaySummaryAllRoutes['RouteId'] == routeId]

        # plots other stops too - to make the background for comparison
        stopDirRouteThisRoute = dfHdwaySumRoute['stopDirRoute'].tolist()
        dfHdwaySumBckgrnd = dfHdwaySummaryAllRoutes[~dfHdwaySummaryAllRoutes['stopDirRoute'].isin(stopDirRouteThisRoute)]
        for idx,row in dfHdwaySumBckgrnd.iterrows():
            tooltip = """Trạm: {stopName} <br>Tuyến: {routeDesc}""".\
                format(stopName='%s (%d)' % (row['Name'], row['StopId']),
                       routeDesc='%s, %s' % (row['DirRoute'], row['routeDesc']))
            cMarker = vector_layers.CircleMarker(location=(row['Lat'], row['Lng']),
                                                 radius=row['ActSchedMedHdwayRatio'] * 2, # to make circles more visible
                                                 tooltip=tooltip, opacity=.5, fill_opacity=.5, fill_color='#74add1')
            cMarker.add_to(basemap)
        # ends plotting other stops for background

        for dirRoute in dfHdwaySumRoute['DirRoute'].unique():
            dfHdwaySumDirRoute = dfHdwaySumRoute[dfHdwaySumRoute['DirRoute'] == dirRoute]
            dfHdwayConcat = pd.read_csv('./pkl/dirRoutes/%s/dfActuSchedHdwaysConcat.csv' % dirRoute)
            dirRouteLayer = FeatureGroup(name='%s, %s' % (dirRoute, dfHdwaySumDirRoute.iloc[0]['routeDesc']),
                                         show=False)
            for idx, row in dfHdwaySumDirRoute.iterrows():
                routeDesc = '%s, %s' % (row['DirRoute'], row['routeDesc'])
                stopId = row['StopId']
                dfHdwayConcatStop = dfHdwayConcat[dfHdwayConcat['StopId']==stopId]
                vega = features.VegaLite(plotHdwaysDetail(dfHdwayConcatStop, row['Name'], routeDesc),
                                         width='100%', height='100%')
                popup = folium.Popup().add_child(vega)

                tooltip = """Trạm: {stopName} <br>Tuyến: {routeDesc}""". \
                    format(stopName='%s (%d)' % (row['Name'], row['StopId']), routeDesc=routeDesc)

                cMarker = vector_layers.CircleMarker(location=(row['Lat'], row['Lng']),
                                                     radius=row['ActSchedMedHdwayRatio'] * 2,
                                                     # to make circles more visible
                                                     popup=popup, tooltip=tooltip,
                                                     opacity=.5, fill_opacity=.5, fill_color='#FF3030', color='#FF3030')
                cMarker.add_to(dirRouteLayer)
            dirRouteLayer.add_to(basemap)

        LayerControl().add_to(basemap)
        basemap.save('../plots/routes/%s.html' % routeId)
        plottedRoutes.append(routeId)
        print('finished plotting routeId %s ' % routeId)
        print('finished plotting %d/%d routes in %.3f secs' % (len(plottedRoutes), nRoutes, time.time()-tik))
        print(plottedRoutes)

# ======================================================================================================================
def plotStopHdwayToBaseMap_v2():
    basemap = makeBaseMap()

    #dfHdwaysSummaryByStop = pd.read_csv('./pkl/dfHdwaysSummaryByStop.csv')
    dfHdwaySummaryAllRoutes = pd.read_csv('./pkl/dfHdwaySummaryAllRoutes.csv')
    dfHdwaySummaryAllRoutes['ActSchedMedHdwayRatio'] = dfHdwaySummaryAllRoutes['medActuHdway']/\
                                                       dfHdwaySummaryAllRoutes['medSchedHdway']
    [uBnd,lBnd] = stopHeadway.getBounds(dfHdwaySummaryAllRoutes['ActSchedMedHdwayRatio'], 'all')
    #print('uBnd ActSchedMedHdwayRatio %.3f' % uBnd)
    dfHdwaySummaryAllRoutes = dfHdwaySummaryAllRoutes[dfHdwaySummaryAllRoutes['ActSchedMedHdwayRatio'] < max(uBnd,10)]

    countStops = 0
    nStops = len(dfHdwaySummaryAllRoutes['StopId'].unique().tolist())
    tik = time.time()
    for stopId in dfHdwaySummaryAllRoutes['StopId'].unique():
        dfStopId = dfHdwaySummaryAllRoutes[dfHdwaySummaryAllRoutes['StopId']==stopId]
        dfStopId.sort_values(by=['ActSchedMedHdwayRatio'], ascending=False, inplace=True)
        for idx,row in dfStopId.iterrows():
            routeDesc = '%s, %s' % (row['DirRoute'], row['routeDesc'])
            print('stopId %d, route %s' % (stopId, routeDesc))
            dfHdwaysSub = pd.read_csv('./pkl/dirRoutes/%s/dfActuSchedHdwaysConcat.csv' % row['DirRoute'])
            #colused = ['StopId', 'dTimeSecs', 'datestr', 'day', 'Type', 'date', 'time']
            dfHdwaysSub = dfHdwaysSub[dfHdwaysSub['StopId']==row['StopId']]
            vega = features.VegaLite(plotHdwaysDetail(dfHdwaysSub, row['Name'], routeDesc), width='100%', height='100%')
            #vega = features.VegaLite(testAltairPlot(), width='100%', height='100%')
            popup = folium.Popup().add_child(vega)

            tooltip = """Trạm: {stopName} <br>
            Tuyến: {routeDesc}
            """.format(stopName = '%s (%d)' % (row['Name'], row['StopId']),
                       routeDesc = routeDesc)

            cMarker = vector_layers.CircleMarker(location=(row['Lat'],row['Lng']),
                                                 radius=row['ActSchedMedHdwayRatio']*2, # to make circles more visible
                                                 popup=popup, tooltip=tooltip,
                                                 opacity = .5, fill_opacity=.5, fill_color = '#74add1')
            cMarker.add_to(basemap)
        countStops += 1
        if countStops%50==0:
            print('plotStopHdwayToBaseMap_v2, finished %d/%d stops in %.3f' % (countStops, nStops, time.time()-tik))
        if countStops%300==0:
            basemap.save('../plots/stopHdwayMapPlot_v2_%dStops.html' % countStops)

    basemap.save('../plots/stopHdwayMapPlot_v2_allStops.html')

# ======================================================================================================================
def plotHdwaysDetail(dfHdwaysStopDirRoute, stopName, routeDesc):
    dayPlot = plotHdwaysByDay(dfHdwaysStopDirRoute, stopName, routeDesc)
    monHrPlot = plotHdwaysByHour(dfHdwaysStopDirRoute, 'Monday')
    tueHrPlot = plotHdwaysByHour(dfHdwaysStopDirRoute, 'Tuesday')
    wedHrPlot = plotHdwaysByHour(dfHdwaysStopDirRoute, 'Wednesday')
    thuHrPlot = plotHdwaysByHour(dfHdwaysStopDirRoute, 'Thursday')
    friHrPlot = plotHdwaysByHour(dfHdwaysStopDirRoute, 'Friday')
    output = alt.vconcat(dayPlot, monHrPlot, tueHrPlot, wedHrPlot, thuHrPlot, friHrPlot)
    return output

# ======================================================================================================================
def plotHdwaysByHour(dfHdwaysStopDirRoute, day):
    dfHdwaysDaySched = dfHdwaysStopDirRoute[(dfHdwaysStopDirRoute['day']==day) &
                                            (dfHdwaysStopDirRoute['Type']=='Scheduled')]
    dfHdwaysDayActual = dfHdwaysStopDirRoute[(dfHdwaysStopDirRoute['day'] == day) &
                                             (dfHdwaysStopDirRoute['Type'] == 'Actual')]
    if (dfHdwaysDaySched.shape[0]==0) or (dfHdwaysDayActual.shape[0]==0): # either no scheduled or no actual trips
        output = alt.LayerChart().properties(width=800, height=150, title='%ss' % day) # returns an empty chart
    else:
        aDate = dfHdwaysDaySched['datestr'].unique()[0]
        dfHdwaysDaySched = dfHdwaysDaySched[dfHdwaysDaySched['datestr']==aDate]
        schedHdways = alt.Chart(dfHdwaysDaySched).mark_line(point=True, color='red').encode(
            x=alt.X('time:T', axis=alt.Axis(format='%H:%M', title='')),
            y=alt.Y('dTimeSecs:Q', title='Headway (minutes)')
        )
        actualHdways = alt.Chart(dfHdwaysDayActual).mark_line(
            point=True, opacity=.3, fillOpacity=.3
        ).encode(
            x=alt.X('time:T', axis=alt.Axis(format='%H:%M', title='')),
            y=alt.Y('dTimeSecs:Q'),
            color=alt.Color('datestr', legend=None)
        )
        plot = (schedHdways + actualHdways).interactive()
        output = alt.layer(plot).properties(width=800, height=120, title='%ss' % day)
    return output

def mkEmptyDfHdways():
    dfEmptyHdways = pd.DataFrame({'dTimeSecs': [0], 'timestr': ['00:00:00'], 'datestr': ['01/01/1900']})
    dfEmptyHdways['time'] = pd.to_datetime(dfEmptyHdways['timestr'], format='%H:%M:%S')
    return dfEmptyHdways

# ======================================================================================================================
def plotHdwaysByDay(dfHdwaysStopDirRoute, stopName, routeDesc):
    points = alt.Chart(dfHdwaysStopDirRoute).mark_point().encode(
        x=alt.X('date:T', axis=alt.Axis(format='%d/%m', title='')),
        # y=alt.Y('dTimeSecs:Q', aggregate='median', title='Headway (minutes)'),
        y=alt.Y('median(dTimeSecs):Q', title='Headway (minutes)'),
        color=alt.Color('Type:N', legend=None)
    )
    errorBars = points.mark_rule().encode(
        y='q1(dTimeSecs)',
        y2='q3(dTimeSecs)'
    )
    plot = (points + errorBars).interactive()
    output = alt.layer(plot).properties(width=800, height=120,
                                        title='Headways at stop %s, route %s' % (stopName, routeDesc))
    return output

def testAltairPlot():
    source = data.barley()

    bars = alt.Chart().mark_bar().encode(
        x='year:O',
        y=alt.Y('mean(yield):Q', title='Mean Yield'),
        color='year:N',
    )
    '''
    error_bars = alt.Chart().mark_errorbar(extent='ci').encode(
        x='year:O',
        y='yield:Q'
    )
    '''
    alt.layer(bars, data=source).facet(
        column='site:N'
    )

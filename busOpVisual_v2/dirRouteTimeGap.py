import folium
from folium import features, FeatureGroup, LayerControl, vector_layers, Map, Marker
from folium.features import GeoJson, GeoJsonTooltip
from folium.plugins import MarkerCluster, FloatImage, BeautifyIcon
import branca.colormap as cm

import altair as alt
from vega_datasets import data

from bokeh.plotting import figure, output_file, show, save
from bokeh.models import Legend, ColumnDataSource, HoverTool
from bokeh.layouts import column, gridplot, row
from bokeh.models.formatters import DatetimeTickFormatter

import pandas as pd

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
def getBounds(aSeries):
    # calcs bounds using 3-sigma method
    upperBnd_3Sigma = aSeries.mean() + 3 * aSeries.std()
    lowerBnd_3Sigma = aSeries.mean() - 3 * aSeries.std()

    # calcs bounds using boxplot method
    [q1, q3] = aSeries.quantile([.25, .75]).values
    upperBnd_Boxplot = q3 + 1.5 * (q3 - q1)
    lowerBnd_Boxplot = q1 - 1.5 * (q3 - q1)

    # calcs bounds using Hampel method
    bSeries = abs(aSeries - aSeries.median())
    madm = 1.4826 * bSeries.median()
    upperBnd_hampel = aSeries.median() + 3 * madm
    lowerBnd_hampel = aSeries.median() - 3 * madm

    maxUpperBnd = max(upperBnd_3Sigma, upperBnd_Boxplot, upperBnd_hampel)
    minLowerBnd = min(lowerBnd_3Sigma, lowerBnd_Boxplot, lowerBnd_hampel)
    return [maxUpperBnd, minLowerBnd]

def preprocessTimeDiffs(dfTimeDiffDays):
    '''
    :param dfTimeDiffDays:
    :return:
    '''
    dfdtMeanDirRoutes = pd.DataFrame()

    '''
    # calculates the average minAvgAbsTimeDiff for each dir route over the whole period (i.e. all trips in all days)
    dfdtMeanDirRoutesAllDays = dfTimeDiffDays.groupby(by=['DirRoute'])['minAvgAbsTimeDiff'].mean().to_frame()
    '''
    # or we can calculate median
    dfdtMeanDirRoutesAllDays = dfTimeDiffDays.groupby(by=['DirRoute'])['minAvgAbsTimeDiff'].median().to_frame()
    # removes those trips that have the average (or median) of minAvgAbsTimeDiff deemed to be outlier.
    # (these trips will not be plotted)
    [uBnd, lBnd] = getBounds(dfdtMeanDirRoutesAllDays['minAvgAbsTimeDiff'])
    dfdtMeanDirRoutesAllDays = dfdtMeanDirRoutesAllDays[dfdtMeanDirRoutesAllDays['minAvgAbsTimeDiff'] < uBnd]
    dfdtMeanDirRoutesAllDays['day'] = 'allDays'

    dfdtMeanDirRoutes = pd.concat([dfdtMeanDirRoutes, dfdtMeanDirRoutesAllDays])

    for day in dfTimeDiffDays['day'].unique():
        dfTimeDiff1Day = dfTimeDiffDays[dfTimeDiffDays['day']==day]
        # or we can calculate median
        dfdtMeanDirRoutes1Day = dfTimeDiff1Day.groupby(by=['DirRoute'])['minAvgAbsTimeDiff'].median().to_frame()
        # removes those trips that have the average (or median) of minAvgAbsTimeDiff deemed to be outlier.
        # (these trips will not be plotted)
        [uBnd, lBnd] = getBounds(dfdtMeanDirRoutes1Day['minAvgAbsTimeDiff'])
        dfdtMeanDirRoutes1Day = dfdtMeanDirRoutes1Day[dfdtMeanDirRoutes1Day['minAvgAbsTimeDiff'] < uBnd]
        dfdtMeanDirRoutes1Day['day'] = day
        dfdtMeanDirRoutes = pd.concat([dfdtMeanDirRoutes, dfdtMeanDirRoutes1Day])

    '''
    # sort descendingly, we want to plot dir routes with high minAvgAbsTimeDiff first
    dfdtMeanDirRoutes.sort_values(by=['minAvgAbsTimeDiff'], ascending=False, inplace=True)
    '''
    # reset index
    dfdtMeanDirRoutes.reset_index(inplace=True)
    return dfdtMeanDirRoutes

# ======================================================================================================================
def plotRoutesToBaseMap(dfdtMeanDirRoutes, dfTimeDiffDays, dfPaths, dfRoutes, baseMap):
    dfdtMeanDirRoutes = dfdtMeanDirRoutes[dfdtMeanDirRoutes['day']=='allDays']
    # sort descendingly, we want to plot dir routes with high minAvgAbsTimeDiff first
    dfdtMeanDirRoutes.sort_values(by=['minAvgAbsTimeDiff'], ascending=False, inplace=True)
    dfdtMeanDirRoutes.reset_index(inplace=True)

    mindt = dfdtMeanDirRoutes['minAvgAbsTimeDiff'].min()
    maxdt = dfdtMeanDirRoutes['minAvgAbsTimeDiff'].max()
    colourmap = cm.LinearColormap(vmin=mindt, vmax=maxdt, colors=['green', 'yellow', 'red'])
    colourmap.caption = 'Directed route actual vs scheduled time gap (in minutes)'

    countDirRoutes = 0
    for idx,row in dfdtMeanDirRoutes.iterrows():
        dirRoute = row['DirRoute']
        meandt = row['minAvgAbsTimeDiff']

        print('%s, %.6f' % (dirRoute, meandt))
        # gets timediff and the number of scheduled trips of this directed route
        dfdtDirRoute = dfTimeDiffDays[dfTimeDiffDays['DirRoute']==dirRoute]
        dfdtDirRoute.rename(columns={'minAvgAbsTimeDiff': 'Avg time gap at stops',
                                     'timestr': 'Scheduled departure time',
                                     'datestr': 'Date',
                                     'day': 'Day'}, inplace=True)

        colourDirRoute = colourmap(meandt)
        weightDirRoute = 3
        opacityDirRoute = .7

        # gets path points of this directed route from dfPaths
        lats = dfPaths['lat'].loc[(dfPaths['RouteId'] == int(dirRoute.split('_')[0])) &
                                  (dfPaths['RouteVarId'] == int(dirRoute.split('_')[1]))].values[0]
        lngs = dfPaths['lng'].loc[(dfPaths['RouteId'] == int(dirRoute.split('_')[0])) &
                                  (dfPaths['RouteVarId'] == int(dirRoute.split('_')[1]))].values[0]
        pathPoints = [(lats[i], lngs[i]) for i in range(len(lats))]
        # gets list of stops of dirRoute and dirRoute description from dfRoutes
        stops = dfRoutes[['Lat', 'Lng', 'Name']].loc[dfRoutes['DirRoute'] == dirRoute]
        routeDesc = '%s -> %s' % (stops.iloc[0]['Name'], stops.iloc[-1]['Name'])

        routeLayer = FeatureGroup(name='%s, %s' % (dirRoute, routeDesc), show=False)

        # adds polyline of this directed route to routeLayer
        vega = features.VegaLite(plotTimeDiffDetail(dfdtDirRoute, dirRoute, routeDesc), width='100%', height='100%')
        #vega = features.VegaLite(tstErrorBars(), width='100%', height='100%')
        popup = folium.Popup().add_child(vega)
        routeLine = folium.PolyLine(pathPoints, color=colourDirRoute, weight=weightDirRoute, opacity=opacityDirRoute,
                                    tooltip='%s, %s' % (dirRoute, routeDesc), popup=popup)
        routeLine.add_to(routeLayer)

        # adds only the 1st stop and the last stop to routeLayer (or alternatively we can add all stops along dirRoute)
        for i in [0,-1]: #for idx,row in stops.iterrows():
            row = stops.iloc[i]
            vector_layers.CircleMarker(location=(row['Lat'], row['Lng']), radius=5, tooltip=row['Name'],
                                       color=colourDirRoute, opacity=opacityDirRoute).add_to(routeLayer)

        # adds layer of this route to basemap
        routeLayer.add_to(baseMap)
        countDirRoutes += 1
        #if countDirRoutes==10: break

    baseMap.add_child(colourmap)
    LayerControl().add_to(baseMap)
    baseMap.save('../plots/timeDiffDirRoutesMapPlot.html')

# ======================================================================================================================
def plotTimeDiffDetail(dfdtDirRoute, dirRoute, routeDesc):
    plot1 = plotTimeDiffByHour(dfdtDirRoute, dirRoute, routeDesc)
    plot2 = plotTimeDiffByDate(dfdtDirRoute, dirRoute)
    output = alt.vconcat(plot1, plot2)
    return output

def plotTimeDiffByHour(dfdtDirRoute, dirRoute, routeDesc):
    '''
    :param dfdtDirRoute:
    :param dirRoute:
    :return:
    '''
    selection = alt.selection_multi(fields=['Day'], bind='legend')
    output = alt.Chart(dfdtDirRoute).mark_circle(size=60).encode(
        x=alt.X('time:T', axis=alt.Axis(format='%H:%M', title='')), #x=alt.X('hoursminutes(time):T'),
        y=alt.Y('Avg time gap at stops:Q', title='Number of minutes'),
        color=alt.Color('Day:N'),
        tooltip = ['Scheduled departure time', 'Date', 'Day', alt.Tooltip('Avg time gap at stops:Q',format=',.3f')],
        opacity = alt.condition(selection, alt.value(1.0), alt.value(0.0))
    ).properties(
        width=600, height=200, title='Actual vs scheduled time gap directed route %s, %s' % (dirRoute, routeDesc)
    ).add_selection(
        selection
    ).interactive()

    #output = alt.layer(plot).properties(width=500, height=200)

    return output

def plotTimeDiffByDate(dfdtDirRoute, dirRoute):
    points = alt.Chart(dfdtDirRoute).mark_point(filled=True,color='black').encode(
        x=alt.X('date:T', axis=alt.Axis(format='%d/%m', title='')),
        y=alt.Y('Avg time gap at stops:Q', aggregate='mean',
                title='Number of minutes')
    )
    # more info on ci0 and ci1 and other options is at https://altair-viz.github.io/user_guide/encoding.html
    errorBars = points.mark_rule().encode(
        y='ci0(Avg time gap at stops)',
        y2='ci1(Avg time gap at stops)',
    )
    plot = (points+errorBars).interactive()
    output = alt.layer(plot).properties(width=600, height=200)
    return output

# ======================================================================================================================
def plotTimeGapBubbleChart_v2(dfdtMeanDirRoutes, dfTimeDiffDays):
    p = figure(plot_width=1200, plot_height=900,  # x_axis_type="datetime",
               title='Median of scheduled vs actual time gap of directed routes', toolbar_location='below')
    # dfdtMeanDirRoutes columns are DirRoute  minAvgAbsTimeDiff  nTripsSched1Day  dist2nd_2ndLastStops, day
    dfTimeDiffDays.sort_values(by=['nTripsSched1Day'], inplace=True)
    dfTimeDiffDaysNoDup = dfTimeDiffDays[['DirRoute', 'nTripsSched1Day', 'dist2nd_2ndLastStops']].drop_duplicates()
    dfTimeDiffDaysNoDup.to_csv('dfTimeDiffDaysNoDup.csv')
    legendList = []

    # plot allDays
    dfdtMeanDirRoutesAllDays = dfdtMeanDirRoutes[dfdtMeanDirRoutes['day']=='allDays']
    dfdtMeanDirRoutesAllDays = dfdtMeanDirRoutesAllDays.merge(dfTimeDiffDaysNoDup, on='DirRoute')
    #print(dfdtMeanDirRoutes.head(10))
    source = ColumnDataSource(dfdtMeanDirRoutesAllDays)
    pAllDays = p.scatter(x='dist2nd_2ndLastStops', y='minAvgAbsTimeDiff',size='nTripsSched1Day', source=source,
                         alpha=.4, fill_color='#74add1')
    #pAllDays = p.scatter(x=dfdtMeanDirRoutesAllDays['dist2nd_2ndLastStops'],
    #                     y=dfdtMeanDirRoutesAllDays['minAvgAbsTimeDiff'],
    #                     size=dfdtMeanDirRoutesAllDays['nTripsSched1Day'], alpha=.7, fill_color='#74add1')
    
    legendList.append(('All days', [pAllDays]))

    # plot each day of the week
    colorDict = {'Monday': 'orange', 'Tuesday': 'cyan', 'Wednesday': 'green', 'Thursday': 'red', 'Friday': 'yellow'}
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        dfdtMeanDirRoutes1Day = dfdtMeanDirRoutes[dfdtMeanDirRoutes['day'] == day]
        dfdtMeanDirRoutes1Day = dfdtMeanDirRoutes1Day.merge(dfTimeDiffDaysNoDup, on='DirRoute')
        # print(dfdtMeanDirRoutes.head(10))
        source = ColumnDataSource(dfdtMeanDirRoutes1Day)
        p1Day = p.scatter(x='dist2nd_2ndLastStops', y='minAvgAbsTimeDiff', size='nTripsSched1Day', source=source,
                          alpha=.4, fill_color=colorDict[day])
        #p1Day = p.scatter(x=dfdtMeanDirRoutes1Day['dist2nd_2ndLastStops'],
        #                     y=dfdtMeanDirRoutes1Day['minAvgAbsTimeDiff'],
        #                     size=dfdtMeanDirRoutes1Day['nTripsSched1Day'], alpha=.5, fill_color=colorDict[day])

        legendList.append((day, [p1Day]))

    legend = Legend(items=legendList)
    legend.click_policy = 'hide'
    legend.label_text_font_size = '10px'
    #legend.label_height = 8
    p.add_layout(legend, 'right')
    p.add_tools(HoverTool(tooltips=[('Directed route', '@DirRoute'),
                                    ('Number of daily scheduled trips', '@nTripsSched1Day')]))
    p.xaxis.axis_label = 'Trip length (end stops excluded) (m)'
    p.yaxis.axis_label = 'Median of actual vs scheduled time gap of directed routes'

    output_file('../plots/timeDiffBubbleChart.html')
    save(p)

# ======================================================================================================================

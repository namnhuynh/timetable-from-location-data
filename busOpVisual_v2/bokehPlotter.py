from bokeh.plotting import figure, output_file, show, save
from bokeh.models import Legend
from bokeh.layouts import column, gridplot, row
from bokeh.models.formatters import DatetimeTickFormatter

import pandas as pd

# ======================================================================================================================
def plotTtbsToBokeh(dfTtbMatched, dfTtbActual, dirRoute, routeDesc, plotFilename, pltTimeWindow=[]):
    def secs2HHMMSS(secs):
        hh = int(secs / 3600)
        mm = int((secs % 3600) / 60)
        ss = secs - hh*3600 - mm*60
        return '%d:%d:%d' % (hh,mm,ss)

    if pltTimeWindow:
        dfTtbMatchedSub = dfTtbMatched.loc[(dfTtbMatched['TimeSecs']>=pltTimeWindow[0]) &
                                           (dfTtbMatched['TimeSecs']<=pltTimeWindow[1])]
    else: # if pltTimeWindow is empty, gets everything corresponding to TimeSecs between 0-86400
        dfTtbMatchedSub = dfTtbMatched.loc[(dfTtbMatched['TimeSecs'] >= 0) &
                                           (dfTtbMatched['TimeSecs'] <= 24*3600)]

    p = figure(plot_width=1800, plot_height=1000, x_axis_type="datetime",
               title='Scheduled vs Actual Timetable Directed Route %s, %s' % (dirRoute, routeDesc),
               toolbar_location='below')

    legendList = []
    for uTrip in dfTtbMatchedSub['TripId'].unique():
        dfTrip = dfTtbMatchedSub[dfTtbMatchedSub['TripId']==uTrip]

        dfTrip['TimeStr'] = dfTrip['TimeSecs'].apply(lambda x: secs2HHMMSS(x))
        dfTrip['TimeFrmted'] = pd.to_datetime(dfTrip['TimeStr'], format = '%H:%M:%S')
        schedPnts = p.square(dfTrip['TimeFrmted'], dfTrip['MetresToEnd'], line_color='red', size=6, alpha=.7)
        schedLine = p.line(dfTrip['TimeFrmted'], dfTrip['MetresToEnd'], line_color='red', line_width=2, alpha=.7,
                           line_dash='dashed')
        tripDesc = '%d' % uTrip
        elementsThisTrip = [schedPnts, schedLine]

        dfTripActual = dfTrip.loc[dfTrip['ActualTimeSecs']>-1]
        if dfTripActual.shape[0]>0: # if this scheduled trip has a matching actual trip
            dfTripActual['ActualTimeStr'] = dfTripActual['ActualTimeSecs'].apply(lambda x: secs2HHMMSS(x))
            dfTripActual['ActualTimeFrmted'] = pd.to_datetime(dfTripActual['ActualTimeStr'], format = '%H:%M:%S')
            actualPnts = p.square(dfTripActual['ActualTimeFrmted'], dfTripActual['MetresToEnd'],
                                  line_color='green', size=6, alpha=.7)
            actualLine = p.line(dfTripActual['ActualTimeFrmted'], dfTripActual['MetresToEnd'],
                                line_color='green', line_width=2, alpha=.7, line_dash='dashed')
            dirRouteVehTripNo = dfTripActual.iloc[0]['DirRouteVehTripNo'].split('_')
            tripDesc = '%s_%s_%s' % (tripDesc, dirRouteVehTripNo[2], dirRouteVehTripNo[3])
            elementsThisTrip = elementsThisTrip + [actualPnts, actualLine]

        legendList.append((tripDesc, elementsThisTrip))

    # plots any actual trips that were not matched with a scheduled trips
    uMatchedDirRouteVehTripNo = dfTtbMatchedSub['DirRouteVehTripNo'].unique().tolist()
    dfTtbActualUnplotted = dfTtbActual.loc[~dfTtbActual['DirRouteVehTripNo'].isin(uMatchedDirRouteVehTripNo)]
    if dfTtbActualUnplotted.shape[0]>0:
        for dirRouteVehTripNo in dfTtbActualUnplotted['DirRouteVehTripNo'].unique():
            dfTripRem = dfTtbActualUnplotted[(dfTtbActualUnplotted['DirRouteVehTripNo']==dirRouteVehTripNo) &
                                             (dfTtbActualUnplotted['TimeSecs']>-1)]

            dfTripRem['ActualTimeStr'] = dfTripRem['TimeSecs'].apply(lambda x: secs2HHMMSS(x))
            dfTripRem['ActualTimeFrmted'] = pd.to_datetime(dfTripRem['ActualTimeStr'], format='%H:%M:%S')

            actUnplotPnts = p.square(dfTripRem['ActualTimeFrmted'], dfTripRem['MetresToEnd'], line_color='green',
                                     size=6, alpha=.7)
            actUnplotLine = p.line(dfTripRem['ActualTimeFrmted'], dfTripRem['MetresToEnd'], line_color='green',
                                   line_width=2, alpha=.7, line_dash='dashed')
            tripDesc = '%s_%s' % (dirRouteVehTripNo.split('_')[2], dirRouteVehTripNo.split('_')[3])
            legendList.append((tripDesc, [actUnplotPnts, actUnplotLine]))

    legend = Legend(items=legendList)
    legend.click_policy = 'hide'
    legend.label_text_font_size = '8px'
    legend.label_height = 8
    p.add_layout(legend, 'right')
    p.xaxis.formatter = DatetimeTickFormatter(hours="%H:%M", seconds="%S") # days="%d-%b-%Y %H:%M:%S"

    output_file(plotFilename)
    save(p)

import pandas as pd
import time
from enum import Enum
from datetime import datetime
from rdp import rdp
import matplotlib.pyplot as plt
from pathlib import Path
import pickle
import shutil
import math

from bokeh.plotting import figure, output_file, show, save
from bokeh.models import Legend
from bokeh.layouts import column, gridplot, row
from bokeh.models.formatters import DatetimeTickFormatter

import routeHandler

pd.options.mode.chained_assignment = None

# ======================================================================================================================
class predictionsCols(Enum):
    RequestTime = 0
    StopId = 1
    RouteId = 2
    RouteVarId = 3
    BusId = 4
    LocTimeStamp = 5
    Distance_m = 6
    Speed_kmph = 7
    TimeToStop_sec = 8

def mkList(myEnum):
    return [val.name for val in myEnum]

# ======================================================================================================================
def convertToDateTime(datetimeStr):
    # example, datetimeStr = '2020-06-07T20:24:15+07:00'
    datetimeStr = datetimeStr.split('+')[0]
    datetimeObj = datetime.strptime(datetimeStr, '%Y-%m-%dT%H:%M:%S')
    timeSecs = (datetimeObj.time().hour*60 + datetimeObj.time().minute) * 60 + datetimeObj.time().second
    return [datetimeObj.date(), timeSecs]

def readPredictions(predictionsFilename, yyyy, mm, dd, selDirRoutes=[]):
    dfPredictions = pd.read_csv(predictionsFilename, names=mkList(predictionsCols), header=None, index_col=False)

    if len(selDirRoutes)!=0: # selects only a subset of dfPredictions for testing purposes
        dfPredictions['dirRoute'] = dfPredictions['RouteId'].astype(str) + '_' + dfPredictions['RouteVarId'].astype('str')
        dfPredictions = dfPredictions.loc[dfPredictions['dirRoute'].isin(selDirRoutes)]
        dfPredictions.drop(['dirRoute'], axis=1, inplace=True)

    dfPredictions['newLocTime'] = dfPredictions['LocTimeStamp'].apply(convertToDateTime)
    dfPredictions['LocDate'] = dfPredictions['newLocTime'].apply(lambda x: x[0])
    dfPredictions['LocTimeSecs'] = dfPredictions['newLocTime'].apply(lambda x: x[1])
    dfPredictions.drop(['newLocTime', 'Speed_kmph', 'TimeToStop_sec'], axis=1, inplace=True)

    reqDate = datetime.strptime('%s/%s/%s' % (yyyy, mm, dd), '%Y/%m/%d').date()
    dfPredThisDate = dfPredictions.loc[dfPredictions['LocDate'] == reqDate]
    dfPredThisDate.reset_index(drop=True, inplace=True)
    return dfPredThisDate

# ======================================================================================================================
def preprocessPredictions(dfPredictions, dfEndStopByDirRoute):
    '''
    checks if at least one requested stop of each directed route (in the prediction) is the end stop of that dir route.
    :param dfPredictions:
    :param dfEndStopByDirRoute:
    :return:
    '''
    dfPredictions['DirRoute'] = dfPredictions['RouteId'].astype(str) + '_' + dfPredictions['RouteVarId'].astype(str)
    dfPredictions['DirRouteVeh'] = dfPredictions['RouteId'].astype(str) + '_' + \
                                   dfPredictions['RouteVarId'].astype(str) + '_' + \
                                   dfPredictions['BusId']

    dfReqStopByDirRoute = dfPredictions.groupby(['DirRoute','BusId','StopId']).size().reset_index()#.rename(columns={0: 'count'})
    dfResult = pd.merge(dfReqStopByDirRoute, dfEndStopByDirRoute, on='DirRoute')
    dfResult.to_csv('./trashSite/reqStopByDirRouteVeh.csv', index=False)

# ======================================================================================================================
def getBounds(aSeries, method):
    '''
    :param aSeries: a pandas series
    :param method: '3Sigma', 'boxplot', or 'hampel'
    :return: [upperBound, lowerBound] of normal values in aSeries
    '''
    if method=='3Sigma':
        upperBnd = aSeries.mean() + 3 * aSeries.std()
        lowerBnd = aSeries.mean() - 3 * aSeries.std()
    elif method=='boxplot':
        [q1, q3] = aSeries.quantile([.25, .75]).values
        upperBnd = q3 + 1.5 * (q3 - q1)
        lowerBnd = q1 - 1.5 * (q3 - q1)
    elif method=='hampel':
        bSeries = abs(aSeries - aSeries.median())
        madm = 1.4826 * bSeries.median()
        upperBnd = aSeries.median() + 3 * madm
        lowerBnd = aSeries.median() - 3 * madm
    else:
        print('Method %s not recognised. Valid methods are 3Sigma, boxplot, or hampel')
        return None
    # idxOutliers = aSeries[(aSeries>upperBnd) | (aSeries<lowerBnd)].index
    # print('3-Sigma, upperBnd %.3f, lowerBnd %.3f' % (upperBnd,lowerBnd))
    # print(aSeries[idxOutliers])
    return [upperBnd, lowerBnd]

# ----------------------------------------------------------------------------------------------------------------------
def getIndicesOfTrips(dfPredDirRteVeh, dirRouteVeh, col2DetectTrips):
    trashFolder = './trashSite/predictionsHandler/getIndicesOfTrips'
    Path(trashFolder).mkdir(parents=True, exist_ok=True)
    # splits dfPredDirRteVeh into individual trips, i.e. the vehicle dirRouteVeh may make multiple trips a day
    # examplary dirRouteVeh are '41_81_51B32132', '41_81_51B32200'
    [uBndBoxp, lBndBoxp] = getBounds(dfPredDirRteVeh[col2DetectTrips], 'boxplot')
    [uBndHamp, lBndHamp] = getBounds(dfPredDirRteVeh[col2DetectTrips], 'hampel')
    [uBnd3Sig, lBnd3Sig] = getBounds(dfPredDirRteVeh[col2DetectTrips], '3Sigma')
    plotOutliers_dLocTimeSecs(dfPredDirRteVeh, col2DetectTrips, uBndBoxp, uBndHamp, uBnd3Sig,
                              '%s/%s_Outliers_%s.html' % (trashFolder, col2DetectTrips, dirRouteVeh))
    upperBnd = max(uBndBoxp, uBndHamp, uBnd3Sig)
    dfPredDirRteVeh.reset_index(drop=True, inplace=True)  # reset_index is required so that we can use iloc
    # with idxOutliers to split dfPredDirRteVeh
    idxOutliers = dfPredDirRteVeh[col2DetectTrips][(dfPredDirRteVeh[col2DetectTrips] > upperBnd)].index.values
    staIndices = [0] + idxOutliers.tolist()
    endIndices = idxOutliers.tolist() + [-1]
    return [staIndices, endIndices]

# ----------------------------------------------------------------------------------------------------------------------
def plotOutliers_dLocTimeSecs(dfPredDirRteVeh, col2DetectTrips, uBndBoxp, uBndHamp, uBnd3Sig, savefile):
    pBoxp = figure(plot_width=400, plot_height=400, title='outliers detection - Boxplot', toolbar_location='below')
    pHamp = figure(plot_width=400, plot_height=400, title='outliers detection - Hampel', toolbar_location='below')
    p3Sig = figure(plot_width=400, plot_height=400, title='outliers detection - 3Sigma', toolbar_location='below')
    for p,uBnd in zip([pBoxp, pHamp, p3Sig], [uBndBoxp, uBndHamp, uBnd3Sig]):
        norsIdx = dfPredDirRteVeh[col2DetectTrips][(dfPredDirRteVeh[col2DetectTrips] <= uBnd)].index
        outsIdx = dfPredDirRteVeh[col2DetectTrips][(dfPredDirRteVeh[col2DetectTrips] > uBnd)].index
        p.circle(dfPredDirRteVeh.loc[norsIdx]['LocTimeSecs'], dfPredDirRteVeh.loc[norsIdx][col2DetectTrips],
                     size=7, color='black')
        p.circle(dfPredDirRteVeh.loc[outsIdx]['LocTimeSecs'], dfPredDirRteVeh.loc[outsIdx][col2DetectTrips],
                     size=7, color='red')
        p.line([dfPredDirRteVeh['LocTimeSecs'].min(), dfPredDirRteVeh['LocTimeSecs'].max()], [uBnd, uBnd],
                   line_width=2, color='black', line_dash='dotted')

    rowPlots = row(pBoxp, pHamp, p3Sig)
    output_file(savefile)
    save(rowPlots)

# ----------------------------------------------------------------------------------------------------------------------
def smoothOutDistTimeLine(dfPredDirRteVeh, epsDistance):
    '''
    :param dfPredDirRteVeh:
    :param epsDistance: in metres, because values in dfPredDirRteVeh['Distance_m'] are in metres
    :return:
    '''
    arr = dfPredDirRteVeh[['LocTimeSecs', 'Distance_m']].to_numpy()
    maskOut = rdp(arr, epsilon=epsDistance, algo='iter', return_mask=True)
    arrOut = arr[maskOut]  # output of the RDP algorithm: smoothened travelled distance vs time of this bus
    tmpdf = pd.DataFrame(data={'LocTimeSecs': arrOut[:, 0], 'Distance_m': arrOut[:, 1]})
    # calculates slopes between consecutive data points on the smoothened distance-time curve
    tmpdf['Slope'] = (tmpdf['Distance_m'].shift(-1) - tmpdf['Distance_m']) / \
                     (tmpdf['LocTimeSecs'].shift(-1) - tmpdf['LocTimeSecs'])
    return tmpdf

# ----------------------------------------------------------------------------------------------------------------------
def constructScheduledTtb(dfTtbs, dfTtbTripsAll, dfRoutes, routeId, routeVarId, reqDate, pathLen):
    trashFolder = './trashSite/predictionsHandler/constructScheduledTtb'
    Path(trashFolder).mkdir(parents=True, exist_ok=True)

    def calcSchedTime(metresToEnd, staTimeSecs, endTimeSecs, pathLen):
        tripTime = endTimeSecs - staTimeSecs
        return round(staTimeSecs + (pathLen-metresToEnd) * tripTime / pathLen)

    # gets start time and end time of all trips in the day of dirRoute (via ttbId)
    ttbId = routeHandler.getTimetableId(dfTtbs, routeId, routeVarId, reqDate)
    dfTripSched = routeHandler.readStartEndTimes(dfTtbTripsAll, routeId, ttbId)
    dfTripSched.to_csv('%s/dfTripSched_%d_%d.csv' % (trashFolder, routeId, routeVarId), index=False)

    dfTtbSched = pd.DataFrame() # columns: 'StopId', 'DirRoute', 'Name', 'MetresToEnd', 'TripId', 'TimeSecs'
    for idx,row in dfTripSched.iterrows():
        staTimeSecs = row['StartTimeSecs']
        endTimeSecs = row['EndTimeSecs']
        dfTmp = dfRoutes[['StopId', 'DirRoute', 'Name', 'MetresFrStart']].loc[(dfRoutes['RouteId']==routeId) &
                                                                              (dfRoutes['RouteVarId']==routeVarId)]
        dfTmp['TripId'] = row['TripId']
        dfTmp['MetresToEnd'] = dfTmp['MetresFrStart'].apply(lambda x: pathLen - x)
        dfTmp['TimeSecs'] = dfTmp['MetresToEnd'].apply(lambda x: calcSchedTime(x, staTimeSecs, endTimeSecs, pathLen))
        dfTmp.drop(['MetresFrStart'], axis = 1, inplace=True)
        dfTtbSched = pd.concat([dfTtbSched, dfTmp])
    dfTtbSched.reset_index(drop=True, inplace=True)

    return dfTtbSched

# ----------------------------------------------------------------------------------------------------------------------
def constructAtualTtb_1Trip(dfTrip, dfRoutesSub, pathLen):
    trashFolder = './trashSite/predictionsHandler/constructAtualTtb_1Trip'
    Path(trashFolder).mkdir(parents=True, exist_ok=True)

    # columns of dfTrip[['Distance_m', 'LocTimeSecs', 'DirRouteVeh', 'tripNo']]
    def getIndex(metresToEnd, dfTrip):
        # appends metresToEnd to series Distance_m
        dist = dfTrip['Distance_m'].append(pd.Series([metresToEnd]))
        dist.sort_values(ascending=False, inplace=True)
        dist.reset_index(drop=True, inplace=True)
        # gets index of metresToEnd in the (sorted) series
        idx = dist.loc[dist == metresToEnd].index.values[0]
        return idx

    def calcLocTimeAtStop(metresToEnd, dfTrip):
        idx = getIndex(metresToEnd, dfTrip) # gets index of metresToEnd in the (sorted) series
        maxIdx = max(dfTrip.index) # maxIdx in dfTrip
        # if idx==0, metresToEnd is larger than the largest. if idx > maxIdx, metresToEnd is smaller than the smallest.
        # In both cases, the dfTrip does not cover the requested stop thus the time at the stop cannot be interpolated,
        # and gets value 1. (we don't want to extrapolate.)
        if idx == 0 or idx > maxIdx: return -1
        dt = (dfTrip.at[idx, 'LocTimeSecs'] - dfTrip.at[idx - 1, 'LocTimeSecs']) / \
             (dfTrip.at[idx - 1, 'Distance_m'] - dfTrip.at[idx, 'Distance_m']) * \
             (dfTrip.at[idx - 1, 'Distance_m'] - metresToEnd)
        return int(dfTrip.at[idx - 1, 'LocTimeSecs'] + dt)

    def calcLocTimeAt1stStop(metresToEnd2ndStop, timeAt2ndStop, pathLen, dfTrip):
        idx = getIndex(metresToEnd2ndStop, dfTrip) # gets index of metresToEnd in the (sorted) series
        # metresToEnd2ndStop is larger than the largest distance in dfTrip, i.e. no data point in dfTrip is between the
        # 1st and 2nd stops, we cannot calculate timeLoc for the 1st stop and return -1.
        if idx==0 or timeAt2ndStop==-1: return -1
        else:
            dfTripSubSmooth = smoothOutDistTimeLine(dfTrip.iloc[0:idx+1], epsDistance=20)
            avgSpd = dfTripSubSmooth['Slope'].loc[dfTripSubSmooth['Slope'].abs() > .1].mean()
            if math.isnan(avgSpd): return -1
            return int(timeAt2ndStop - (metresToEnd2ndStop - pathLen)/avgSpd)

    def calcLocTimeAtLastStop(mToEnd2ndLastStop, timeAt2ndLastStop, dfTrip):
        idx = getIndex(mToEnd2ndLastStop, dfTrip)
        maxIdx = max(dfTrip.index)
        if idx > maxIdx or timeAt2ndLastStop==-1: return -1
        else:
            dfTripSubSmooth = smoothOutDistTimeLine(dfTrip.iloc[idx-1:maxIdx+1], epsDistance=20)
            avgSpd = dfTripSubSmooth['Slope'].loc[dfTripSubSmooth['Slope'].abs() > .1].mean()
            if math.isnan(avgSpd): return -1
            return int(timeAt2ndLastStop - mToEnd2ndLastStop/avgSpd)

    dfRoutesSub.reset_index(drop=True, inplace=True)
    # calculates time at stop for all stops except the 1st stop and the last stop
    dfTmp = dfRoutesSub[['StopId', 'Name', 'MetresFrStart']]
    dfTmp['MetresToEnd'] = dfTmp['MetresFrStart'].apply(lambda x: pathLen - x)
    dfTmp['TimeSecs'] = dfTmp.iloc[1:len(dfRoutesSub) - 1]['MetresToEnd'].apply(lambda x: calcLocTimeAtStop(x, dfTrip))
    # calculates time at stop for 1st stop and at last stop
    dfTmp.at[0,'TimeSecs'] = calcLocTimeAt1stStop(dfTmp.at[1,'MetresToEnd'], dfTmp.at[1,'TimeSecs'], pathLen, dfTrip)
    dfTmp.at[len(dfRoutesSub) - 1, 'TimeSecs'] = calcLocTimeAtLastStop(
        dfTmp.at[len(dfRoutesSub) - 2,'MetresToEnd'], dfTmp.at[len(dfRoutesSub) - 2,'TimeSecs'], dfTrip)

    dfTmp.drop(['MetresFrStart'], axis = 1, inplace=True)
    dfTmp['DirRouteVeh'] = dfTrip.iloc[0]['DirRouteVeh']
    dfTmp['TripNo'] = dfTrip.iloc[0]['tripNo']

    #if dfTrip.iloc[0]['DirRouteVeh']=='4_8_50LD00596' and dfTrip.iloc[0]['tripNo']==5:
    #    print(dfTmp)

    return dfTmp # columns ['StopId', 'Name', 'MetresToEnd', 'TimeSecs', 'DirRouteVeh', 'TripNo']

# ----------------------------------------------------------------------------------------------------------------------
def plotLocDtaPntsToBokeh(dfRawLocPnts, dfSelLocPnts, dfTtbActual, dfDirRoute, dirRoute, pathLen):
    pRDP = figure(plot_width=1200, plot_height=800,  # x_axis_type="datetime",
                  title='Location data directed route %s' % dirRoute, toolbar_location='below')
    legendList = []
    for dirRouteVeh in dfRawLocPnts['DirRouteVeh'].unique():
        rawDirRouteVeh = dfRawLocPnts[dfRawLocPnts['DirRouteVeh'] == dirRouteVeh]

        #selDirRouteVeh = dfSelLocPnts[dfSelLocPnts['DirRouteVeh'] == dirRouteVeh]

        actTtbDirRouteVeh = pd.DataFrame()
        if dfTtbActual.shape[0] > 0:
            actTtbDirRouteVeh = dfTtbActual[dfTtbActual['DirRouteVeh'] == dirRouteVeh]

        elementsThisVeh = []
        for tripNo in rawDirRouteVeh['tripNo'].unique():
            rawTrip = rawDirRouteVeh[rawDirRouteVeh['tripNo'] == tripNo]
            rwDtaPnts = pRDP.circle(rawTrip['LocTimeSecs'], rawTrip['Distance_m'],
                                    line_color='red', size=4, alpha=.7)
            elementsThisVeh = elementsThisVeh + [rwDtaPnts]

            #selTrip = selDirRouteVeh[selDirRouteVeh['tripNo'] == tripNo]
            if dfSelLocPnts.shape[0]>0:
                selTrip = dfSelLocPnts[(dfSelLocPnts['DirRouteVeh'] == dirRouteVeh) &
                                       (dfSelLocPnts['tripNo'] == tripNo)]
                if selTrip.shape[0] > 0:
                    fiDtaPnts = pRDP.circle(selTrip['LocTimeSecs'], selTrip['Distance_m'], line_color='blue',
                                            size=4, alpha=.7)
                    # fiDtaLine = pRDP.line(selTrip['LocTimeSecs'], selTrip['Distance_m'], line_color='blue',
                    #                      line_width=1, alpha=.7)
                    elementsThisVeh = elementsThisVeh + [fiDtaPnts]  # , fiDtaLine]

            if actTtbDirRouteVeh.shape[0]>0:
                actTtbTrip = actTtbDirRouteVeh.loc[(actTtbDirRouteVeh['TripNo'] == tripNo) &
                                                   (actTtbDirRouteVeh['TimeSecs'] > -1)]
                if actTtbTrip.shape[0] > 0:
                    ttbDtaPnts = pRDP.square(actTtbTrip['TimeSecs'], actTtbTrip['MetresToEnd'], line_color='green',
                                             size=6, alpha=.7)
                    ttbDtaLine = pRDP.line(actTtbTrip['TimeSecs'], actTtbTrip['MetresToEnd'], line_color='green',
                                           line_width=2, alpha=.7, line_dash='dashed')
                    elementsThisVeh = elementsThisVeh + [ttbDtaPnts, ttbDtaLine]

        legendList.append((dirRouteVeh, elementsThisVeh))

    # plots pathLen and designed departure times
    minTime = dfDirRoute['LocTimeSecs'].min()
    maxTime = dfDirRoute['LocTimeSecs'].max()
    pRDP.line([minTime, maxTime], [pathLen, pathLen], line_width=1, color='black', alpha=.7, line_dash='dashed')

    #pRDP.legend.visible = False
    legend = Legend(items=legendList)
    legend.click_policy = 'hide'
    pRDP.add_layout(legend, 'right')
    #output_file('%s/locDtaPnts_%s.html' % (trashFolder, dirRoute))
    #save(pRDP)
    return pRDP

# ----------------------------------------------------------------------------------------------------------------------
def plotTtbsToBokeh(dfTtbMatched, dfTtbActual, dirRoute, pltTimeWindow=[]):
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

    p = figure(plot_width=2000, plot_height=1400, x_axis_type="datetime",
               title='Scheduled vs Actual Timetable Directed Route %s' % dirRoute, toolbar_location='below')

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

    return p

# ----------------------------------------------------------------------------------------------------------------------
def copyResultsToPkl(dfRawLocPnts, dfSelLocPnts, dfTtbSched, dfTtbActual, dfTtbMatched, pRDP, dateStr, dirRoute):
    pklPath = 'pkl/%s/dirRoutes/%s' % (dateStr, dirRoute)
    Path(pklPath).mkdir(parents=True, exist_ok=True)
    with open('%s/dfRawLocPnts_%s.pkl' % (pklPath, dirRoute), 'wb') as file:
        pickle.dump(dfRawLocPnts, file)
    with open('%s/dfSelLocPnts_%s.pkl' % (pklPath, dirRoute), 'wb') as file:
        pickle.dump(dfSelLocPnts, file)
    with open('%s/dfTtbSched_%s.pkl' % (pklPath, dirRoute), 'wb') as file:
        pickle.dump(dfTtbSched, file)
    with open('%s/dfTtbActual_%s.pkl' % (pklPath, dirRoute), 'wb') as file:
        pickle.dump(dfTtbActual, file)
    with open('%s/dfTtbMatched_%s.pkl' % (pklPath, dirRoute), 'wb') as file:
        pickle.dump(dfTtbMatched, file)

    csvPath = 'csv/%s/dirRoutes/%s' % (dateStr, dirRoute)
    Path(csvPath).mkdir(parents=True, exist_ok=True)
    dfRawLocPnts.to_csv('%s/dfRawLocPnts_%s.csv' % (csvPath, dirRoute), index=False)
    dfSelLocPnts.to_csv('%s/dfSelLocPnts_%s.csv' % (csvPath, dirRoute), index=False)
    dfTtbSched.to_csv('%s/dfTtbSched_%s.csv' % (csvPath, dirRoute), index=False)
    dfTtbActual.to_csv('%s/dfTtbActual_%s.csv' % (csvPath, dirRoute), index=False)
    dfTtbMatched.to_csv('%s/dfTtbMatched_%s.csv' % (csvPath, dirRoute), index=False)

    output_file('%s/locDtaPnts_%s.html' % (pklPath, dirRoute))
    save(pRDP)
    shutil.copy2('%s/locDtaPnts_%s.html' % (pklPath, dirRoute), '%s/locDtaPnts_%s.html' % (csvPath, dirRoute))

    '''
    output_file('%s/ttbSchedVsActual_%s.html' % (pklPath, dirRoute))
    save(pTTB)
    shutil.copy2('%s/ttbSchedVsActual_%s.html' % (pklPath, dirRoute),
                 '%s/ttbSchedVsActual_%s.html' % (csvPath, dirRoute))
    '''

# ----------------------------------------------------------------------------------------------------------------------
def matchTtbActualWithSched(dfTtbActual, dfTtbSched):
    trashFolder = './trashSite/predictionsHandler/matchTtbActualWithSched'
    Path(trashFolder).mkdir(parents=True, exist_ok=True)

    # dfTtbActual columns: ['StopId', 'DirRouteVeh', 'Name', 'MetresToEnd', 'TimeSecs', 'TripNo']
    # dfTtbSched columns: ['StopId', 'DirRoute', 'Name', 'MetresToEnd', 'TimeSecs', 'TripId']
    aStop = dfTtbSched.iloc[0]['StopId']
    aStopTimes = dfTtbSched.loc[dfTtbSched['StopId']==aStop]
    aStopTimes.sort_values(['TimeSecs'], inplace=True)
    schedTripIds = aStopTimes['TripId'].values.tolist()

    # if dfTtbActual has no rows, e.g. when no loc data points got passed the 2nd stop, do not match with scheduled ttb
    if dfTtbActual.shape[0]>0:
        dfTtbActual['DirRouteVehTripNo'] = dfTtbActual['DirRouteVeh'] + '_' + dfTtbActual['TripNo'].astype(str)

    dfTtbMatched = pd.DataFrame()
    usedTripNos = []
    for i in range(len(schedTripIds)): #for tripId in schedTripIds:
        tripId = schedTripIds[i]
        minAvgAbsDiffTimeSecs = -1
        matchingActualTripNo = 'na'
        selAvgDiffTimeSecs = 0
        if dfTtbActual.shape[0]>0: # if dfTtbActual has no rows, do not match with scheduled timetable
            availTripNos = list(set(dfTtbActual['DirRouteVehTripNo'].unique().tolist()) - set(usedTripNos))
            for tripNo in availTripNos:
                dfTtbActualSub = dfTtbActual.loc[dfTtbActual['DirRouteVehTripNo']==tripNo]
                dfTtbActualSub = dfTtbActualSub.iloc[1:len(dfTtbActualSub.index)-1] # removes the 1st and last stops
                actualTrip = dfTtbActualSub[['StopId', 'TimeSecs']].loc[dfTtbActualSub['TimeSecs']>-1]
                availStopIds = actualTrip['StopId'].unique().tolist()
                actualTrip.rename(columns={'TimeSecs': 'ActualTimeSecs'}, inplace=True)
                schedTrip = dfTtbSched[['StopId', 'TimeSecs']].loc[(dfTtbSched['TripId']==tripId) &
                                                                   (dfTtbSched['StopId'].isin(availStopIds))]
                schedTrip = schedTrip.merge(actualTrip, left_on='StopId', right_on='StopId')
                avgAbsDiffTimeSecs = (schedTrip['TimeSecs'] - schedTrip['ActualTimeSecs']).abs().mean()
                avgDiffTimeSecs = (schedTrip['ActualTimeSecs'] - schedTrip['TimeSecs']).mean()
                if minAvgAbsDiffTimeSecs==-1 or avgAbsDiffTimeSecs < minAvgAbsDiffTimeSecs:
                    minAvgAbsDiffTimeSecs = avgAbsDiffTimeSecs
                    matchingActualTripNo = tripNo
                    selAvgDiffTimeSecs = avgDiffTimeSecs

            if i < len(schedTripIds)-1:
                nxtTripId = schedTripIds[i+1]
                dtNxtSchedTrip = dfTtbSched['TimeSecs'].loc[(dfTtbSched['TripId']==nxtTripId) &
                                                            (dfTtbSched['StopId']==aStop)].values[0] - \
                                  dfTtbSched['TimeSecs'].loc[(dfTtbSched['TripId']==tripId) &
                                                            (dfTtbSched['StopId']==aStop)].values[0]
                if selAvgDiffTimeSecs > dtNxtSchedTrip: # if the gap between actual and current scheduled trip is large
                    # there's a chance that this actual trip matches better with the next scheduled trip.
                    # therefore we leave the current scheduled trip unmatched and move on to the next one.
                    matchingActualTripNo = 'na'

        dfTtbSchedSel = dfTtbSched.loc[dfTtbSched['TripId']==tripId]
        if matchingActualTripNo == 'na':
            dfTtbMatchedTmp = dfTtbSchedSel
            dfTtbMatchedTmp['ActualTimeSecs'] = -1
            dfTtbMatchedTmp['DirRouteVehTripNo'] = matchingActualTripNo
            dfTtbMatchedTmp['minAvgAbsTimeDiff'] = -1
        else:
            usedTripNos.append(matchingActualTripNo)
            dfTtbActualSel = dfTtbActual[['StopId', 'TimeSecs', 'DirRouteVehTripNo']].loc[
                dfTtbActual['DirRouteVehTripNo'] == matchingActualTripNo]
            dfTtbActualSel.rename(columns={'TimeSecs': 'ActualTimeSecs'}, inplace=True)
            dfTtbMatchedTmp = dfTtbSchedSel.merge(dfTtbActualSel, left_on='StopId', right_on='StopId')
            dfTtbMatchedTmp['minAvgAbsTimeDiff'] = minAvgAbsDiffTimeSecs
        dfTtbMatched = pd.concat([dfTtbMatched, dfTtbMatchedTmp])

    dfTtbMatched.reset_index(drop=True, inplace=True)

    actTripsAll = []
    if dfTtbActual.shape[0] > 0:
        actTripsAll = dfTtbActual['DirRouteVehTripNo'].unique().tolist()
    actTripsMatched = dfTtbMatched.loc[dfTtbMatched['DirRouteVehTripNo']!='na']['DirRouteVehTripNo'].unique().tolist()
    actTripsUnmatched = list(set(actTripsAll) - set(actTripsMatched))
    print('\t...%d/%d actual trips unmatched: ' % (len(actTripsUnmatched), len(actTripsAll)), actTripsUnmatched)

    schedTripsAll = dfTtbSched['TripId'].unique().tolist()
    schedTripsUnMatched = dfTtbMatched['TripId'].loc[dfTtbMatched['DirRouteVehTripNo']=='na'].unique().tolist()
    print('\t...%d/%d scheduled trips unmatched: ' % (len(schedTripsUnMatched),len(schedTripsAll)), schedTripsUnMatched)

    return dfTtbMatched

# ----------------------------------------------------------------------------------------------------------------------
def extractTripsFromPredictions(dfPredictions, dfEndStopByDirRoute, dfPaths, dfRoutes, dfTtbs, dfTtbTripsAll,
                                yyyy, mm, dd, selDirRoutes = [], ignoredDirRoutes=[]):
    trashFolder = './trashSite/predictionsHandler/extractTripsFromPredictions'
    Path(trashFolder).mkdir(parents=True, exist_ok=True)
    reqDate = datetime.strptime('%s/%s/%s' % (yyyy, mm, dd), '%Y/%m/%d').date()

    dfPredictions['DirRoute'] = dfPredictions['RouteId'].astype(str) + '_' + dfPredictions['RouteVarId'].astype(str)
    dfPredictions['DirRouteVeh'] = dfPredictions['RouteId'].astype(str) + '_' + \
                                   dfPredictions['RouteVarId'].astype(str) + '_' + \
                                   dfPredictions['BusId']

    print('nDirRoutes in dfPredictions %d' % len(dfPredictions['DirRoute'].unique().tolist()))
    print('len(ignoredDirRoutes) %d' % len(ignoredDirRoutes))

    dfEndStopByDirRoute.rename({'StopId': 'EndStopId'}, axis=1, inplace=True)
    dfPredictions = dfPredictions.merge(dfEndStopByDirRoute, left_on='DirRoute', right_on='DirRoute')

    if selDirRoutes: dirRoutes2Process = selDirRoutes
    else: dirRoutes2Process = dfPredictions['DirRoute'].unique().tolist()

    tik0 = time.time()
    countDirRoutes = 0
    processedDirRoutes = []
    for dirRoute in dirRoutes2Process:
        if dirRoute in ignoredDirRoutes: continue

        tik = time.time()
        [routeId,routeVarId] = dirRoute.split('_')
        routeId = int(routeId)
        routeVarId = int(routeVarId)

        # gets pathLen of this dirRoute
        pathLen = dfPaths['pathLen'].loc[(dfPaths['RouteId']==routeId) & (dfPaths['RouteVarId']==routeVarId)].values[0]
        # gets distance of the 2nd stop and of the 2nd last stop of this dirRoute
        dfRoutesSub = dfRoutes[dfRoutes['DirRoute'] == dirRoute]
        dfRoutesSub.reset_index(drop=True, inplace=True)
        #dfRoutesSub.to_csv('%s/dfRoutesSub_%s.csv' % (trashFolder, dirRoute))
        dist2ndStopFrStart = dfRoutesSub['MetresFrStart'].iloc[1]
        dist2ndLastStopFrStart = dfRoutesSub['MetresFrStart'].iloc[dfRoutesSub.shape[0]-2]
        print('dirRoute %s, pathLen %.3f, dist2ndStopFrStart %.3f, dist2ndLastStopFrStart %.3f ' %
              (dirRoute, pathLen, dist2ndStopFrStart, dist2ndLastStopFrStart))

        # calculates scheduled timetable (of all trips on reqDate) for this dirRoute
        dfTtbSched = constructScheduledTtb(dfTtbs, dfTtbTripsAll, dfRoutes, routeId, routeVarId, reqDate, pathLen)
        #dfTtbSched.to_csv('%s/dfTtbSched_%s.csv' % (trashFolder, dirRoute), index=False)

        # gets location data points of this dirRoute
        dfDirRoute = dfPredictions.loc[(dfPredictions['DirRoute'] == dirRoute)]

        # handles requested stop(s) that are not the end stop of this dirRoute
        # 1. removes those records of these mid-stops that duplicate with the end stop (i.e. having same LocTimeSecs)
        # 2. converts distance to the mid-stop(s) to the distance to the end-stop by adding the distance between these
        # and the end-stop.
        # 3. changes stopID of these mid-stops to the stopID of end-stop
        #dfDirRoute.to_csv('%s/dfDirRouteB4_%s.csv' % (trashFolder, dirRoute), index=False)
        dfDirRouteEndSt = dfDirRoute[dfDirRoute['StopId'] == dfDirRoute['EndStopId']]
        dfDirRouteMidSt = dfDirRoute[dfDirRoute['StopId'] != dfDirRoute['EndStopId']]
        #dfDirRouteEndSt.to_csv('%s/dfDirRouteEndSt_%s.csv' % (trashFolder, dirRoute), index=False)
        #dfDirRouteMidSt.to_csv('%s/dfDirRouteMidSt_%s.csv' % (trashFolder, dirRoute), index=False)
        uLocTimeSecsEndSt = dfDirRouteEndSt['LocTimeSecs'].unique()
        dfDirRouteMidSt = dfDirRouteMidSt.loc[~dfDirRouteMidSt['LocTimeSecs'].isin(uLocTimeSecsEndSt)]
        dfDirRouteMidSt['DistToEndSt'] = dfDirRouteMidSt['StopId'].\
            apply(lambda x: pathLen - dfRoutesSub['MetresFrStart'].loc[(dfRoutesSub['StopId']==x)].values[0])
        dfDirRouteMidSt['Distance_m'] = dfDirRouteMidSt['Distance_m'] + dfDirRouteMidSt['DistToEndSt']
        dfDirRouteMidSt['StopId'] = dfDirRouteMidSt['EndStopId']
        #dfDirRouteMidSt.to_csv('%s/dfDirRouteMidStAfter_%s.csv' % (trashFolder, dirRoute), index=False)
        dfDirRouteMidSt.drop(['DistToEndSt'], axis=1, inplace=True)
        dfDirRoute = pd.concat([dfDirRouteEndSt,dfDirRouteMidSt])
        dfDirRoute.sort_values(by=['LocTimeSecs'], inplace=True)
        #dfDirRoute.to_csv('%s/dfDirRouteAfter_%s.csv' % (trashFolder, dirRoute), index=False)

        dfRawLocPnts = pd.DataFrame()
        dfSelLocPnts = pd.DataFrame()
        dfTtbActual = pd.DataFrame()
        for dirRouteVeh in dfDirRoute['DirRouteVeh'].unique():
            dfPredDirRteVeh = dfDirRoute.loc[(dfDirRoute['DirRouteVeh'] == dirRouteVeh)]
            # calculates time difference and makes sure that LocTimeSecs increases monotonically
            dfPredDirRteVeh['dLocTimeSecs'] = dfPredDirRteVeh['LocTimeSecs'] - dfPredDirRteVeh['LocTimeSecs'].shift(1)
            dfPredDirRteVeh['dDistance_m'] = dfPredDirRteVeh['Distance_m'] - dfPredDirRteVeh['Distance_m'].shift(1)
            #dfPredDirRteVeh.to_csv('%s/%s_1.csv' % (trashFolder,dirRouteVeh), index=False)
            # removes rows where dLocTimeSecs is non-positive
            idxNonPostive = dfPredDirRteVeh[dfPredDirRteVeh['dLocTimeSecs'] <= 0].index
            dfPredDirRteVeh.drop(idxNonPostive, inplace=True)
            #dfPredDirRteVeh.to_csv('%s/%s_2.csv' % (trashFolder, dirRouteVeh), index=False)

            # there needs to be at least 3 rows in dfPredDirRteVeh, because minimum 2 rows are required for a trip and
            # at least 1 row to signifies the next trip.
            if dfPredDirRteVeh.shape[0] < 3: continue
            # gets start and end index of each trip in dfPredDirRteVeh. USE dDistance_m, DO NOT USE dLocTimeSecs
            [staIndices, endIndices] = getIndicesOfTrips(dfPredDirRteVeh, dirRouteVeh, col2DetectTrips='dDistance_m')

            countTr = 0
            for staIdx,endIdx in zip(staIndices, endIndices):
                # gets trip from dfPredDirRteVeh. iloc used here thanks to dfPredDirRteVeh.reset_index above.
                dfTrip = dfPredDirRteVeh.iloc[staIdx:endIdx]
                if dfTrip.shape[0] < 2: continue # if dfTrip has 1 or no rows, ignore it.
                dfTrip['tripNo'] = countTr
                dfTrip.reset_index(drop=True, inplace=True)
                #dfTrip.to_csv('%s/dfTrip_%s_%d.csv' % (trashFolder, dirRouteVeh, countTr))
                # adds the raw dfTrip to dfRawLocPnts for plotting for Bokeh later
                dfRawLocPnts = pd.concat([dfRawLocPnts, dfTrip[['Distance_m', 'LocTimeSecs', 'DirRouteVeh', 'tripNo']]])

                # STEP 0: if the last point of dfTrip didn't get pass the 2nd stop, ignore it
                if dfTrip['Distance_m'].iloc[-1] > (pathLen-dist2ndStopFrStart): continue

                # STEP 1: removes rows of dfTrip that have distance larger than pathLen
                dfTrip = dfTrip.loc[dfTrip['Distance_m']<=pathLen]
                dfTrip.reset_index(drop=True, inplace=True)

                # STEP 2: removes part of dfTrip before maxDist and after min(dfTrip['Distance_m'])
                maxDist = dfTrip['Distance_m'].max() # maxDist should now be <= pathLen
                idxMaxDist = dfTrip[dfTrip['Distance_m']==maxDist].index.values.tolist()
                idxMinDist = dfTrip[dfTrip['Distance_m']==dfTrip['Distance_m'].min()].index.values.tolist()
                # if the index of 1st occurrence of minDist is larger than the index of last maxDist, we can safely
                # assume that this part of dfTrip does not represent a genuine trip and can be ignored.
                # this is often the last records of the day logged by a vehicle when it stays at the bus yard but is
                # not going anywhere.
                if min(idxMinDist)<max(idxMaxDist): continue
                # keeps only the part of dfTrip between last occurrence of maxDistance & 1st occurrence of minDistance
                dfTrip = dfTrip.iloc[max(idxMaxDist):min(idxMinDist)+1]
                dfTrip.reset_index(drop=True, inplace=True)

                # STEP 4: removes Vs in dfTrip, i.e. distance drops then goes up
                for i in range(1, len(dfTrip.index) - 1):
                    # notes we can use 'at' instead of 'iloc' because of dfTrip.reset_index
                    if dfTrip.at[i, 'Distance_m'] < dfTrip.at[i + 1, 'Distance_m']:
                        if dfTrip.at[i + 1, 'Distance_m'] >= dfTrip.at[i - 1, 'Distance_m']:
                            dfTrip.at[i + 1, 'Distance_m'] = dfTrip.at[i - 1, 'Distance_m']
                            dfTrip.at[i, 'Distance_m'] = dfTrip.at[i - 1, 'Distance_m']
                        else:
                            dDist = (dfTrip.at[i - 1, 'Distance_m'] - dfTrip.at[i + 1, 'Distance_m']) / \
                                    (dfTrip.at[i + 1, 'LocTimeSecs'] - dfTrip.at[i - 1, 'LocTimeSecs']) * \
                                    (dfTrip.at[i, 'LocTimeSecs'] - dfTrip.at[i - 1, 'LocTimeSecs'])
                            dfTrip.at[i, 'Distance_m'] = dfTrip.at[i - 1, 'Distance_m'] - dDist

                # STEP 3: removes part of dfTrip near the end stop (e.g. after the 2nd last stop or the last 5% of the
                # pathLen) that drag on
                distNearTheEnd = pathLen * .05  #pathLen-dist2ndLastStopFrStart # or max of these two
                dfTripSub = dfTrip.loc[dfTrip['Distance_m'] < distNearTheEnd]
                dfTripSub.reset_index(drop=True, inplace=True)
                # smooths data points in dfTripSub to an error of 20 metres
                tmpdf = smoothOutDistTimeLine(dfTripSub, epsDistance=20)  # metres
                # gets smoothed data points that have absolute slope smaller than, say, .1 m/s and the other end of the
                # slope is at least 90 seconds away
                tmpdf['dTime'] = tmpdf['LocTimeSecs'].shift(-1) - tmpdf['LocTimeSecs']
                locTimeSecsHor = tmpdf['LocTimeSecs'].loc[(tmpdf['Slope'].abs() < .1) &
                                                          (tmpdf['dTime'] > 90)].values.tolist()
                # removes points in dfTrip starting from the point right after the 1st occurrence of locTimeSecsHor
                if locTimeSecsHor:
                    dfTrip.drop(dfTrip.loc[dfTrip['LocTimeSecs'] > min(locTimeSecsHor)].index, inplace=True)
                dfTrip.reset_index(drop=True, inplace=True)

                # STEP 5: adds this processed trip to dfSelLocPnts
                dfSelLocPnts = pd.concat([dfSelLocPnts, dfTrip[['Distance_m', 'LocTimeSecs', 'DirRouteVeh', 'tripNo']]])

                # STEP 6: calculates timetable for this trip based on dfTrip
                #print('dfRoutesSub')
                #print(dfRoutesSub)
                #print('dfTrip')
                #print(dfTrip)
                dfTmpTtb = constructAtualTtb_1Trip(dfTrip, dfRoutesSub, pathLen)
                dfTtbActual = pd.concat([dfTtbActual, dfTmpTtb])

                countTr += 1

        dfRawLocPnts.reset_index(drop=True, inplace=True)
        dfSelLocPnts.reset_index(drop=True, inplace=True)
        dfTtbActual.reset_index(drop=True, inplace=True)
        #columns['StopId', 'Name', 'MetresToEnd', 'TimeSecs', 'DirRouteVeh', 'TripNo']

        # matches each trip in dfTtbActual with a trip in dfTtbSched
        dfTtbMatched = matchTtbActualWithSched(dfTtbActual, dfTtbSched)

        # plots to Bokeh
        pRDP = plotLocDtaPntsToBokeh(dfRawLocPnts, dfSelLocPnts, dfTtbActual, dfDirRoute, dirRoute, pathLen)
        #pTTB = plotTtbsToBokeh(dfTtbMatched, dfTtbActual, dirRoute)

        # saves results
        copyResultsToPkl(dfRawLocPnts, dfSelLocPnts, dfTtbSched, dfTtbActual, dfTtbMatched, pRDP,
                         '%s_%s_%s' % (yyyy, mm, dd), dirRoute)

        print('\t...complete in %.3f seconds - totDataPoints %d, nVehs %d' %
              (time.time() - tik, dfDirRoute.shape[0], len(dfDirRoute['DirRouteVeh'].unique())))
        countDirRoutes +=1
        print('\tcomplete %d/%d dirRoutes in %.3f seconds' %
              (countDirRoutes, (len(dfPredictions['DirRoute'].unique().tolist()) - len(ignoredDirRoutes)),
               time.time() - tik0))
        processedDirRoutes.append(dirRoute)
        print('\tprocessedDirRoutes ', processedDirRoutes)
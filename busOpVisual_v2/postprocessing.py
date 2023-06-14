import math

import pandas as pd
import os
import pickle

import bokehPlotter
import dirRouteTimeGap

# ======================================================================================================================
def plotTripTimeDiff(dfTimeDiffDays):
    # gets path of the last date in dfTimeDiffDays
    lastDateStr = dfTimeDiffDays.loc[dfTimeDiffDays['date']==dfTimeDiffDays['date'].max()]['datestr'].unique()[0]
    with open('../../busOpAnalytics/myPy/pkl/%s/dfPaths.pkl' % (lastDateStr), 'rb') as f:
        dfPaths = pickle.load(f)
    # gets stops along directed routes, using dfRoutes of the last date in dfTimeDiffDays
    with open('../../busOpAnalytics/myPy/pkl/%s/dfRoutes.pkl' % (lastDateStr), 'rb') as f:
        dfRoutes = pickle.load(f)

    dfTimeDiffDays['minAvgAbsTimeDiff'] = dfTimeDiffDays['minAvgAbsTimeDiff'] / 60  # converts to minutes
    dfdtMeanDirRoutes = dirRouteTimeGap.preprocessTimeDiffs(dfTimeDiffDays)
    dfdtMeanDirRoutes.to_csv('dfdtMeanDirRoutes.csv', index=False)

    dirRouteTimeGap.plotRoutesToBaseMap(dfdtMeanDirRoutes, dfTimeDiffDays, dfPaths, dfRoutes,
                                        baseMap=dirRouteTimeGap.makeBaseMap())

    dirRouteTimeGap.plotTimeGapBubbleChart_v2(dfdtMeanDirRoutes, dfTimeDiffDays)


# ======================================================================================================================
def secs2HHMMSS(secs):
    hh = int(secs / 3600)
    mm = int((secs % 3600) / 60)
    ss = secs - hh*3600 - mm*60

    hhStr = '%d' % hh if hh>=10 else '0%d' % hh
    mmStr = '%d' % mm if mm>=10 else '0%d' % mm
    ssStr = '%d' % ss if ss >= 10 else '0%d' % ss
    return '%s:%s:%s' % (hhStr,mmStr,ssStr)

# ======================================================================================================================
def getBounds(aSeries, method):
    if method=='3Sigma':
        # calcs bounds using 3-sigma method
        upperBnd_3Sigma = aSeries.mean() + 3 * aSeries.std()
        lowerBnd_3Sigma = aSeries.mean() - 3 * aSeries.std()
        return [upperBnd_3Sigma, lowerBnd_3Sigma]
    elif method=='Boxplot':
        # calcs bounds using boxplot method
        [q1, q3] = aSeries.quantile([.25, .75]).values
        upperBnd_Boxplot = q3 + 1.5 * (q3 - q1)
        lowerBnd_Boxplot = q1 - 1.5 * (q3 - q1)
        return [upperBnd_Boxplot, lowerBnd_Boxplot]
    elif method=='Hampel':
        # calcs bounds using Hampel method
        bSeries = abs(aSeries - aSeries.median())
        madm = 1.4826 * bSeries.median()
        upperBnd_hampel = aSeries.median() + 3 * madm
        lowerBnd_hampel = aSeries.median() - 3 * madm
        return [upperBnd_hampel, lowerBnd_hampel]
    elif method=='all':
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
    else:
        print('invalid outlier detection method. Valid methods include Boxplot, 3Sigma, Hampel, all')
        return [math.nan, math.nan]

def getTimeDiffMatchedDirRoutes1Day(yyyy, mm, dd):
    dataPath1Day = '../../busOpAnalytics/myPy/csv/%s_%s_%s/dirRoutes' % (yyyy, mm, dd)
    # gets all folders, i.e. directed routes of this day
    subFolders = os.listdir(dataPath1Day)

    dfTimeDiff1Day = pd.DataFrame() # columns: DirRoute, minAvgAbsTimeDiff, date(datetime), DirRouteDesc
    countDirRoutes = 0
    for dirRoute in subFolders:
        dfTtbMatched = pd.read_csv('%s/%s/dfTtbMatched_%s.csv' % (dataPath1Day, dirRoute, dirRoute))

        # gets rows corresponding to matched actual trips, and thus having valid minAvgAbsTimeDiff values
        dfTimeDiff1DirRoute = dfTtbMatched[['DirRoute','minAvgAbsTimeDiff', 'TimeSecs']].loc[
            (dfTtbMatched['minAvgAbsTimeDiff']>0) & (dfTtbMatched['MetresToEnd']==dfTtbMatched['MetresToEnd'].max())]
        dfTimeDiff1DirRoute['datestr'] = '%s_%s_%s' % (yyyy,mm,dd)
        dfTimeDiff1DirRoute['date'] = pd.to_datetime(dfTimeDiff1DirRoute['datestr'], format='%Y_%m_%d')
        dfTimeDiff1DirRoute['timestr'] = dfTimeDiff1DirRoute['TimeSecs'].apply(lambda x:secs2HHMMSS(x))
        dfTimeDiff1DirRoute['time'] = pd.to_datetime(dfTimeDiff1DirRoute['timestr'], format = '%H:%M:%S')
        dfTimeDiff1DirRoute['nTripsSched1Day'] = len(dfTtbMatched['TripId'].unique().tolist())

        # gets records of the 1st (or of a random) trip
        aTripId = dfTtbMatched['TripId'].unique().tolist()[0]
        dfTtbMatchedSub = dfTtbMatched[(dfTtbMatched['TripId']==aTripId)]
        dfTtbMatchedSub.sort_values(by=['MetresToEnd'], ascending=False, inplace=True)
        dist2nd_2ndLastStops = dfTtbMatchedSub.iloc[1]['MetresToEnd'] - dfTtbMatchedSub.iloc[-2]['MetresToEnd']
        #if dirRoute=='1_1' or dirRoute=='2_1':
        #    print('dirRoute %s, aTripId %d, %.6f' % (dirRoute, aTripId, dist2nd_2ndLastStops))
        dfTimeDiff1DirRoute['dist2nd_2ndLastStops'] = dist2nd_2ndLastStops

        dfTimeDiff1Day = pd.concat([dfTimeDiff1Day, dfTimeDiff1DirRoute])

        #countDirRoutes += 1
        #if countDirRoutes==3: break

    #dfTimeDiff1Day.drop(['datestr'], axis=1, inplace=True)
    dfTimeDiff1Day.reset_index(drop=True, inplace=True)

    return dfTimeDiff1Day

# ======================================================================================================================
def getTimeDiffDays(dayDateDict):
    dfTimeDiffDays = pd.DataFrame()
    for day,dateStrs in dayDateDict.items():
        dfTimeDiff1Day = pd.DataFrame()
        for dateStr in dateStrs:
            dateParts = dateStr.split('/')
            dfTimeDiff1Date = getTimeDiffMatchedDirRoutes1Day(dateParts[2], dateParts[1], dateParts[0])
            dfTimeDiff1Date['day'] = day
            dfTimeDiff1Day = pd.concat([dfTimeDiff1Day, dfTimeDiff1Date])

        # removes outlier minAvgAbsTimeDiff for each directed route for 'day'
        dfTimeDiff1DayClean = pd.DataFrame()
        for dirRoute in dfTimeDiff1Day['DirRoute'].unique():
            dfDirRoute1Day = dfTimeDiff1Day[dfTimeDiff1Day['DirRoute']==dirRoute]
            [uBnd, lBnd] = getBounds(dfDirRoute1Day['minAvgAbsTimeDiff'], 'Boxplot')
            #if day=='Wednesday' and dirRoute=='125_2':
            #    print('%s, %s, %.3f' % (day, dirRoute, uBnd))
            dfDirRoute1Day = dfDirRoute1Day[dfDirRoute1Day['minAvgAbsTimeDiff'] < uBnd]
            dfTimeDiff1DayClean = pd.concat([dfTimeDiff1DayClean, dfDirRoute1Day])

        dfTimeDiffDays = pd.concat([dfTimeDiffDays, dfTimeDiff1DayClean])

    dfTimeDiffDays.reset_index(drop=True, inplace=True)
    # print(dfTimeDiffDays)
    return dfTimeDiffDays
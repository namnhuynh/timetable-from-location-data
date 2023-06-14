import pandas as pd
import os
import pickle
from pathlib import Path
import math

# ======================================================================================================================
def secs2HHMMSS(secs):
    hh = int(secs / 3600)
    mm = int((secs % 3600) / 60)
    ss = secs - hh*3600 - mm*60
    hhStr = '%d' % hh if hh>=10 else '0%d' % hh
    mmStr = '%d' % mm if mm>=10 else '0%d' % mm
    ssStr = '%d' % ss if ss >= 10 else '0%d' % ss
    return '%s:%s:%s' % (hhStr,mmStr,ssStr)

def concatHeadwaysForAltairPlots():
    # columns to keep in cleanActualHeadways:
    # StopId, DirRoute, ActualTimeSecs, dActualTimeSecs, datestr, day
    # columns to keep in schedActualHeadways
    # StopId, DirRoute, TimeSecs, dTimeSecs, datestr, day
    subFolders = os.listdir('./pkl/dirRoutes')
    dfHdwaySummaryAllRoutes = pd.DataFrame()
    for dirRoute in subFolders:
        pklFolderThisDirRoute = './pkl/dirRoutes/%s' % dirRoute
        dfActualHdway = pd.read_csv('%s/cleanActualHeadways.csv' % pklFolderThisDirRoute)
        dfSchedHdway = pd.read_csv('%s/cleanSchedHeadways.csv' % pklFolderThisDirRoute)
        dfActualHdway.drop(['TimeSecs'], axis=1, inplace=True)
        dfActualHdway.rename(columns={'ActualTimeSecs': 'TimeSecs', 'dActualTimeSecs': 'dTimeSecs'}, inplace=True)
        dfActualHdway['Type'] = 'Actual'
        dfSchedHdway['Type'] = 'Scheduled'
        dfActualHdway.reset_index(drop=True, inplace=True)
        dfSchedHdway.reset_index(drop=True, inplace=True)
        #dfActualHdway.to_csv('dfActualHdway_%s.csv' % (dirRoute))
        #dfSchedHdway.to_csv('dfSchedHdway_%s.csv' % (dirRoute))

        colUsed = ['StopId', 'DirRoute', 'TimeSecs', 'dTimeSecs', 'datestr', 'day', 'Type']
        dfActuSchedHdways = pd.concat([dfActualHdway[colUsed], dfSchedHdway[colUsed]])
        # converts datestr to date
        dfActuSchedHdways['date'] = pd.to_datetime(dfActuSchedHdways['datestr'], format='%d/%m/%Y')
        # converts TimeSecs to time
        dfActuSchedHdways['timestr'] = dfActuSchedHdways['TimeSecs'].apply(lambda x: secs2HHMMSS(x))
        dfActuSchedHdways['time'] = pd.to_datetime(dfActuSchedHdways['timestr'], format='%H:%M:%S')
        #converts dTimeSecs to minutes
        dfActuSchedHdways['dTimeSecs'] = dfActuSchedHdways['dTimeSecs'] / 60
        # resets index
        dfActuSchedHdways.reset_index(drop=True, inplace=True)

        dfActuSchedHdways.to_csv('%s/dfActuSchedHdwaysConcat.csv' % pklFolderThisDirRoute, index=False)

# ======================================================================================================================
def analyseHeadwaysForMapPlots():
    subFolders = os.listdir('./pkl/dirRoutes')
    dfHdwaySummaryAllRoutes = pd.DataFrame()
    for dirRoute in subFolders:
        pklFolderThisDirRoute = './pkl/dirRoutes/%s' % dirRoute
        dfActualHdway = pd.read_csv('%s/cleanActualHeadways.csv' % pklFolderThisDirRoute)
        dfSchedHdway = pd.read_csv('%s/cleanSchedHeadways.csv' % pklFolderThisDirRoute)

        dfActualHdway['stopDirRoute'] = dfActualHdway['StopId'].astype(str) + '_' + dfActualHdway['DirRoute']
        actuHdwayMed = dfActualHdway.groupby(by=['stopDirRoute'])['dActualTimeSecs'].median().to_frame()
        actuHdwayMed.reset_index(inplace=True)
        actuHdwayMed.rename(columns={'dActualTimeSecs': 'medActuHdway'}, inplace=True)
        actuHdwayAvg = dfActualHdway.groupby(by=['stopDirRoute'])['dActualTimeSecs'].mean().to_frame()
        actuHdwayAvg.reset_index(inplace=True)
        actuHdwayAvg.rename(columns={'dActualTimeSecs': 'avgActuHdway'}, inplace=True)
        actuHdwaySummary = actuHdwayMed.merge(actuHdwayAvg, on='stopDirRoute')

        dfSchedHdway['stopDirRoute'] = dfSchedHdway['StopId'].astype(str) + '_' + dfSchedHdway['DirRoute']
        schedHdwayMed = dfSchedHdway.groupby(by=['stopDirRoute'])['dTimeSecs'].median().to_frame()
        schedHdwayMed.reset_index(inplace=True)
        schedHdwayMed.rename(columns={'dTimeSecs': 'medSchedHdway'}, inplace=True)
        schedHdwayAvg = dfSchedHdway.groupby(by=['stopDirRoute'])['dTimeSecs'].mean().to_frame()
        schedHdwayAvg.reset_index(inplace=True)
        schedHdwayAvg.rename(columns={'dTimeSecs': 'avgSchedHdway'}, inplace=True)
        schedHdwaySummary = schedHdwayMed.merge(schedHdwayAvg, on='stopDirRoute')

        actuHdwaySummary = actuHdwaySummary.merge(schedHdwaySummary, on='stopDirRoute')

        tmpdf = dfActualHdway[['StopId', 'DirRoute', 'stopDirRoute', 'Name', 'routeDesc', 'Lat', 'Lng']].\
            drop_duplicates()
        actuHdwaySummary = actuHdwaySummary.merge(tmpdf, on='stopDirRoute')

        dfHdwaySummaryAllRoutes = pd.concat([dfHdwaySummaryAllRoutes, actuHdwaySummary])

    dfHdwaySummaryAllRoutes['dAbsAvgHdway'] = (dfHdwaySummaryAllRoutes['avgSchedHdway'] -
                                               dfHdwaySummaryAllRoutes['avgActuHdway']).abs()
    dfHdwaySummaryAllRoutes['dAbsMedHdway'] = (dfHdwaySummaryAllRoutes['medSchedHdway'] -
                                               dfHdwaySummaryAllRoutes['medActuHdway']).abs()
    dfHdwaySummaryAllRoutes.to_csv('./pkl/dfHdwaySummaryAllRoutes.csv', index=False)

    dfHdwaysSummaryByStop = pd.DataFrame()
    for stopId in dfHdwaySummaryAllRoutes['StopId'].unique():
        hdwaysSub = dfHdwaySummaryAllRoutes[dfHdwaySummaryAllRoutes['StopId']==stopId]
        hdwaysSub = hdwaysSub[hdwaysSub['dAbsMedHdway']==hdwaysSub['dAbsMedHdway'].max()]
        # or we can select max of average headway
        #hdwaysSub = hdwaysSub[hdwaysSub['dAbsMedHdway'] == hdwaysSub['dAbsMedHdway'].max()]
        dfHdwaysSummaryByStop = pd.concat([dfHdwaysSummaryByStop,hdwaysSub])
    dfHdwaysSummaryByStop.to_csv('./pkl/dfHdwaysSummaryByStop.csv', index=False)

# ======================================================================================================================
def cleanHeadways():
    '''
    removes records of 1st stop and of last stop and empty cells.
    also removes outliers in dActualTimeStopsAllDays
    :param dirRoute:
    :return:
    '''
    subFolders = os.listdir('./pkl/dirRoutes')
    for dirRoute in subFolders:
        pklFolderThisDirRoute = './pkl/dirRoutes/%s' % dirRoute
        dSchedTimeStopsAllDays = pd.read_csv('%s/dSchedTimeStopsAllDays.csv' % pklFolderThisDirRoute)
        dActualTimeStopsAllDays = pd.read_csv('%s/dActualTimeStopsAllDays.csv' % pklFolderThisDirRoute)

        # gets the last date in dfSchedTimeStopsAllDays
        dSchedTimeStopsAllDays['date'] = pd.to_datetime(dSchedTimeStopsAllDays['datestr'], format='%d/%m/%Y')
        lastDateStr = dSchedTimeStopsAllDays.loc[dSchedTimeStopsAllDays['date'] ==
                                                 dSchedTimeStopsAllDays['date'].max()]['datestr'].unique()[0]
        [dd, mm, yyyy] = lastDateStr.split('/')
        # gets dfRoutes of the last date
        with open('../../busOpAnalytics/myPy/pkl/%s_%s_%s/dfRoutes.pkl' % (yyyy, mm, dd), 'rb') as f:
            dfRoutes = pickle.load(f)

        # gets 1st stop and last stop of this dirRoute
        dfRouteSub = dfRoutes[['StopId','MetresFrStart','Name', 'Lat', 'Lng']].loc[dfRoutes['DirRoute']==dirRoute]
        dfRouteSub.sort_values(by=['MetresFrStart'], inplace=True)
        endStops = dfRouteSub.iloc[[0,-1]]['StopId']
        routeDesc = '%s -> %s' % (dfRouteSub.iloc[0]['Name'], dfRouteSub.iloc[-1]['Name'])

        # clean actual headways
        dActualTimeStopsAllDays = dActualTimeStopsAllDays.loc[(~dActualTimeStopsAllDays['StopId'].isin(endStops)) &
                                                              (dActualTimeStopsAllDays['dActualTimeSecs'] > 0)]
        # removes any outliers of dTime at each stop in dActualTimeStopsAllDays
        dActualTimeCleaned = pd.DataFrame()
        for stopId in dActualTimeStopsAllDays['StopId'].unique():
            dfActualTimesSub = dActualTimeStopsAllDays[dActualTimeStopsAllDays['StopId']==stopId]
            [uBnd, lBnd] = getBounds(dfActualTimesSub['dActualTimeSecs'], 'all') #'Boxplot'
            #print('stopId %d, uBnd %.3f' % (stopId, uBnd))
            dfActualTimesSub = dfActualTimesSub[dfActualTimesSub['dActualTimeSecs']<uBnd]
            dActualTimeCleaned = pd.concat([dActualTimeCleaned, dfActualTimesSub])

        # clean scheduled headways
        dSchedTimeCleaned = dSchedTimeStopsAllDays.loc[(~dSchedTimeStopsAllDays['StopId'].isin(endStops)) &
                                                            (dSchedTimeStopsAllDays['dTimeSecs'] > 0)]

        dActualTimeCleaned = dActualTimeCleaned.merge(dfRouteSub[['StopId', 'Lat', 'Lng']], on='StopId')
        dSchedTimeCleaned = dSchedTimeCleaned.merge(dfRouteSub[['StopId', 'Lat', 'Lng']], on='StopId')
        dActualTimeCleaned['routeDesc'] = routeDesc
        dSchedTimeCleaned['routeDesc'] = routeDesc

        dActualTimeCleaned.to_csv('%s/cleanActualHeadways.csv' % pklFolderThisDirRoute, index=False)
        dSchedTimeCleaned.to_csv('%s/cleanSchedHeadways.csv' % pklFolderThisDirRoute, index=False)

# ======================================================================================================================
def preprocessHeadwayDays(dayDateDict):
    '''
    :param dayDateDict:
    :return:
    '''
    '''
    for day, dates in dayDateDict.items():
        for dateStr in dates:
            [dd,mm,yyyy] = dateStr.split('/')
            preprocessHeadway1Day(yyyy, mm, dd)
    '''

    # for each dirRoute, consolidates data from different dates into 1 file
    subFolders = os.listdir('./pkl/dirRoutes')
    for dirRoute in subFolders:
        print('consolidating headway dirRoute %s' % (dirRoute))
        pklFolderThisDirRoute = './pkl/dirRoutes/%s' % dirRoute

        dSchedTimeStopsAllDays = pd.DataFrame()
        dActualTimeStopsAllDays = pd.DataFrame()
        for day, dates in dayDateDict.items():
            for dateStr in dates:
                [dd, mm, yyyy] = dateStr.split('/')
                dSchedTimeStopsPkl = '%s/dSchedTimeStops_%s_%s_%s.pkl' % (pklFolderThisDirRoute, yyyy, mm, dd)
                if os.path.exists(dSchedTimeStopsPkl):
                    with open(dSchedTimeStopsPkl, 'rb') as f:
                        tmpdf = pickle.load(f)
                        tmpdf['datestr'] = dateStr
                        tmpdf['day'] = day
                        dSchedTimeStopsAllDays = pd.concat([dSchedTimeStopsAllDays, tmpdf])
                dActualTimeStopsPkl = '%s/dActualTimeStops_%s_%s_%s.pkl' % (pklFolderThisDirRoute, yyyy, mm, dd)
                if os.path.exists(dActualTimeStopsPkl):
                    with open(dActualTimeStopsPkl, 'rb') as f:
                        tmpdf = pickle.load(f)
                        tmpdf['datestr'] = dateStr
                        tmpdf['day'] = day
                        dActualTimeStopsAllDays = pd.concat([dActualTimeStopsAllDays, tmpdf])

        dSchedTimeStopsAllDays.to_csv('%s/dSchedTimeStopsAllDays.csv' % pklFolderThisDirRoute, index=False)
        dActualTimeStopsAllDays.to_csv('%s/dActualTimeStopsAllDays.csv' % pklFolderThisDirRoute, index=False)

# ======================================================================================================================
def preprocessHeadway1Day(yyyy, mm, dd):
    dataPath1Day = '../../busOpAnalytics/myPy/csv/%s_%s_%s/dirRoutes' % (yyyy, mm, dd)
    subFolders = os.listdir(dataPath1Day)

    for dirRoute in subFolders:
        print('making headway dirRoute %s, %s/%s/%s' % (dirRoute, dd,mm,yyyy))
        pklPath = './pkl/dirRoutes/%s' % dirRoute
        Path(pklPath).mkdir(parents=True, exist_ok=True)

        dSchedTimeStopsPkl = '%s/dSchedTimeStops_%s_%s_%s.pkl' % (pklPath, yyyy, mm, dd)
        dActualTimeStopsPkl = '%s/dActualTimeStops_%s_%s_%s.pkl' % (pklPath, yyyy, mm, dd)
        if os.path.exists(dSchedTimeStopsPkl) and os.path.exists(dActualTimeStopsPkl):
            print('...existed!')
            continue

        dfTtbMatched = pd.read_csv('%s/%s/dfTtbMatched_%s.csv' % (dataPath1Day, dirRoute, dirRoute))

        dSchedTimeStops = pd.DataFrame()
        dActualTimeStops = pd.DataFrame()
        for stopId in dfTtbMatched['StopId'].unique():
            df1StopSchedTimes = dfTtbMatched[dfTtbMatched['StopId']==stopId]
            df1StopSchedTimes.sort_values(by=['TimeSecs'], ascending=True, inplace=True)
            df1StopSchedTimes['dTimeSecs'] = df1StopSchedTimes['TimeSecs'].shift(-1) - df1StopSchedTimes['TimeSecs']
            dSchedTimeStops = pd.concat([dSchedTimeStops, df1StopSchedTimes])

            df1StopActualTimes = dfTtbMatched[(dfTtbMatched['StopId']==stopId) & (dfTtbMatched['ActualTimeSecs']>=0)]
            df1StopActualTimes.sort_values(by=['ActualTimeSecs'], ascending=True, inplace=True)
            df1StopActualTimes['dActualTimeSecs'] = df1StopActualTimes['ActualTimeSecs'].shift(-1) - \
                                                    df1StopActualTimes['ActualTimeSecs']
            dActualTimeStops = pd.concat([dActualTimeStops,df1StopActualTimes])

        with open(dSchedTimeStopsPkl, 'wb') as f:
            pickle.dump(dSchedTimeStops, f)
        with open(dActualTimeStopsPkl, 'wb') as f:
            pickle.dump(dActualTimeStops, f)

        # for testing purposes
        if dirRoute=='2_1':
            dSchedTimeStops.to_csv('%s/dSchedTimeStops_%s_%s_%s.csv' % (pklPath, yyyy, mm, dd))
            dActualTimeStops.to_csv('%s/dActualTimeStops_%s_%s_%s.csv' % (pklPath, yyyy, mm, dd))

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

import pandas as pd
import constants as const
import json
from geopy.distance import distance
import time
from datetime import datetime
import math

def readTrips(jsonFile):
    tripJsonList = []
    with open(jsonFile) as f:
        for jsonObj in f:
            tripJsonList.append(json.loads(jsonObj))
    dfTripsFrJson = pd.DataFrame()
    for tripJsonObjs in tripJsonList:
        for obj in tripJsonObjs:
            df = pd.DataFrame(obj, index=[0])
            dfTripsFrJson = pd.concat([dfTripsFrJson, df])
    dfTripsFrJson.reset_index(inplace=True, drop=True)

    return dfTripsFrJson

def readStartEndTimes(dfTrips, tstRouteId, ttbId):
    dfTripsSub = dfTrips.loc[
        (dfTrips['RouteId'].astype(int) == tstRouteId) & (dfTrips['TimeTableId'].astype(int) == ttbId)]
    dfTripsSub['StartTimeSecs'] = dfTripsSub['StartTime'].apply(lambda x: convertHHMMToSecs(x))
    dfTripsSub['EndTimeSecs'] = dfTripsSub['EndTime'].apply(lambda x: convertHHMMToSecs(x))
    return dfTripsSub

def convertHHMMToSecs(hhmm):
    [hh,mm] = hhmm.split(':')
    return int(hh)*3600 + int(mm)*60

# ======================================================================================================================
def readTimetables(jsonFile):
    ttbJsonList = []
    with open(jsonFile) as f:
        for jsonObj in f:
            ttbJsonList.append(json.loads(jsonObj))

    dfTtbFrJson = pd.DataFrame()
    for ttbJsonObj in ttbJsonList:
        # ttbJsonObj is a list, each element of which is an element and has timetable information of a directed route
        # in a period.
        # All directed routes in ttbJsonObj belong to a route.
        for obj in ttbJsonObj:
            df = pd.DataFrame(obj, index=[0])
            dfTtbFrJson = pd.concat([dfTtbFrJson, df])

    dfTtbFrJson.reset_index(inplace=True, drop=True)

    # splits StartDate to 3 columns, dd, mm, yy
    dfTtbFrJson['StartDateObj'] = dfTtbFrJson['StartDate'].apply(lambda x: convert2datetime(x))
    dfTtbFrJson['EndDateObj'] = dfTtbFrJson['EndDate'].apply(lambda x: convert2datetime(x))

    return dfTtbFrJson

# ----------------------------------------------------------------------------------------------------------------------
def convert2datetime(strDate):
    # exapmle strDate = '27/01/2020'
    if (not strDate) or (len(strDate)==0):
        return datetime.strptime('01/01/2100', '%d/%m/%Y').date()
    return datetime.strptime(strDate, '%d/%m/%Y').date()

# ======================================================================================================================
def getTimetableId(dfTtbFrJson, routeId, routeVarId, reqDate):
    dfTtbDirRoute = dfTtbFrJson.loc[(dfTtbFrJson['RouteId']==routeId) &
                                    (dfTtbFrJson['RouteVarId']==routeVarId) &
                                    (dfTtbFrJson['StartDateObj']<reqDate) &
                                    (dfTtbFrJson['EndDateObj']>reqDate)]
    dfTtbDirRoute['dStartDate'] = reqDate - dfTtbDirRoute['StartDateObj']
    dfTtbDirRoute.reset_index(inplace=True, drop=True)

    iSelRow = dfTtbDirRoute[dfTtbDirRoute['dStartDate']==dfTtbDirRoute['dStartDate'].min()].index[0]
    #totalTrip = dfTtbDirRoute.at[iSelRow,'TotalTrip']
    #runTime = int(dfTtbDirRoute.at[iSelRow,'RunningTime'])
    timetableId = int(dfTtbDirRoute.at[iSelRow,'TimeTableId'])
    return timetableId

# ======================================================================================================================
def readPaths(jsonFile):
    raw = open(jsonFile)
    dfPaths = pd.DataFrame()

    pathsColList = [const.pathsCols.lat.name, const.pathsCols.lng.name,
                    const.pathsCols.RouteId.name, const.pathsCols.RouteVarId.name]

    for line in raw:
        jsonLine = json.loads(line)
        dfTmp = pd.DataFrame([[jsonLine[const.pathsCols.lat.name], jsonLine[const.pathsCols.lng.name],
                               jsonLine[const.pathsCols.RouteId.name], jsonLine[const.pathsCols.RouteVarId.name]]],
                             columns=pathsColList)
        pathLats = dfTmp['lat'].values.tolist()[0]
        pathLngs = dfTmp['lng'].values.tolist()[0]
        pathLen = 0
        for i in range(len(pathLats)-1):
            pathLen += distance([pathLats[i], pathLngs[i]], [pathLats[i+1], pathLngs[i+1]]).meters
        dfTmp['pathLen'] = pathLen
        dfPaths = pd.concat([dfPaths, dfTmp])

    dfPaths[const.pathsCols.RouteId.name] = dfPaths[const.pathsCols.RouteId.name].astype(int)
    dfPaths[const.pathsCols.RouteVarId.name] = dfPaths[const.pathsCols.RouteVarId.name].astype(int)

    dfPaths.reset_index(inplace=True, drop=True)
    return dfPaths

# ======================================================================================================================
def readStops(jsonFile):
    '''
    :param jsonFile:
    :return:
    '''
    raw = open(jsonFile)
    dfStops = pd.DataFrame()

    stopsColList = [const.stopsCols.StopsAttribs_StopId.value,
                    const.stopsCols.StopsAttribs_Code.value,
                    const.stopsCols.StopsAttribs_Lat.value,
                    const.stopsCols.StopsAttribs_Lng.value,
                    const.stopsCols.StopsAttribs_Name.value,
                    const.stopsCols.RouteId.value,
                    const.stopsCols.RouteVarId.value]

    for line in raw:
        jsonLine = json.loads(line)
        for stop in jsonLine['Stops']:
            dfTmp = pd.DataFrame([[stop['StopId'], stop['Code'], stop['Lat'], stop['Lng'], stop['Name'],
                                   jsonLine['RouteId'], jsonLine['RouteVarId']
                                   ]], columns=stopsColList)
            dfStops = pd.concat([dfStops, dfTmp])

    dfStops[const.stopsCols.RouteId.name] = dfStops[const.stopsCols.RouteId.name].astype(int)
    dfStops[const.stopsCols.RouteVarId.name] = dfStops[const.stopsCols.RouteVarId.name].astype(int)

    dfStops.reset_index(inplace=True, drop=True)
    return dfStops

# ======================================================================================================================
def calcDistAlongPath(pathLats, pathLngs, stopLat, stopLng):
    # calculates distance from stop to each point in path
    dists = [distance([stopLat,stopLng], [pathLats[i],pathLngs[i]]).meters for i in range(len(pathLats))]
    iPoint = dists.index(min(dists))

    distFrStart = 0
    for i in range(0,iPoint):
        distFrStart += distance([pathLats[i],pathLngs[i]], [pathLats[i+1],pathLngs[i+1]]).meters
    return [distFrStart, dists[iPoint]]

# ======================================================================================================================
def calcDistOfStops(dfStops, dfPaths):
    '''
    calculates
    :param dfStops:
    :param dfPaths:
    :return:
    '''
    dfStops['DirRoute'] = dfStops['RouteId'].astype(str) + '_' + dfStops['RouteVarId'].astype(str)
    dfPaths['DirRoute'] = dfPaths['RouteId'].astype(str) + '_' + dfPaths['RouteVarId'].astype(str)

    tik = time.time()
    dfRoutes = pd.DataFrame()
    count = 0
    for dirRoute in dfStops['DirRoute'].unique():
        dfStopsDirRoute = dfStops.loc[dfStops['DirRoute']==dirRoute]
        dfPathDirRoute = dfPaths.loc[dfPaths['DirRoute']==dirRoute]
        pathLats = dfPathDirRoute['lat'].values[0]
        pathLngs = dfPathDirRoute['lng'].values[0]
        if len(pathLngs)==0:
            dfStopsDirRoute['MetresFrStart'] = math.nan
            dfStopsDirRoute['MetresFrPathPnt'] = math.nan
        else:
            dfStopsDirRoute['Metres'] = dfStopsDirRoute.apply(
                lambda row: calcDistAlongPath(pathLats, pathLngs, row['Lat'], row['Lng']), axis=1)
            dfStopsDirRoute['MetresFrStart'] = dfStopsDirRoute['Metres'].apply(lambda x: x[0])
            dfStopsDirRoute['MetresFrPathPnt'] = dfStopsDirRoute['Metres'].apply(lambda x: x[1])
            dfStopsDirRoute.drop(columns=['Metres'], axis=1, inplace=True)
        dfRoutes = pd.concat([dfRoutes, dfStopsDirRoute])
        count += 1
        if count%10==0:
            print('complete %d dirRoute in %.3f secs' % (count, time.time()-tik))

    #dfRoutes.drop(columns=['Metres'], axis=1, inplace=True)
    dfRoutes.reset_index(inplace=True, drop=True)
    return dfRoutes

# ======================================================================================================================
def getLastStop(dfStops):
    dfStops['DirRoute'] = dfStops['RouteId'].astype(str) + '_' + dfStops['RouteVarId'].astype(str)
    dfEndStopOfDirRoutes = dfStops.groupby('DirRoute').tail(1)
    return dfEndStopOfDirRoutes[['DirRoute','StopId']]
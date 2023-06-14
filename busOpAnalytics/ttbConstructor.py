import time
import routeHandler
import predictionsHandler
from datetime import datetime
from pathlib import Path
import os
import pickle
import pandas as pd

# ======================================================================================================================
def constructTtb(dfRoutes, dfPredictions):
    dfPredictions['DirRoute'] = dfPredictions['RouteId'] + '_' + dfPredictions['RouteVarId']
    dfRoutes['DirRoute'] = dfRoutes['RouteId'] + '_' + dfRoutes['RouteVarId']
    for dirRoute in dfPredictions['DirRoute'].unique():
        if dirRoute not in dfRoutes['DirRoute'].unique():
            print('WARNING: dirRoute %s in dfPredictions but not in dfRoutes - ignored in constructTtb' % dirRoute)
            continue

# ======================================================================================================================
def main_ttbConstructor(yyyy, mm, dd):
    busInfoFolder = '../data/bus_info'
    busPredictionsFolder = '../data/bus_prediction'

    trashFolder = './trashSite/ttbConstructor/main_ttbConstructor'
    Path(trashFolder).mkdir(parents=True, exist_ok=True)
    pklFolder = './pkl/%s_%s_%s' % (yyyy, mm, dd)
    Path(pklFolder).mkdir(parents=True, exist_ok=True)
    csvFolder = './csv/%s_%s_%s' % (yyyy, mm, dd)
    Path(csvFolder).mkdir(parents=True, exist_ok=True)

    dfRoutesPkl = '%s/dfRoutes.pkl' % (pklFolder)
    dfRoutesCsv = '%s/dfRoutes.csv' % (csvFolder)
    dfPredictionsPkl = '%s/dfPredictions.pkl' % (pklFolder)
    dfPredictionsCsv = '%s/dfPredictions.csv' % (csvFolder)
    dfTripsPkl = '%s/dfTrips.pkl' % (pklFolder)
    dfTripsCsv = '%s/dfTrips.csv' % (csvFolder)
    dfTtbsPkl = '%s/dfTtbs.pkl' % (pklFolder)
    dfTtbsCsv = '%s/dfTtbs.csv' % (csvFolder)
    dfStopsPkl = '%s/dfStops.pkl' % (pklFolder)
    dfStopsCsv = '%s/dfStops.csv' % (csvFolder)
    dfPathsPkl = '%s/dfPaths.pkl' % (pklFolder)
    dfPathsCsv = '%s/dfPaths.csv' % (csvFolder)

    # ------------------------------------------------------------------------------------------------------------------
    # STEP 1: Read in information of bus routes, and calculate distance of stops to the first stop
    # ------------------------------------------------------------------------------------------------------------------
    tik = time.time()
    print('\nstart routeHandler.readPaths, creating dfPaths...')
    if os.path.exists(dfPathsPkl):
        with open(dfPathsPkl, 'rb') as file:
            dfPaths = pickle.load(file)
    else:
        dfPaths = routeHandler.readPaths('%s/%s/%s/%s/paths.json' % (busInfoFolder, yyyy, mm, dd))
        with open(dfPathsPkl, 'wb') as file:
            pickle.dump(dfPaths, file)
        dfPaths.to_csv(dfPathsCsv, index=False)
    #dfPathsSub = dfPaths.loc[(dfPaths['RouteId']==104) & (dfPaths['RouteVarId']==1)]
    print(dfPaths.dtypes)
    print(dfPaths.head())
    print('complete routeHandler.readPaths in %.3f secs' % (time.time()-tik))
    # ------------------------------------------------------------------------------------------------------------------
    tik = time.time()
    print('\nstart routeHandler.readStops, creating dfStops...')
    if os.path.exists(dfStopsPkl):
        with open(dfStopsPkl, 'rb') as file:
            dfStops = pickle.load(file)
    else:
        dfStops = routeHandler.readStops('%s/%s/%s/%s/stops.json' % (busInfoFolder, yyyy, mm, dd))
        with open(dfStopsPkl, 'wb') as file:
            pickle.dump(dfStops, file)
        dfStops.to_csv(dfStopsCsv, index=False)
    #dfStopsSub = dfStops.loc[(dfStops['RouteId']==104) & (dfStops['RouteVarId']==1)]
    print(dfStops.dtypes)
    print(dfStops.head())
    print('complete routeHandler.readStops in %.3f secs' % (time.time() - tik))
    # ------------------------------------------------------------------------------------------------------------------
    tik = time.time()
    print('\nstart routeHandler.calcDistOfStops, creating dfRoutes...')
    if os.path.exists(dfRoutesPkl):
        with open(dfRoutesPkl, 'rb') as file:
            dfRoutes = pickle.load(file)
    else:
        dfRoutes = routeHandler.calcDistOfStops(dfStops, dfPaths)
        with open(dfRoutesPkl, 'wb') as file:
            pickle.dump(dfRoutes, file)
        dfRoutes.to_csv(dfRoutesCsv, index=False)
    print(dfRoutes.dtypes)
    print(dfRoutes.head())
    print('complete routeHandler.calcDistOfStops in %.3f secs' % (time.time() - tik))
    # ------------------------------------------------------------------------------------------------------------------
    tik = time.time()
    print('\nstart routeHandler.getLastStop, creating dfEndStopByDirRoute...')
    dfEndStopByDirRoute = routeHandler.getLastStop(dfStops)
    print(dfEndStopByDirRoute.dtypes)
    print(dfEndStopByDirRoute.head())
    print('complete routeHandler.getLastStop in %.3f secs' % (time.time() - tik))
    # dfEndStopByDirRoute.to_csv('./trashSite/endStopOfDirRoutes.csv', index=False)
    # ------------------------------------------------------------------------------------------------------------------
    tik = time.time()
    print('\nstart routeHandler.readTimetables, creating dfTtbs...')
    if os.path.exists(dfTtbsPkl):
        with open(dfTtbsPkl, 'rb') as file:
            dfTtbs = pickle.load(file)
    else:
        dfTtbs = routeHandler.readTimetables('%s/%s/%s/%s/timetables.json' % (busInfoFolder, yyyy, mm, dd))
        with open(dfTtbsPkl, 'wb') as file:
            pickle.dump(dfTtbs, file)
        dfTtbs.to_csv(dfTtbsCsv, index=False)
    #dfTtbsSub = dfTtbs.loc[(dfTtbs['RouteId']==5) & (dfTtbs['RouteVarId']==1) & (dfTtbs['TimeTableId']==7)]
    print(dfTtbs.dtypes)
    print(dfTtbs.head())
    print('complete routeHandler.getTimetableId in %.3f secs' % (time.time() - tik))
    # ------------------------------------------------------------------------------------------------------------------
    #tstRouteId = 41
    #tstRouteVarId = 81
    #ttbId = routeHandler.getTimetableId(dfTtbs, tstRouteId, tstRouteVarId, reqDate)
    #print('test results: directed route %d_%d has ttbId %d' % (tstRouteId, tstRouteVarId, ttbId))
    # ------------------------------------------------------------------------------------------------------------------
    tik = time.time()
    print('\nstart routeHandler.readTrips, creating dfTrips...')
    if os.path.exists(dfTripsPkl):
        with open(dfTripsPkl, 'rb') as file:
            dfTrips = pickle.load(file)
    else:
        dfTrips = routeHandler.readTrips('%s/%s/%s/%s/trips.json' % (busInfoFolder, yyyy, mm, dd))
        with open(dfTripsPkl, 'wb') as file:
            pickle.dump(dfTrips, file)
        dfTrips.to_csv(dfTripsCsv, index=False)
    # dfTripsSub = routeHandler.readStartEndTimes(dfTrips, tstRouteId, ttbId)
    print(dfTrips.dtypes)
    print(dfTrips.head())
    print('complete routeHandler.readTrips in %.3f secs' % (time.time() - tik))

    # ------------------------------------------------------------------------------------------------------------------
    # STEP 2: read in location data of bus routes
    # ------------------------------------------------------------------------------------------------------------------
    tik = time.time()
    print('\nstart reading predictionsHandler.readPredictions, creating dfPredictions...')
    predictionsFilename = '%s/%s_%s_%s.csv' % (busPredictionsFolder, yyyy, mm, dd)
    #predictionsFilename = '../data/samplePredictions_2020_06_08_2DirRoutes.csv'
    if os.path.exists(dfPredictionsPkl):
        with open(dfPredictionsPkl, 'rb') as file:
            dfPredictions = pickle.load(file)
    else:
        selDirRoute = []
        dfPredictions = predictionsHandler.readPredictions(predictionsFilename, yyyy, mm, dd, selDirRoute)
        with open(dfPredictionsPkl, 'wb') as file:
            pickle.dump(dfPredictions, file)
        dfPredictions.to_csv(dfPredictionsCsv, index=False)
    print(dfPredictions.dtypes)
    print(dfPredictions.head())
    print('\ncomplete reading predictionsHandler.readPredictions in %.3f seconds' % (time.time() - tik))

    # ------------------------------------------------------------------------------------------------------------------
    #tik = time.time()
    #predictionsHandler.preprocessPredictions(dfPredictions, dfEndStopByDirRoute)
    #print('\ncomplete preprocessPredictions in %.3f seconds' % (time.time() - tik))
    # ------------------------------------------------------------------------------------------------------------------
    tik = time.time()
    print('\nstart predictionsHandler.extractTripsFromPredictions...')
    selDirRoutes = [] # '1_1', '4_8'
    # ignored directed routes that have only 2 stops, because these are either dedicated bus routes and likely not for
    # public use and/or having at least 1 stop outside of HCMC (e.g., '89_2' has 1 stop being Ben xe Binh Duong)
    nStopsByDirRoute = dfRoutes.groupby(['DirRoute']).size()
    ignoredDirRoutes = nStopsByDirRoute.loc[nStopsByDirRoute==2].index.values.tolist()
    # also ignores dirRoutes that have NaN in metresFrStart
    nanDirRoutes = dfRoutes['DirRoute'].loc[dfRoutes['MetresFrStart'].isna()].unique().tolist()
    ignoredDirRoutes = ignoredDirRoutes + nanDirRoutes
    predictionsHandler.extractTripsFromPredictions(dfPredictions, dfEndStopByDirRoute, dfPaths, dfRoutes, dfTtbs,
                                                   dfTrips, yyyy, mm, dd, selDirRoutes, ignoredDirRoutes)
    print('complete predictionsHandler.extractTripsFromPredictions in %.3f seconds' % (time.time() - tik))

    # ------------------------------------------------------------------------------------------------------------------
    # STEP 3: postprocessing timetable constructed from location data
    # ------------------------------------------------------------------------------------------------------------------

# ======================================================================================================================
# ======================================================================================================================
'''
import redis
def matchStopToPath():
    r = redis.Redis(host='localhost', port=6789, db=15)
    r.get('geometry:1_1')
    print(type(r))
    print(r)
'''
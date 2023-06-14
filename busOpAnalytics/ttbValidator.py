import pandas as pd
import time
from enum import Enum

ttbCols = ['ROUTEID', 'ROUTEVARID', 'BUSPREDIC', 'STOPID', 'DATEPREDIC', 'RANK', 'DAYOFWSTR', 'RANKATIME','TRIPSORDER'
           'TRIPSDELTAT', 'TIMEHOURSTR']

class predictionsCols(Enum):
    requestTime = 0
    stopID = 1
    routeID = 2
    routeVarID = 3
    busID = 4
    locTimeStamp = 5
    distance_m = 6
    speed_kmph = 7
    timeToStop_sec = 8

def mkList(myEnum):
    return [val.name for val in myEnum]

def validatingTtb(predictionsFilename, ttbFilename):
    '''
    :param filename:
    :return:
    '''
    tic = time.time()
    dfPredictions = pd.read_csv(predictionsFilename, names=mkList(predictionsCols), header=None, index_col=False)
    print('finish reading predictions in %.3f seconds' % (time.time() - tic))

    dfPredictions.drop(['speed_kmph', 'timeToStop_sec'], axis=1, inplace=True)

    reqRouteID = 1
    reqRouteVarID = 1
    dfPredictDirRoute = dfPredictions.loc[(dfPredictions['routeID']==reqRouteID) &
                                          (dfPredictions['routeVarID']==reqRouteVarID)]
    uBusIDs = dfPredictDirRoute['busID'].unique()

    print(uBusIDs.shape)
    countBuses = 0
    for uBus in uBusIDs:
        print(uBus)
        dfPredThisBus = dfPredictDirRoute.loc[dfPredictDirRoute['busID']==uBus]
        dfPredThisBus.to_csv('./trashSite/dfPred_%d_%d_%s.csv' % (reqRouteID, reqRouteVarID, uBus))
        countBuses += 1
        #if countBuses==1: break

    '''
    tic = time.time()
    dfTtb = pd.read_csv(ttbFilename)
    print('finish reading dfttb in %.3f seconds' % (time.time() - tic))
    print(dfTtb.shape)
    '''

    '''
    validation plan for a given day
    - for each directed route, gets all vehicles 
    - for each vehicle, 
    '''
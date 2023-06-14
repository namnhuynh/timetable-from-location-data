import pandas as pd
import time
from vega_datasets import data
import os

import postprocessing
import dirRouteTimeGap
import stopHeadway
import stopHeadwayPlotter
import ttbPlotter

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.options.mode.chained_assignment = None

if __name__=='__main__':
    dayDateDict = {'Monday':    ['18/05/2020', '25/05/2020',
                                 '01/06/2020', '08/06/2020', '15/06/2020', '22/06/2020', '29/06/2020'],
                   'Tuesday':   ['12/05/2020', '19/05/2020', '26/05/2020',
                                 '02/06/2020', '09/06/2020', '16/06/2020', '23/06/2020', '30/06/2020'],
                   'Wednesday': ['13/05/2020', '20/05/2020', '27/05/2020',
                                 '03/06/2020', '10/06/2020', '17/06/2020', '24/06/2020', '01/07/2020'],
                   'Thursday':  ['14/05/2020', '21/05/2020', '28/05/2020',
                                 '04/06/2020', '11/06/2020', '18/06/2020', '25/06/2020', '02/07/2020'],
                   'Friday':    ['15/05/2020', '22/05/2020', '29/05/2020',
                                 '05/06/2020', '12/06/2020', '19/06/2020', '26/06/2020', '03/07/2020']}

    '''
    dayDateDict = {'Monday':    ['01/06/2020'],
                   'Tuesday':   ['02/06/2020'],
                   'Wednesday': ['03/06/2020'],
                   'Thursday':  ['04/06/2020'],
                   'Friday':    ['05/06/2020']}
    '''

    '''
    dfTimeDiffDays = postprocessing.getTimeDiffDays(dayDateDict)
    dfTimeDiffDays.to_csv('dfTimeDiffDays.csv', index=False)
    postprocessing.plotTripTimeDiff(dfTimeDiffDays)
    '''

    '''
    tik = time.time()
    stopHeadway.preprocessHeadwayDays(dayDateDict)
    print('complete stopHeadway.preprocessHeadwayDays in %.3f secs' % (time.time() - tik))

    tik = time.time()
    stopHeadway.cleanHeadways()
    print('complete stopHeadway.cleanHeadways in %.3f secs' % (time.time() - tik))

    tik = time.time()
    stopHeadway.analyseHeadwaysForMapPlots()
    print('complete stopHeadway.analyseHeadwaysForMapPlots in %.3f secs' % (time.time() - tik))

    tik = time.time()
    stopHeadway.concatHeadwaysForAltairPlots()
    print('complete stopHeadway.concatHeadwaysForAltairPlots in %.3f secs' % (time.time() - tik))
    '''

    '''
    tik = time.time()
    ##stopHeadwayPlotter.plotStopHdwayToBaseMap()
    ##stopHeadwayPlotter.plotStopHdwayToBaseMap_v2()
    stopHeadwayPlotter.plotStopHdwayToBaseMap_v3()
    print('complete stopHeadway.plotStopHdwayToBaseMap_v3 in %.3f secs' % (time.time() - tik))
    '''

    '''
    tik = time.time()
    stopHeadwayPlotter.plotHdWayDetailstoBasemap()
    print('complete stopHeadway.plotHdWayDetailstoBasemap in %.3f secs' % (time.time() - tik))
    '''

    stopHeadwayPlotter.makeBubbleChart()

    '''
    dayDateDict = {'Monday':    ['18/05/2020', '25/05/2020'],
                   'Tuesday':   ['12/05/2020', '19/05/2020', '26/05/2020'],
                   'Wednesday': ['13/05/2020', '20/05/2020', '27/05/2020', '01/07/2020'],
                   'Thursday':  ['14/05/2020', '21/05/2020', '28/05/2020', '02/07/2020'],
                   'Friday':    ['15/05/2020', '22/05/2020', '29/05/2020', '03/07/2020']}
    ttbPlotter.plotTimetables(dayDateDict)
    '''

    print('yay')
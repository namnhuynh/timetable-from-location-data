import pandas as pd
import bokehPlotter
import os
from pathlib import Path

def plotTimetables(dayDateDict):
    for day, dates in dayDateDict.items():
        for dateStr in dates:
            [dd, mm, yyyy] = dateStr.split('/')
            dfRoutes = pd.read_csv('../../busOpAnalytics/myPy/csv/%s_%s_%s/dfRoutes.csv' % (yyyy, mm, dd))
            dataPath1Day = '../../busOpAnalytics/myPy/csv/%s_%s_%s/dirRoutes' % (yyyy, mm, dd)
            subFolders = os.listdir(dataPath1Day)
            for dirRoute in subFolders:
                print('%s, %s' % (dateStr, dirRoute))
                dfTtbMatched = pd.read_csv('%s/%s/dfTtbMatched_%s.csv' % (dataPath1Day, dirRoute, dirRoute))
                dfTtbActualFile = '%s/%s/dfTtbActual_%s.csv' % (dataPath1Day, dirRoute, dirRoute)
                if os.stat(dfTtbActualFile).st_size < 100: # if the file size is < 100 bytes, it's likely empty
                    continue
                else:
                    dfTtbActual = pd.read_csv(dfTtbActualFile)
                plotFolder = ('../plots/ttbs/%s' % dirRoute)
                Path(plotFolder).mkdir(parents=True, exist_ok=True)
                plotFilename = ('%s/ttbSchedVsActual_%s_%s_%s.html' % (plotFolder, yyyy, mm, dd))
                # gets route description
                df1Route = dfRoutes[dfRoutes['DirRoute']==dirRoute]
                df1Route.sort_values(by=['MetresFrStart'],inplace=True)
                routeDesc = '%s -> %s' % (df1Route.iloc[0]['Name'], df1Route.iloc[-1]['Name'])
                bokehPlotter.plotTtbsToBokeh(dfTtbMatched, dfTtbActual, dirRoute, routeDesc, plotFilename=plotFilename)

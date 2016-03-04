from boxofficemojo_scraper import *
import numpy as np

_fidToName = []
def _loadFid():
    global _fidToName
    s = Series.from_csv('boxoffice/'+film_index_name)
    _fidToName = Series(s.index, index=s.values)

def filmDict():
    global _fidToName
    if len(_fidToName) == 0:
        _loadFid()
    return _fidToName

def fidToName(fid):
    global _fidToName
    if len(_fidToName) == 0:
        _loadFid()
    return _fidToName[fid]

def findFilm(s):
    global _fidToName
    if len(_fidToName) == 0:
        s = Series.from_csv('boxoffice/'+film_index_name)
        _fidToName = Series(s.index, index=s.values)
    s = s.lower()
    result = []
    for fid, name in _fidToName.items():
        if name[:len(s)].lower() == s:
            result.append((name, fid))
    return result

def loadDailies(film):
    '''Load the dataframe for the given film from a file.'''
    try:
        df = DataFrame.from_csv('boxoffice/{}.csv'.format(film))
    except:
        df = downloadDailies(film)
        _loadFid()
    return df

def asSeries(df, name='', limit=0):
    '''Get the time series indexed by day of release.'''
    if 'Gross' not in df or 'Day #' not in df:
        print('{} has an empty dataframe'.format(name))
        return Series()
    series = Series(df['Gross'])
    series.index = df['Day #']
    if limit > 0:
        series = series[:limit]
    series.name = name
    return series

def similarDay(price, day, count=0, above=0):
    '''Get a set of films with the most similar gross revenues on the given day since release.'''
    series = Series()
    films = Series.from_csv('boxoffice/'+film_index_name)
    for film in films:
        s = asSeries(loadDailies(film))
        if s is not None and day in s and s[day] > above:
            series[film] = s[day]
    series = (abs(series - price)).sort_values(ascending=True)
    series /= 1000000
    if count > 0:
        return series[:count]
    return series

def formatter(x, pos):
    s = '{:0,d}'.format(int(x))
    return s

def similarCurves(film, count=1):
    '''Find the set of film grosses that most resemble the given film's daily gross time series.'''

def plotSimilarOpening(film, count=8, above=0):
    series = asSeries(loadDailies(film), film)
    similar = similarDay(series[1], 1, count, above)
    for fid, diff in similar.items():
        s = asSeries(loadDailies(fid), name=fidToName(fid), limit=28)
        if s is not None:
            try:
                s.cumsum().plot()
            except:
                print('Could not plot {}, mysteriously'.format(film))
    plt.legend(loc='upper left')
    ax = plt.gca()
    y_format = tkr.FuncFormatter(formatter)
    ax.yaxis.set_major_formatter(y_format)
    plt.title('Films with a similar opening day gross as {0} (${1}m)'.format(fidToName(film), int(series[1]/10000)/100))
    plt.show()

def predictGrossCurveCompoundMultiplication(series, day=28, multiplier=.83):
    '''Return a prediction of the grosses per day up until the specified day after release, given a series of daily grosses. Prediction works by
    starting with the opening day and gets the nth day by multiplying the
    (n-1)th by the multiplier.

    Best multiplier for a given day parameter:
    7:  .73
    14: .81
    28: .83
    56: .83
    '''
    daygross_model = series.iloc[0]
    predict = Series()
    #TODO: test if it's more efficient to build values in a list and then
    #instantiate series instead of modifying series values individually
    for i in range(1, day+1):
        predict.set_value(i, daygross_model)
        daygross_model = daygross_model * multiplier
    return predict

def predictionError(actual, predict, day=28):
    idx = min(min(len(actual),len(predict)), day)
    diff = (actual/1000000 - predict/1000000)**2
    return diff.sum()

def getErrorMatrix():
    matrix = Series()
    films = filmDict()
    for film in films.items():
        series = asSeries(loadDailies(film[0]))
        predict = predictGrossCurve(series, 28)
        matrix.set_value(film[1], predictionError(series, predict))
    return matrix

def evaluateModelWithParamRange(start, end, step, days=28):
    matrix = Series()
    films = filmDict()
    series_list = []
    for film in films.items():
        series = asSeries(loadDailies(film[0]))
        series_list.append((film[0],series))
    scores = Series()
    for param in np.arange(start,end,step):
        matrix = Series()
        for film,series in series_list:
            predict = predictGrossCurveCompoundMultiplication(series, days, param)
            matrix.set_value(film, predictionError(series, predict, days))
        scores.set_value(str(param), matrix.sum())
        print(str(param), matrix.sum())
    return scores

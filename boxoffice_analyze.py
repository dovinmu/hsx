from boxofficemojo_scraper import *
import numpy as np
import pandas as pd

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
        series = Series.from_csv('boxoffice/'+film_index_name)
        _fidToName = Series(series.index, index=series.values)
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
    #clean any data in need of cleaning
    if df.empty:
        return df
    if df['Theaters'].dtype != 'int64':
        df['Theaters'] = df['Theaters'].map(lambda x: x.replace(',',''))
        df['Theaters'] = df['Theaters'].astype('int64')
    if df['Rank'].dtype != 'float64' and df['Rank'].dtype != 'int64':
        df['Rank'] = df['Rank'].map(lambda x: float(x.replace('-','nan')))
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


def plotPredictionAndActual(filmid, day=28, plot='daily', constrain_input=7):
    '''
    Uses the per-day decay model to predict film grosses.

    filmid: The internal film ID from Box Office Mojo
    day: number of days from release to be predicted
    plot: Used to specify if the models should compare daily grosses or cumulative gross sums.
    constrain_input: used to artificially limit input variables even if the data exists

    Note: doesn't factor in limited-to-wide releases.
    '''
    df = loadDailies(filmid)
    filmname = fidToName(filmid)
    actual = df['Gross']
    predicted = predictDecayByDay(df,day_limit=day,index='integer', constrain_input=constrain_input)

    if plot=='cumsum':
        actual[:day].cumsum().plot(label='Gross')
        predicted.cumsum().plot(label='Predicted gross')
        plt.legend(loc='upper left')
    elif plot=='daily':
        actual[:day].plot(label='Gross')
        predicted.plot(label='Predicted gross')
        plt.legend(loc='upper right')
    ax = plt.gca()
    y_format = tkr.FuncFormatter(formatter)
    ax.yaxis.set_major_formatter(y_format)
    msError = meanSquaredError(actual, predicted, day)
    cumError = int(cumsumOffset(actual, predicted)/10000)/100
    plt.title('"{0}" ({1}) daily gross prediction. \nM.S. Error: {2}  Cum Error: {3}m'.format(filmname, filmid, str(int(msError*10)/10), cumError))
    plt.show()

def predictDayFromDay(actual, value, predict):
    '''
    Predict the gross for a film on the given day given the value of another day's gross.
    actual: the day of the week (e.g., 'Fri') the film grossed $value
    value: the gross of the film on day actual (e.g., the first Friday)
    predict: The day of the week to predict (e.g., 'Sat')

    NOTE: this is rudimentary until I calculate a data-centric first-week curve.
    '''
    weekday = ['Mon', 'Tue', 'Wed', 'Thu']
    weekend = ['Fri', 'Sat', 'Sun']
    if actual in weekend and predict in weekend:
        return value
    if actual in weekday and predict in weekday:
        return value
    if actual in weekday and predict in weekend:
        return value*5
    if actual in weekend and predict in weekday:
        return value/5
    return -1

def extrapolateFirstWeek(df, limit=7):
    week = Series(index=['Fri','Sat','Sun','Mon','Tue','Wed','Thu'])
    for i in range(min(len(df),limit)):
        day = df.iloc[i].Day
        week[day] = df.iloc[i].Gross
    comparison_day = None
    for day in week.items():
        if not np.isnan(day[1]):
            comparison_day = day
            break
    for day in week.items():
        if np.isnan(week[day[0]]):
            predict = predictDayFromDay(comparison_day[0], comparison_day[1], day[0])
            week[day[0]] = predict
    return week

def predictCompoundMultiplication(series, day=28, multiplier=.83):
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

def decayProgression(df, plot=True):
    '''
    Get a series with the average weekly drop in gross sales, by day of the week, of the given film.
    '''
    result = Series()
    for day in ['Fri', 'Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu']:
        if day in df['Day'].values:
            if plot:
                df[df['Day']==day]['% Change Prev Week'].plot(label=day)
            result.set_value(day, df[df['Day']==day]['% Change Prev Week'][1:].mean())
    if plot:
        plt.legend()
        plt.show()
    return result

def skipLimitedRun(df):
    '''
    Get a dataframe that begins with the film's wide release (if it had one).
    The definition of a wide release is 600 or more theaters.
    '''
    #print(df['Theaters'].unique())
    if len(df[df['Theaters'] >= 600]) > 0:
        ts = df[df['Theaters'] >= 600].index[0]
        return df[ts.to_datetime():]
    return df

def predictDecayByDay(df, day_limit=28, index='integer', constrain_input=7):
    '''Return a prediction of the grosses per day up until the specified day after release, given a series of daily grosses. Prediction works by
    applying a precomputed decay rate for each day of the week. If no data
    exists for the first day of the week, then that data is also estimated.

    day: number of days from release to be predicted
    index: what to index the returned time series with
    constrain_input: used to artificially limit input variables even if the data exists
    '''
    prevWeek = None
    currWeek = extrapolateFirstWeek(df, constrain_input)

    series = asSeries(df)
    #these values were calculated from the top ~180 films from 2015
    avg_percent_drop = Series([37, 33, 30, 21, 34, 34, 34], index=['Fri', 'Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu'])
    predict = Series()
    dayCount = 1
    for weeknum in range(1, int(day_limit/7) +1):
        for i in range(7):
            day = currWeek.index[i]
            drop_percent = avg_percent_drop[day]
            if prevWeek is not None: #don't apply this formula to first week
                prediction = prevWeek[i] - prevWeek[i] * drop_percent/100
            else:
                prediction = currWeek[i]
            currWeek[day] = prediction
            if index=='day-of-week':
                predict.set_value(day + ' ' + str(weeknum), prediction)
            elif index=='integer':
                predict.set_value(dayCount, prediction)
                dayCount += 1
        prevWeek = currWeek
    return predict

def meanSquaredError(actual, predict, day=28):
    '''
    Get the Mean Squared Error for day 1 through n (or the length of the shorter series, whichever is smaller), denoted in millions.
    '''
    idx = min(min(len(actual),len(predict)), day)
    diff = (actual[:idx]/1000000 - predict[:idx]/1000000)**2
    return diff.sum() / idx

def cumsumOffset(actual, predict, limit=28):
    return predict[:len(actual[:limit])].sum() - actual[:limit].sum()

def getErrorMatrix():
    matrix = Series()
    films = filmDict()
    for film in films.items():
        df = loadDailies(film[0])
        actual = asSeries(df)
        predict = predictDecayByDay(df, 28)
        matrix.set_value(film[1], meanSquaredError(actual, predict))
    return matrix

def getCumsumOffsetMatrix(day=28):
    matrix = Series()
    films = filmDict()
    for film in films.items():
        df = loadDailies(film[0])
        actual = asSeries(df)
        predict = predictDecayByDay(df, day)
        cumError = int((cumsumOffset(actual, predict)) /10000)/100
        matrix.set_value(film[1], cumError)
    return matrix

def cumsumOffsetSweep(filmid, day=28):
    df = loadDailies(filmid)
    filmname = fidToName(filmid)
    actual = df['Gross']
    result = Series()
    for i in range(1,8):
        predict = predictDecayByDay(df,day_limit=day,index='integer', constrain_input=i)
        result.set_value(i, cumsumOffset(actual, predict, day))
    return result

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
            predict = predictCompoundMultiplication(series, days, param)
            matrix.set_value(film, meanSquaredError(series, predict, days))
        scores.set_value(str(param), matrix.sum())
        print(str(param), matrix.sum())
    return scores

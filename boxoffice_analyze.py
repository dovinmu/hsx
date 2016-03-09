from boxofficemojo_scraper import *
import numpy as np
import pandas as pd

_nameToFid = []
_fidToName = []
def _loadFid():
    global _fidToName
    global _nameToFid
    s = Series.from_csv('boxoffice/'+film_index_name)
    _fidToName = Series(s.index, index=s.values)
    _nameToFid = s

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

def nameToFid(name):
    global _nameToFid
    if len(_nameToFid) == 0:
        _loadFid()
    return _nameToFid[name]

def findFilm(s=''):
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

def loadDailies(film,skipLimited=True):
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
    if df['Day #'].dtype != 'int64':
        df['Day #'] = df['Day #'].astype('int')
    if skipLimited:
        df = skipLimitedRun(df)
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

def plotSimilarOpening(film, count=8, above=0, plot='daily'):
    series = asSeries(loadDailies(film), film)
    similar = similarDay(series[1], 1, count, above)
    for fid, diff in similar.items():
        s = asSeries(loadDailies(fid), name=fidToName(fid), limit=28)
        if s is not None:
            try:
                if plot=='daily':
                    s.plot()
                elif plot=='cumsum':
                    s.cumsum().plot()
            except:
                print('Could not plot {}, mysteriously'.format(film))
    if plot=='daily':
        plt.legend(loc='upper right')
    elif plot=='cumsum':
        plt.legend(loc='upper left')
    ax = plt.gca()
    y_format = tkr.FuncFormatter(formatter)
    ax.yaxis.set_major_formatter(y_format)
    plt.title('Films with a similar opening day gross as {0} (${1}m)'.format(fidToName(film), int(series[1]/10000)/100))
    plt.show()

def plotFilms(films, plot='daily', days=28):
    for film in films:
        if film in _fidToName:
            filmname = fidToName(film)
        else:
            filmname = film
            film = nameToFid(film)
        df = loadDailies(film)
        series = asSeries(df, filmname)
        if plot=='daily':
            series[:days].plot()
        elif plot=='cumsum':
            series[:days].cumsum().plot()
    if plot=='daily':
        plt.legend(loc='upper right')
    elif plot=='cumsum':
        plt.legend(loc='upper left')
    ax = plt.gca()
    y_format = tkr.FuncFormatter(formatter)
    ax.yaxis.set_major_formatter(y_format)
    plt.title('Box office gross in first {} days'.format(days))
    plt.show()

def plotPredictionAndActual(filmid, day=28, plot='daily', limit_day_input=[7]):
    '''
    Uses the per-day decay model to predict film grosses.

    filmid: The internal film ID from Box Office Mojo
    day: number of days from release to be predicted
    plot: Used to specify if the models should compare daily grosses or cumulative gross sums.
    constrain_input: used to artificially limit input variables even if the data exists
    '''
    df = loadDailies(filmid)
    if df.empty:
        return
    df = skipLimitedRun(df)
    filmname = fidToName(filmid)
    actual = df['Gross']

    predicted_curves = {}
    for constrained_param in limit_day_input:
        predicted = predictDecayByDay(df,day_limit=day,index='integer', constrain_input=constrained_param)
        predicted_curves[constrained_param] = predicted

    if plot=='cumsum':
        actual[:day].cumsum().plot(label='Gross')
        for i,predicted in predicted_curves.items():
            label = 'day 1'
            if i > 1:
                label = 'days 1-' + str(i)
            cumError = int(cumsumOffset(actual, predicted)/10000)/100
            predicted.cumsum().plot(label='Input: {0}, Err: {1}m'.format(label, cumError), style='--')
        plt.legend(loc='upper left')
    elif plot=='daily':
        actual[:day].plot(label='Gross')
        for i,predicted in predicted_curves.items():
            label = 'day 1'
            if i > 1:
                label = 'days 1-' + str(i)
            msError = int(meanSquaredError(actual, predicted, day)*100)/100
            predicted.plot(label='Input: {0}, Err: {1}'.format(label, msError),style='--')
        plt.legend(loc='upper right')
    ax = plt.gca()
    y_format = tkr.FuncFormatter(formatter)
    ax.yaxis.set_major_formatter(y_format)
    if plot=='cumsum':
        error_text = 'Difference between predicted and gross revenue at day {}.'.format(day)
    elif plot=='daily':
        error_text = 'Mean squared error over the time frame.'
    plt.title('"{0}" ({1}) daily gross prediction.\nErr: {2}'.format(filmname, filmid, error_text))
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

def predictDecayByDay(df, day_limit=28, index='integer', constrain_input=7, override_percent_drop=None):
    '''Return a prediction of the grosses per day up until the specified day after release, given a series of daily grosses. Prediction works by
    applying a precomputed decay rate for each day of the week. If no data
    exists for the first day of the week, then that data is also estimated.

    day: number of days from release to be predicted
    index: what to index the returned time series with
    constrain_input: used to artificially limit input variables even if the data exists
    '''
    if df.empty:
        return Series()
    prevWeek = None
    currWeek = extrapolateFirstWeek(df, constrain_input)
    series = asSeries(df)
    if override_percent_drop:
        avg_percent_drop = Series(override_percent_drop, index=['Fri', 'Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu'])
    else:
        #value calculated to minimize error over the current dataset
        avg_percent_drop = Series([45], index=['Fri', 'Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu'])
    predict = Series()
    dayCount = df.iloc[0]['Day #']
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
    return cumsumGross(predict, limit) - cumsumGross(actual, limit)

def cumsumGross(series, limit=28):
    return series.iloc[:limit].sum()

def cumsumOffsetPercent(actual, predict, limit=28):
    '''Get the cumulative amount the model's off as a percent of total revenue.'''
    cumsum = cumsumOffset(actual, predict, limit)
    return int((cumsum / cumsumGross(actual, limit))*100)

def getErrorMatrix():
    matrix = Series()
    films = filmDict()
    for film in films.items():
        df = loadDailies(film[0])
        actual = asSeries(df)
        predict = predictDecayByDay(df, 28)
        matrix.set_value(film[1], meanSquaredError(actual, predict))
    return matrix

def getCumsumOffsetMatrix(day=28, percent=True):
    matrix_df = DataFrame()
    films = filmDict()
    for film in films.items():
        #print(film)
        df = loadDailies(film[0])
        if df.empty or len(df) < day:
            continue
        actual = asSeries(df)
        predict = predictDecayByDay(df, day)
        if percent:
            cumError = cumsumOffsetPercent(actual, predict, limit=day)
        else:
            cumError = int((cumsumOffset(actual, predict)) /10000)/100
        matrix_df.set_value(film[1], 'cumError', cumError)
        matrix_df.set_value(film[1], 'fid', film[0])
        matrix_df.set_value(film[1], 'gross', cumsumGross(actual, day))
    return matrix_df

def cumsumOffsetSweep(filmid, day=28):
    df = loadDailies(filmid)
    filmname = fidToName(filmid)
    actual = asSeries(df)
    result = Series()
    for i in range(1,8):
        predict = predictDecayByDay(df,day_limit=day,index='integer', constrain_input=i)
        result.set_value(i, cumsumOffset(actual, predict, day))
    return result

def totalCumsumOffsetErrorParams(override_start, override_stop, override_step, day_limit=28):
    '''
    Returns the standard error, in millions, of the predictDecayByDay model given the current decay rate parameter.
    '''
    matrix = Series()
    films = filmDict()
    df_list = []
    for film in films.items():
        df = loadDailies(film[0])
        df_list.append((film[0],df))
    for param in np.arange(override_start,override_stop,override_step):
        cumsum = Series()
        for film,df in df_list:
            actual = asSeries(df)
            predict = predictDecayByDay(df, day_limit=day_limit, override_percent_drop=[param])
            cumsum.set_value(film[1], cumsumOffset(actual, predict))
        cumsum = cumsum / 1000000
        total = (cumsum*cumsum).sum()
        matrix.set_value(param, np.sqrt(total))
        print(param, '\t', np.sqrt(total))
    return matrix

def totalCumsumOffsetError(day_limit=28):
    '''
    Returns the standard error, in millions, of the predictDecayByDay model with the default parameters.
    '''
    films = filmDict()
    df_list = []
    for film in films.items():
        df = loadDailies(film[0])
        df_list.append((film[0],df))
    cumsum = Series()
    for film,df in df_list:
        actual = asSeries(df)
        predict = predictDecayByDay(df, day_limit=day_limit)
        cumsum.set_value(film[1], cumsumOffset(actual, predict))
    cumsum = cumsum / 1000000
    total = (cumsum*cumsum).sum()
    return np.sqrt(total)

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

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


def plotPredictionAndActual(filmname, day=28, plot='daily', constrain_input=7):
    df = loadDailies(filmname)

    actual = df['Gross']
    predicted = predictDecayByDay(df,day=day,index='integer', constrain_input=constrain_input)

    if plot=='cumsum':
        actual[:limit].cumsum().plot(label='Gross')
        predicted.cumsum().plot(label='Predicted gross')
        plt.legend(loc='upper left')
    elif plot=='daily':
        actual[:limit].plot(label='Gross')
        predicted.plot(label='Predicted gross')
        plt.legend(loc='upper right')
    ax = plt.gca()
    y_format = tkr.FuncFormatter(formatter)
    ax.yaxis.set_major_formatter(y_format)
    plt.title('"' + filmname.capitalize() + '" daily gross prediction. M.S. Error: ' + str(int(meanSquaredError(actual, predicted, limit)*10)/10))
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
        return value*3
    if actual in weekend and predict in weekday:
        return value/3
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

def predictDecayByDay(df, day=28, index='day-of-week', constrain_input=7):
    '''Return a prediction of the grosses per day up until the specified day after release, given a series of daily grosses. Prediction works by
    applying a precomputed decay rate for each day of the week. If no data
    exists for the first day of the week, then that data is also estimated.

    day: number of days from release to be predicted
    index: what to index the returned time series with
    constrain_input: used to artificially limit input variables even if the data exists
    '''
    print('released on a ' + df.iloc[0].Day)
    firstWeek = extrapolateFirstWeek(df, constrain_input)
    series = asSeries(df)
    constants = [1] * 7
    predict = Series()
    dayCount = 1
    for weeknum in range(1, int(day/7) +1):
        for i in range(7):
            const = constants[i]
            day = firstWeek.index[i]
            prediction = firstWeek[i] * 1/(const * weeknum)
            if index=='day-of-week':
                predict.set_value(day + ' ' + str(weeknum), prediction)
            elif index=='integer':
                predict.set_value(dayCount, prediction)
                dayCount += 1
    return predict

def meanSquaredError(actual, predict, day=28):
    '''
    Get the Mean Squared Error for day 1 through n (or the length of the shorter series, whichever is smaller), denoted in millions.
    '''
    idx = min(min(len(actual),len(predict)), day)
    diff = (actual[:idx]/1000000 - predict[:idx]/1000000)**2
    return diff.sum() / idx

def getErrorMatrix():
    matrix = Series()
    films = filmDict()
    for film in films.items():
        series = asSeries(loadDailies(film[0]))
        predict = predictGrossCurve(series, 28)
        matrix.set_value(film[1], meanSquaredError(series, predict))
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
            predict = predictCompoundMultiplication(series, days, param)
            matrix.set_value(film, meanSquaredError(series, predict, days))
        scores.set_value(str(param), matrix.sum())
        print(str(param), matrix.sum())
    return scores

from boxofficemojo_scraper import *

_fidToName = []
def _loadFid():
    global _fidToName
    s = Series.from_csv('boxoffice/'+film_index_name)
    _fidToName = Series(s.index, index=s.values)

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

def predictGrossCurve(series, day):
    '''Return a prediction of the grosses per day up until the specified day after release, given a series of daily grosses.

    NOTE: this is extremely rudimentary for now until I get the rest of the infrastructure in place.
    '''
    cumsum_actual = 0
    cumsum_model = 0
    daygross_model = series[1]
    daygross_actual = series[1]
    print('day: actual  model     cum_actual cum_model')
    for i in range(1, day+1):
        if i < len(series):
            cumsum_actual += series[i]
            daygross_actual = series[i]
        cumsum_model += daygross_model
        print('{0}: {1}    {2}        {3}    {4}'.format(i,
            int(daygross_actual/10000)/100,
            int(daygross_model/10000)/100,
            int(cumsum_actual/10000)/100,
            int(cumsum_model/10000)/100
            ))
        daygross_model = daygross_model * (5/6)

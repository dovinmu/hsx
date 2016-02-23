import requests
from bs4 import BeautifulSoup
from pandas import DataFrame, Series
from datetime import datetime
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as tkr
import matplotlib
import numpy as np
import time

plt.style.use('ggplot')
plt.figure(figsize=(12,10), dpi=100)
base_url = 'http://www.boxofficemojo.com'
film_index_name = '0name-id.csv'

def scrapePastYear(page=1):
    r = requests.get('{0}/yearly/chart/past365.htm?page={1}'.format(base_url, page))
    soup = BeautifulSoup(r.text, 'lxml')
    yearly_table = soup.find('table',attrs={'border':0,'cellspacing':1,'cellpadding':5})

    movie_ids = {}
    for yearly_tr in yearly_table.findAll('tr')[2:]:
        yearly_tds = yearly_tr.findAll('td')
        if len(yearly_tds) == 9:
            href = yearly_tds[1].find('a')
            if not href:
                continue
            href = href.get('href')
            movie_name = yearly_tds[1].text
            movie_id = href[href.find('=')+1:href.find('.')]
            movie_ids[movie_name] = movie_id

    i=1
    for movie_name, movie_id in movie_ids.items():
        print('{0}/{1}: Writing {2}.csv ({3})'.format(i, len(movie_ids), movie_id, movie_name))
        downloadDailies(movie_id, movie_name)
        time.sleep(1)
        i += 1
    cleanFilmIndex()

def downloadDailies(movie_id, movie_name='', save=True):
    index = ['Day', 'Date', 'Rank', 'Gross', '% Change Prev Day', '% Change Prev Week', 'Theaters', 'Avg/Theater', 'Gross-to-Date','Day #']
    r = requests.get('{0}/movies/?page=daily&view=chart&id={1}.htm'.format(base_url, movie_id))
    soup = BeautifulSoup(r.text,'lxml')

    if not name:
        try:
            movie_name = soup.find('font', attrs={'face':'Verdana', 'size':'6'}).text
        except:
            movie_name = soup.find('font', attrs={'face':'Verdana', 'size':'5'}).text

    table = soup.find('table', attrs={'class':'chart-wide'})
    if table is None:
        print('{} does not have daily box office numbers'.format(movie_id))
        return DataFrame()
    results = {}
    for tr in table.findAll('tr')[1:]:
        result = [td.text for td in tr.findAll('td')]
        if len(result) > 1:
            dt = datetime.strptime(result[1].replace('\t','').replace('.',''), '%b %d, %Y')
            results[dt] = result
    df = DataFrame(results, index=index).T
    #clean data
    df['Gross'] = df['Gross'].map(lambda x: int(x[1:].replace(',','')))
    df['Gross-to-Date'] = df['Gross-to-Date'].map(lambda x: int(x[1:].replace(',','')))
    df['Avg/Theater'] = df['Avg/Theater'].map(lambda x: int(x[1:].replace(',','')))
    df['% Change Prev Day'] = df['% Change Prev Day'].map(lambda x: float('nan') if x == '-' else float(x[:-1].replace(',','')))
    df['% Change Prev Week'] = df['% Change Prev Week'].map(lambda x: float('nan') if x == '-' else float(x[:-1].replace(',','')))
    if save:
        df.to_csv('boxoffice/{}.csv'.format(movie_id))
        series = Series.from_csv('boxoffice/'+film_index_name)
        series[movie_name] = movie_id
        series.to_csv('boxoffice/'+film_index_name)
    return df



def cleanFilmIndex():
    series = Series.from_csv('boxoffice/'+film_index_name)
    l=[]
    for name,fid in series.items():
        df=loadDailies(fid)
        if df.empty:
            l.append(name)
    for name in l:
        del series[name]
    series.to_csv('boxoffice/'+film_index_name)

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

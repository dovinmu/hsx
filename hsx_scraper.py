from pandas import DataFrame,Series
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import sys

price_url = "http://www.hsx.com/chart/detail_chart_data.php?id={}"

def get_all_prices():
    '''
    Scrape the current price for each stock on HSX (usually requests 25 pages).
    Returns a DataFrame indexed by the HSX security ID for each film.

    Movement price: amount the price has changed today
    Movement percent: percent the price has changed today
    '''
    start_time = datetime.now()
    page_count = 1
    curr_page = 1

    films = {}

    while curr_page <= page_count:
        r = requests.get('http://www.hsx.com/security/list.php?id=1&sfield=name&sdir=asc&page={}'.format(curr_page))
        soup = BeautifulSoup(r.text, 'lxml')
        if page_count == 1:
            page_count = int(soup.text[soup.text.find('Page 1 of')+9:soup.text.find('Page 1 of')+12])
            print('Scraping {} pages from hsx.com/securities/list.php'.format(page_count))
        film_list = soup.find('tbody').findAll('tr')[1:]
        print('\t\tPage {}'.format(curr_page),end='\r')
        for film in film_list:
            film = film.text.strip().split('\n')
            movement = film[3].replace('(','').replace(')','').split('\xa0')
            films[film[1]] = (film[0], film[2], movement[0], movement[1])
            #print('{0}: {1}'.format(film[1], films[film[1]]))
        curr_page += 1

    df = DataFrame(films, index=['Name','Price','MovementPrice', 'MovementPercent']).T
    df['MovementPercent'] = df['MovementPercent'].map(lambda x: float(x.replace('%','')))
    df['Price'] = df['Price'].map(lambda x: float(x.replace('H$', '')))
    df['MovementPrice'] = df['MovementPrice'].map(lambda x: float(x.replace('H$', '')))
    return df

sec_to_id = Series()

def get_id(sec):
    '''Scrape the internal HTML ID for the film'''
    global sec_to_id
    if sec_to_id.empty:
        try:
            sec_to_id = Series.from_csv('hsx_security_to_id', header=0)
        except:
            print('Security -> ID table not found, making a new one')
            with open('hsx_security_to_id', 'w') as f:
                f.write('security,id')
            sec_to_id = Series.from_csv('hsx_security_to_id', header=0)
    if sec not in sec_to_id:
        r = requests.get('http://www.hsx.com/security/view/{}'.format(sec))
        #extract from webpage
        soup = BeautifulSoup(r.text)
        try:
            script = soup.findAll('script')[4].text.split('\n')
            sec_id = script[3].split('=')[2]
            sec_id = sec_id.split('"')[0]
        except:
            print("Cannot find id for {}".format(sec))
            return -1
        sec_to_id[sec] = int(sec_id)
        Series.to_csv(sec_to_id,'hsx_security_to_id',header='security,id')
    return sec_to_id[sec]

def get_historic(sec):
    '''Scrape the per-day historic price variations for the film'''
    sec_id = get_id(sec)
    if sec_id < 0:
        return Series()
    year = datetime.now().year - 1
    r = requests.get(price_url.format(sec_id))
    price_list = r.text.strip().split('\n')
    prices = {}
    for entry in price_list:
        entry = entry.split(';')
        date = entry[0].split('-')
        if date[0] == date[1] == '01':
            year += 1
        date = datetime(year, int(date[0]), int(date[1]))
        prices[date] = float(entry[1])
    return Series(prices)

def get_all_historic():
    '''Scrapes historic data for every film in the DataFrame'''
    df = get_all_prices()
    for idx in df.index:
        hist = get_historic(idx)
        all_historic_prices[idx] = hist
        if not hist.empty:
            print('{0}: start {1}, max {3}, min {4}, end {2} \t diff {5}'.format(idx, hist[0], hist[-1], hist.max(), hist.min(), hist[-1] - hist[0]))

if __name__ == '__main__':
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == 'all':
            df = get_all_prices()
            print('Summary:')
            print(df.sort('Price')[['Name','Price']])
        else:
            print('Finding history of security {}'.format(arg))
            s = get_historic(arg)
            print(s)
    elif len(sys.argv) == 1:
        print(
        '''
        Usage:
            hsx_scraper.py all: Scrape all current securities on hsx
            hsx_scraper.py <sec>: Get a time series of the past year's prices
                                  for the given security by day. securities
                                  for a given film can be found as the index
                                  of the DataFrame that is returned by using
                                  the 'all' command.
        '''
        )

The Hollywood Stock Exchange (HSX) is a virtual stocks trading platform where players place bets on the domestic grosses of films in the first four weeks of their theatrical release. Comparing the curves of previously released movies is one way to project the total gross for a just-released film. These scripts mostly scrape HSX for current prices of film stocks as well as Box Office Mojo for historical daily grosses, and do simple plotting.

Check out my demonstration of the model [here](http://dovinmu.github.io/hsx/).

Dependencies:
 * beautifulsoup4
 * pandas
 * numpy
 * matplotlib
 * requests

### Using hsx_scraper.py:
hsx_scraper.py all: Scrape all current securities on hsx
hsx_scraper.py <sec>: Get a time series of the past year's prices
                      for the given security by day. Securities
                      for a given film can be found as the index
                      of the DataFrame that is returned by using
                      the 'all' command.

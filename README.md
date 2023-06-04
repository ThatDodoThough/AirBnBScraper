# AirBnB Price Scraper
The goal of this script is to collect pricing data of advertisement in a specific area to fare better against the competition. It's meant to be executed once to give a good starting point to a new listing, in terms of pricing. It will not be maintained.

Edit 15 May 2023: AirBnB added a new functionality to its host interface to allow hosts to easily retrieve this kind of data without breaking its terms of service, therefore allowing simple comparisons. The scraper will therefore be dismissed.


The repository is organized as follows:
- **amenities_savona_2023.txt** is an output file containing the list of amenities and services provided by the selected houses among all the listings
- **prices_savona_2023.txt** is an output file providing an estimate of the daily price for a stay in all the selected houses, week by week, including clean-up prices and AirBnB fees if the host doesn't pay entirely for them.
- **src/scraper.py** is the actual scraper script. It uses Selenium drivers for Chrome to emulate a user's behavior.

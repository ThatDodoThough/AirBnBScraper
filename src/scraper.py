from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.mouse_button import MouseButton
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
import time
from calendar import Calendar
from datetime import date, timedelta
from json import dumps
import csv

from bs4 import BeautifulSoup
import urllib.request as urllib2


RESULTS_PER_PAGE = 18


def is_link_to_house(tag):
    return tag.name == 'a' and tag.has_attr('class') and ' '.join(tag['class']) == "l1j9v1wn bn2bl2p dir dir-ltr"


def stop_sign(tag):
    return tag.name == 'h2' and tag.has_attr('class') and ' '.join(tag['class']) == "_14i3z6h" and tag.string == 'Nessun risultato'


def house_no_from_link(house_link):
    return house_link[house_link.find("rooms/") + len("rooms/"): house_link.find('?')]


def lengthy_click(driver, element, seconds):
    action = ActionBuilder(driver)
    chain = ActionChains(driver)
    chain.move_to_element(element).pause(1.0*seconds/2).perform()
    action.pointer_action.pointer_down(MouseButton.LEFT)
    action.perform()
    time.sleep(seconds)
    action.clear_actions()
    action.pointer_action.pointer_up(MouseButton.LEFT)
    action.perform()
    time.sleep(1.0*seconds/2)


def retrieve_links(checkin_date: str, checkout_date: str, n_adults, min_reviews, results_per_page):
    starting_string = "https://www.airbnb.it/s/Savona--SV/homes?tab_id=home_tab&refinement_paths%5B%5D=%2Fhomes&flexible_trip_lengths%5B%5D=one_week&price_filter_input_type=0&price_filter_num_nights=5&adults={n_adults}&date_picker_type=calendar&query=Savona%2C%20SV&place_id=ChIJUwL5oRTh0hIRwNE8R33mBQQ&checkin={checkin}&checkout={checkout}&source=structured_search_input_header&search_type=autocomplete_click&items_offset={offset}"
    links = []
    MAX_RESULTS = 1000
    with open('log.txt', 'w') as fout:
        for i in range(0, MAX_RESULTS, results_per_page):
            main_url = starting_string.format(checkin=checkin_date, checkout=checkout_date, n_adults=n_adults, offset=i)
            main_html = urllib2.urlopen(main_url)
            main_page = BeautifulSoup(main_html.read(), features='html.parser')
            if len(main_page.find_all(stop_sign)) != 0:
                break
            ls = list(main_page.find_all(is_link_to_house))
            locations = [tag.string for tag in list(main_page.find_all(lambda tag: tag.name == 'div' and tag.has_attr('class') and ' '.join(tag['class']) == 't1jojoys dir dir-ltr'))]
            reviews = [tag.string for tag in list(main_page.find_all(lambda tag: tag.name == 'span' and tag.has_attr('class') and ' '.join(tag['class']) == 'r1dxllyb dir dir-ltr'))]
            reviews = list(map(lambda rev: 0 if rev.find('(') < 0 else int(rev[rev.find('(')+1: rev.find(')')]), reviews))
            ls = [tup[0] for tup in zip(ls, locations, reviews) if "Savona" in tup[1] and tup[2] > min_reviews]
            detailed_links = list(map(lambda tag: 'https://www.airbnb.it' + tag['href'], ls))
            links.extend(detailed_links)
            for tup in zip(ls, reviews):
                fout.write(f'{tup[1]}: {tup[0]}\n')
    print(len(links))
    return links


def compute_row_and_col(year: int, month: int, day_of_month: int):
    # returns number of row (<tr>) and column (<td>), STARTING FROM 0
    cal = Calendar()
    raw = cal.monthdatescalendar(year, month)
    filtered = [set(filter(lambda dt: dt.month == month, l)) for l in raw]
    target = date(year, month, day_of_month)
    for n_row, week in enumerate(filtered):
        if target in week:
            return n_row, target.weekday()


def compute_min_nights(loaded_page):
    soup = BeautifulSoup(loaded_page, features='html.parser')
    err_div = soup.find("div", class_='_1yhfti2', id="bookItTripDetailsError")
    if err_div is None:
        return 1
    n_nights = int(list(err_div.strings)[-1].split(' ')[-1])
    return n_nights


def close_privacy(driver):
    try:
        driver.find_element(By.XPATH, "//div[@class='_160gnkxa']/button[1]").click()
    finally:
        return


def close_active_translation(driver):
    try:
        driver.find_element(By.XPATH, "//div[@class='_1piuevz']/button[1]")
    finally:
        return


def click_next_month(driver):
    driver.find_element(By.XPATH, "//div[@class='_qz9x4fc']/button[1]").click()
    time.sleep(2)


def find_suitable_date(driver, starting_date: date, offset=0):
    # offset is 0 for the checkin date, but it's 1 for checkout --> start from the following day from checkin date
    n_movements = 0
    effective_start = starting_date + timedelta(days=offset)
    if starting_date.month != effective_start.month:
        # click on the arrow to change month
        click_next_month(driver)

    while True:
        try:
            # print(effective_start)
            row, col = compute_row_and_col(effective_start.year, effective_start.month, effective_start.day)
            element = driver.find_element(By.XPATH,
                                          f'//table[@class="_cvkwaj"]/tbody/tr[{row + 1}]/td[{col + 1}]')
            lengthy_click(driver, element, 0.25)
            time.sleep(2)
            if offset == 1 and len(retrieve_prices(driver.page_source).keys()) == 0:
                raise ElementNotInteractableException("Invalid date, moving on")
            return n_movements + offset, effective_start

        except ElementNotInteractableException:
            n_movements += 3
            previous_start = effective_start
            effective_start = previous_start + timedelta(days=3)
            if (effective_start - starting_date).days > 30:
                raise NoSuchElementException('Couldn\'t find a suitable date.')

            if previous_start.month != effective_start.month:
                # click on the arrow to change month if the new date is in another month
                driver.find_element(By.XPATH, "//div[@class='_qz9x4fc']/button[1]").click()
                time.sleep(2)
            continue


def change_dates(driver, checkin_date: date = date(2023, 8, 26)):
    # clink on chosen checkin date in the calendar
    flex_slots, checkin_date = find_suitable_date(driver, checkin_date, 0)

    # find a suitable checkout date in the calendar
    n_nights, checkout_date = find_suitable_date(driver, checkin_date + timedelta(days=flex_slots), 1)

    return checkin_date, checkout_date, n_nights


def retrieve_prices(loaded_page):
    soup = BeautifulSoup(loaded_page, features='html.parser')
    rows = soup.find("div", class_='_ud8a1c').find_all("div", class_="_1fpuhdl")
    if len(rows) == 0:
        return {}
    house_prices = {}
    for r in rows:
        label = list(r.strings)[0]
        spans = list(r.contents)
        price = float(spans[1].string.replace('\xa0€', '').replace('.', ''))
        if "€" in label:
            house_prices['Giornaliero'] = price
        else:
            house_prices[label] = price

    return house_prices


def retrieve_amenities(loaded_page):
    soup = BeautifulSoup(loaded_page, features='html.parser')
    provided_amenities = set()
    sections = soup.find("div", class_='_17itzz4').find_all("div", class_="_11jhslp")
    for s in sections:
        title = s.div.h3.string
        # print(title)
        if "Non incluso" in title:
            continue

        amnts = [tag.string for tag in s.find_all("div", class_="t1dx2edb")]
        provided_amenities = provided_amenities.union(amnts)
        # print(f'{amnts} {provided_amenities}')

    return provided_amenities


def retrieve_house_amenities_and_prices(driver, link, ending_date: date, step_days=7):
    driver.get(link)
    time.sleep(14)
    close_active_translation(driver)
    time.sleep(1)
    close_privacy(driver)
    time.sleep(1)

    house_prices = {}

    # Amenities
    try:
        driver.find_element(By.CLASS_NAME, 'b65jmrv').click()   # open amenities
        time.sleep(10)
        house_amenities = retrieve_amenities(driver.page_source)
        driver.find_element(By.XPATH, '//div[@class="c10hl6ue dir dir-ltr"]/button[1]').click()  # close amenities
        time.sleep(1)

    except (NoSuchElementException, ElementNotInteractableException):
        print("Not found")
        return set(), house_prices

    # Prices scraping
    starting_date = date.fromisoformat(link[link.find('check_in=')+len("check_in="): link.find('check_in=')+len("check_in=YYYY-MM-DD")])
    running_date = starting_date
    step = timedelta(days=step_days)
    while running_date < ending_date:
        try:
            effective_checkin, effective_checkout, n_nights = change_dates(driver, checkin_date=running_date)
        except NoSuchElementException:
            return house_amenities, house_prices
        
        halfway_date = effective_checkin + (effective_checkout - effective_checkin) / 2
        halfway_date = date(year=halfway_date.year, month=halfway_date.month, day=halfway_date.day)
        raw_prices = retrieve_prices(driver.page_source)
        raw_prices['Giornaliero'] *= 1.0 / n_nights                     # compute the average amount per night starting from the total
        raw_prices['n_nights'] = n_nights
        house_prices[halfway_date.strftime('%Y-%m-%d')] = raw_prices
        running_date = effective_checkout + step
        if running_date.month != effective_checkout.month:
            click_next_month(driver)

    return house_amenities, house_prices


def scrape_all_results(chrome_driver, house_links, end_date: date, output_amenities_fpath, output_prices_fpath):
    amenity_collection = {}
    prices_output = []

    for house in house_links:
        amenities, prices = retrieve_house_amenities_and_prices(chrome_driver, house, end_date)
        # print(amenities)
        amenity_collection[house] = list(amenities)
        prices_output.extend([(house_no_from_link(house), available_date, dumps(price_dict)) for available_date, price_dict in prices.items()])

    with open(output_amenities_fpath, 'w') as f_amenities:
        writer = csv.writer(f_amenities)
        rows = [(house_no_from_link(house), dumps(amenity_list)) for house, amenity_list in amenity_collection.items()]
        writer.writerows(rows)

    with open(output_prices_fpath, 'w') as f_prices:
        writer = csv.writer(f_prices)
        writer.writerows(prices_output)


if __name__ == '__main__':
    test_room = "https://www.airbnb.it/rooms/840394955830733789?adults=4&check_in=2023-04-01&check_out=2023-04-02&previous_page_section_name=1000&federated_search_id=c1649759-0e33-43a8-8dff-3e8d87f49f18"

    service = ChromeService(executable_path=ChromeDriverManager().install())
    driver1 = webdriver.Chrome(service=service)

    all_links = retrieve_links(checkin_date='2023-09-01', checkout_date='2023-09-02', n_adults=4, min_reviews=5, results_per_page=RESULTS_PER_PAGE)
    scrape_all_results(chrome_driver=driver1,
                       house_links=all_links,
                       end_date=date.fromisoformat('2023-10-31'),
                       output_prices_fpath='prices_savona_2023.txt',
                       output_amenities_fpath='amenities_savona_2023.txt')


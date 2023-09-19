from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
import bs4
import requests
import json


ILREGNODELCINEMA_BASE_URL = "https://www.ilregnodelcinema.com"
BASE_URL = "https://www.ilregnodelcinema.com/multisalaportanova"


class MultisalaPortanovaScraper:

    # -- FIELDS -- #
    available_films = list()
    upcoming_films = list()
    valid_from = date(1900, 1, 1)
    valid_to = date(1900, 1, 1)
    error = None

    # -- CONSTRUCTOR -- #
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.get_data()

    # -- MAIN -- #

    def get_data(self):
        """Main method called by constructor to assign fields."""
        try:
            response = requests.get(self.base_url)

        except Exception as ex:
            self.error = ex
            return None

        html_code = self.manage_response(response)

        if not html_code:
            return None

        try:
            page = BeautifulSoup(html_code, "html.parser")

            # Validity
            planning_tag = page.find("div", class_="progData")
            if planning_tag:
                day, month = self.get_day_and_month_from_unformatted_string(planning_tag.text)
                if day and month:
                    self.valid_from = date(date.today().year, month, day)
                    self.valid_to = self.valid_from + timedelta(days=13)

            # Available films
            film_containers = page.findAll("div", class_="filmContainer")
            for container in film_containers:
                film_data = self.get_single_film_data(container)
                # Get only available timetable films (the ones without a timetable will be in the 'upcoming_films' field)
                if film_data.get('orari'):
                    self.available_films.append(film_data)

            # Upcoming films
            upcoming_film_containers = page.findAll("div", class_="longprog_mov")
            for container in upcoming_film_containers:
                self.upcoming_films.append(self.get_upcoming_film_data(container))

        except Exception as ex:
            self.error = ex

    # -- STATIC METHODS -- #
    @staticmethod
    def get_timetable_data(timetable_container_list) -> dict or None:
        """
        :returns: A dictionary with date objects as keys, and a tuple of datetime.time objects as values.
                  Ex: {2023-9-10: [datetime.time(14, 40), datetime.time(17, 0), datetime.time(19, 15)]}
        """
        if not timetable_container_list:
            return None

        timetable_vals = dict()
        for timetable in timetable_container_list:
            dayname_tag = timetable.find("div", class_="dayName")
            hour_tags = timetable.findAll("span")
            hours_list = [hour.text for hour in hour_tags]

            if dayname_tag and hours_list:
                # dayname_tag.text is expected to be like 'Sabato 16/09'
                # (16, 9)
                day_month_values = tuple(int(number) for number in dayname_tag.text.split(" ")[1].split("/"))
                year = date.today().year if date.today().month <= day_month_values[1] else date.today().year + 1
                date_obj = date(year, day_month_values[1], day_month_values[0])
                timetable = tuple(
                    datetime(year, day_month_values[1], day_month_values[0], int(hour.split(":")[0]), int(hour.split(":")[1])).time()
                    for hour in hours_list
                )
                timetable_vals.update({date_obj: timetable})

        return timetable_vals

    @staticmethod
    def get_day_and_month_from_unformatted_string(unformatted_string):
        """
        :param unformatted_string: any string who has a single number and a month name present in month_mapping.json
                                   (month is optional, the function can try to assume it)
        """

        with open("month_mapping.json") as f:
            month_mapping = json.load(f)

        day = 0
        month = 0

        for word in unformatted_string.split(" "):
            if not day and word.isdigit():
                day = int(word)
            if not month:
                month = month_mapping.get(word.lower())

        # In case the string doesn't have the month name I try to assume it.
        # With web scraping you can never know
        if day and not month:
            month = date.today().month
            if day >= date.today().day:
                month += 1

        return day, month

    @staticmethod
    def get_img_src_url(container):
        img_tag = container.find("img")
        if img_tag:
            return ILREGNODELCINEMA_BASE_URL + img_tag.attrs.get('src')[2:]
        else:
            return None

    # -- CLASS METHODS -- #

    def get_single_film_data(self, film_container: bs4.Tag) -> dict:
        film_vals = {'img': self.get_img_src_url(film_container)}

        for cls in ("titolo", "regia", "genere", "durata", "cast"):
            tag = film_container.find("div", class_=cls)
            if tag:
                text = tag.text
                # To have clean data
                if cls.capitalize() in text or "NEW!" in text:
                    text = text.replace(f"{cls.capitalize()}: ", "").replace("NEW! ", "")
                elif "V.M.14" in text:
                    text = text.replace(" - V.M.14", "")
                    film_vals['vm14'] = True
                elif "V.M.14" not in text:
                    film_vals['vm14'] = False

                film_vals[cls] = text

        film_vals['orari'] = self.get_timetable_data(film_container.findAll("li"))

        return film_vals

    def get_upcoming_film_data(self, film_container: bs4.Tag) -> dict:
        upcoming_film_vals = {'img': self.get_img_src_url(film_container)}

        title_tag = film_container.find("div", class_="longprog_title")
        if title_tag:
            upcoming_film_vals['titolo'] = title_tag.text

        release_date_tag = film_container.find("div", class_="longprog_data")
        if release_date_tag:
            day, month = self.get_day_and_month_from_unformatted_string(release_date_tag.text)
            year = date.today().year if month >= date.today().month else date.today().year + 1
            upcoming_film_vals['release_date'] = date(year, month, day)

        return upcoming_film_vals

    def search(self, film_name):
        for film in self.available_films:
            if film_name in film.get('titolo').lower():
                return film
        return None

    def manage_response(self, response: requests.Response):
        """
        Response management | If there're not errors returns html code,
        otherwise returns None and assigns the error to self.error field.
        """

        if response.status_code != 200:
            self.error = str(response.status_code)
            return None

        else:
            return response.content

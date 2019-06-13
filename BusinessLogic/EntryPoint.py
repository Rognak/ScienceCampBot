import re
import requests
from AppSettings import *
from bs4 import BeautifulSoup
from Interfaces.AbstractParser import *
from googletrans import Translator


class MainParser(AParser):

    def __init__(self, settings):
        self.settings = settings

    def _make_url(self, url, query_string):

        """Данная функция служит для преобразования строки в корректный GET запрос"""
        if url == search_sources[0]:

            query = search_sources[0] + 'action/doSearch?AllField='

            for pattern, repl in zip(' ,', ['+', '%2C']):
                query_string = re.sub(pattern, repl, query_string)

            query += query_string

            return query


    #def _show_results:

    def start_console(self):

        print("Введите строку запроса: ")
        query_string = input()

        # Объявляем объект web-сессии и переводчика
        session = requests.Session()
        translator = Translator()

        #for source in self.settings['sources']:
         #   query = self._make_url(source, query_string)

        for source in search_sources:
            query = self._make_url(source, query_string)
            response = session.get(query)
            soup = BeautifulSoup(response.text, 'lxml')

            articles = soup.find_all("div", {"class": "issue-item_metadata"})

            for result in articles:
                print()
                print('Название статьи: ', result.h5.get_text())

                authors = []

                for author in result.ul:
                    authors.append(author.text)
                print('Авторы: ', ', '.join(authors))

                try:
                    doi = result.find('div', {'class': 'issue-item_info'})
                    res = re.search(patterns['doi'], doi.contents[-2].get_text())
                    print('DOI: ', res.group(0))
                    print()
                except:
                    print("none")

                try:
                    annotation = result.find('div', {"class": "accordion__content"}).get_text()
                    print('Аннотация (En):', annotation)
                    print()

                    translated_annotation = translator.translate(annotation, dest='ru')
                    print('Аннотация (Ru):', translated_annotation.text)
                    print()
                except:
                    print('No')


                try:
                    r = requests.get(scihub_url + res.group(0))
                    hub = BeautifulSoup(r.text, 'lxml')
                    res = hub.find('div', {'id': 'buttons'}).ul.contents[3].a['onclick']
                    print('Ссылка для скачивания sci hub:', re.findall(r'href=[\'"]?([^\'" >]+)', res))
                except:
                    "Oops, captcha!"




if __name__ == '__main__':
    parser = MainParser(search_settings)
    parser.start_console()
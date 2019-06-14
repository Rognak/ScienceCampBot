import re
import requests
from AppSettings import *
from bs4 import BeautifulSoup
from Interfaces.AbstractParser import *
from googletrans import Translator


class MainParser(AParser):

    def __init__(self, settings):
        self.parser_settings = settings

    def _make_url(self, url, query_string):

        """Данная функция служит для преобразования строки в корректный GET запрос"""
        if url == search_sources[0]:

            query = search_sources[0] + 'action/doSearch?AllField='

            for pattern, repl in zip(' ,', ['+', '%2C']):
                query_string = re.sub(pattern, repl, query_string)

            query += query_string

            return query


    def _get_results(self, source, soup, max_articles):
        """Данная функция обрабатывает статьи"""

        articles_titles = []
        authors = []
        all_authors = []
        dois = []
        annotations = []
        scihub_urls = []

        if source == search_sources[0]:
            articles = soup.find_all("div", {"class": "issue-item_metadata"})

            for i in range(max_articles):
                articles_titles.append(articles[i].h5.get_text())

                for author in articles[i].ul:
                    authors.append(author.text)
                all_authors.append(authors)

                try:
                    doi = articles[i].find('div', {'class': 'issue-item_info'})
                    res = re.search(patterns['doi'], doi.contents[-2].get_text())

                    dois.append(
                        res.group(0)
                    )
                except:
                    dois.append('No doi')

                try:
                    annotations.append(articles[i].find('div', {"class": "accordion__content"}).get_text())
                except:
                    annotations.append('No annotation')

                try:
                    r = requests.get(scihub_url + res.group(0))
                    hub = BeautifulSoup(r.text, 'lxml')
                    res = hub.find('div', {'id': 'buttons'}).ul.contents[3].a['onclick']
                    scihub_urls.append(re.findall(patterns['url'], res))
                except:
                    "Oops, captcha!"


        return articles_titles, authors, dois, annotations, scihub_urls



    def start_console(self, max_articles = search_settings['max_articles']):
        print("Введите строку запроса: ")
        query_string = input()

        # Объявляем объект web-сессии и переводчика
        session = requests.Session()
        translator = Translator()

        for source in self.parser_settings['sources']:

            query = self._make_url(source, query_string)
            response = session.get(query)
            soup = BeautifulSoup(response.text, 'lxml')

            results = self._get_results(source, soup, max_articles)

            for i in range(len(results)):
                translated_annotation = translator.translate(results[3][i], dest='ru')
                print()
                print('Название статьи: ', results[0][i])
                print('Авторы: ', ', '.join(results[1]))
                print('DOI: ', results[2][i])
                print()
                print('Аннотация (En):', results[3][i])
                print()
                print('Аннотация (Ru):', translated_annotation.text)
                print()
                print('Ссылка для скачивания sci hub:', results[-1][i])

if __name__ == '__main__':
    parser = MainParser(search_settings)
    parser.start_console()

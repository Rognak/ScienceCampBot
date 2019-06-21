import re
import requests
from spellchecker import SpellChecker
from bs4 import BeautifulSoup
from Interfaces.AbstractParser import *
from googletrans import Translator
import time
import numpy as np
from AppSettings import *
from .database_class import DataBase

class BotParser:

    def __init__(self, settings):
        self.parser_settings = settings

    def _make_url(self, url, query_string, max_articles):

        """Данная функция служит для преобразования строки в корректный GET запрос"""
        if url == search_sources[0]:

            query = search_sources[0] + 'action/doSearch?AllField='

            for pattern, repl in zip(' ,', ['+', '%2C']):
                query_string = re.sub(pattern, repl, query_string)

            query += query_string

            return query + '&startPage=0&pageSize={}'.format(max_articles)

    def _get_results(self, source, soup, database, key_words, doi_from_db):
        """Данная функция обрабатывает статьи"""
        authors = []
        stacked_article = list()
        if source == search_sources[0]:
            articles = soup.find_all("div", {"class": "issue-item_metadata"})

            for i in range(len(articles)):

                doi = articles[i].find('div', {'class': 'issue-item_info'})
                doi = re.search(patterns['doi'], doi.contents[-2].get_text())
                doi = doi.group(0)


                if doi not in doi_from_db:
                    title = articles[i].h5.get_text()

                    for author in articles[i].ul:
                        try:
                            authors.append(author.text)
                        except:
                            authors.append('I dont know author')
                    authors_to_db = ','.join(authors)
                    authors = []

                    try:
                        annotation = articles[i].find('div', {"class": "accordion__content"}).get_text()
                    except:
                        annotation = 'No annotation'

                    #TODO вставить функцию генератора ссылки на скайхаб
                    #start_time = time.time()
                    #:
                    #    r = requests.get(scihub_url + doi)
                    #    hub = BeautifulSoup(r.text, 'lxml')
                    #    res = hub.find('div', {'id': 'buttons'}).ul.contents[3].a['onclick']
                    #    #scihub_url = re.findall(patterns['url'], res)
                    #except:
                    #    "Oops, captcha!"
                    #t = time.time() - start_time

                    database.insert_to_results(connection, key_words, title, authors_to_db, doi, annotation)
                else:
                    article = database.select_by_value(connection, 'search_results', 'doi', doi)
                    stacked_article.append(article)

        if len(stacked_article) != 0:
            return self._stack_and_reshape(np.array(stacked_article), 5)


    def _stack_and_reshape(self, array, shape):
        stacked = np.stack(array)
        if len(stacked.shape) == 2:
            stacked = stacked.reshape(stacked.shape[0], shape)
        else:
            stacked = stacked.reshape(stacked.shape[1], shape)
        return stacked

    def _prepare_results(self, results, stored):
        d2 = {str(results[i:i + 1, 3][0]): results[i:i + 1, :] for i in range(len(results))}
        d1 = {str(stored[i:i + 1, 4][0]): stored[i:i + 1, :5] for i in range(len(stored))}
        value = {k: d2[k] for k in set(d2) - set(d1)}
        return self._stack_and_reshape(value.values(), 5)


    def _prepare_keywords(self, keywords):
        keywords = keywords.lower()
        keywords = re.sub(', ', ',', keywords)
        keywords = re.sub(' ', ',', keywords)
        keywords = keywords.split(',')
        return sorted(keywords)


    def _check_keywords(self, keywords):
        checker = SpellChecker()
        return checker.unknown(keywords)

    def parse(self, keywords, chat_id, max_articles = search_settings['max_articles']):

        query_string = self._prepare_keywords(keywords)
        checked_keywords = self._check_keywords(query_string)
        query_string = ', '.join(self._prepare_keywords(keywords))
        # print(query_string)

        if len(checked_keywords) != 0:
            # print('Я не знаю таких слов: ' + ', '.join(checked_keywords))
            return 0
            #TODO need to write correct return

        session = requests.Session()

        # Объявляем объект базы данных
        database = DataBase(database_connection_settings)

        # Создаём соединение
        global connection
        connection = database.make_connection()

        # Получаем список ключевых слов из бд
        keywords = database.get_keywords(connection, query_string)

        # Получаем список doi из бд
        doi_from_db = database.get_doi(connection)

        #пример chat_id
        chat_id = '12345'

        if query_string in keywords:
            all_results = database.select_by_value(connection, 'search_results', 'key_words', query_string)
            stored_results = database.select_by_value(connection, 'users_stored_articles', 'key_words', query_string, ('chat_id', chat_id))
            results = self._prepare_results(all_results, stored_results)
            database.close_connection(connection)
            return results

        else:
            start_time = time.time()

            for source in self.parser_settings['sources']:
                query = self._make_url(source, query_string, max_articles=5)
                response = session.get(query)

                soup = BeautifulSoup(response.text, 'lxml')

                #получаем спиоск имеющихся статей (если есть) и заносим в бд уникальные
                results = self._get_results(source, soup, database, query_string, doi_from_db)
                all_results = database.select_by_value(connection, 'search_results', 'key_words', query_string)
                stored_results = database.select_by_value(connection, 'users_stored_articles', 'chat_id',
                                                          chat_id)
                if results is not None:
                    indexes = []
                    for i in range(len(results)):
                        if results[i] in stored_results[:, 5]:
                            indexes.append(i)
                    prepared_results = np.vstack((all_results,results[indexes]))
                else:
                    prepared_results = all_results
                key_words, title, authors, doi, annotation = prepared_results[i:i+1, 0, :]
                database.insert_to_stored(connection, key_words, title, authors, doi, annotation, chat_id)
            database.close_connection(connection)
                # print('ready')

            # print("--- %s seconds ---" % (time.time() - start_time))
            return prepared_results


    # def test(self, results):
    #     database = DataBase(database_connection_settings)
    #     connection = database.make_connection()

    #     for i in range(len(results)):
    #         print('Название статьи: ', results[i:i+1, 1][0])
    #         print('Авторы: ', results[i:i+1, 2][0])
    #         print('DOI: ', results[i:i+1, 3][0])
    #         print()
    #         print('Аннотация (En):', results[i:i+1, 4][0])

    #         print()
    #         ans = input("Next? ")
    #         print()
    #         if ans == 'y':
    #             database.insert_to_stored(connection, query, results[i:i+1, 1][0], results[i:i+1, 2][0], results[i:i+1, 3][0], results[i:i+1, 4][0], '12345')
    #             continue
    #         elif ans == 'n':
    #             database.close_connection(connection)
    #             break



# if __name__ == '__main__':
#     parser = BotParser(search_settings)
#     for i in range(2):
#         query = input('введите строку запроса: ')
#         results = parser.parse(query)
#         parser.test(results)
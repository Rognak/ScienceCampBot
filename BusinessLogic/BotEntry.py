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
import hashlib

class BotParser:

    def __init__(self, settings, database):
        self.parser_settings = settings
        self.database = database

    def _make_url(self, url, query_string, max_articles):

        """Данная функция служит для преобразования строки в корректный GET запрос"""
        if url == search_sources[0]:

            query = search_sources[0] + 'action/doSearch?AllField='

            for pattern, repl in zip(' ,', ['+', '%2C']):
                query_string = re.sub(pattern, repl, query_string)

            query += query_string

            return query + '&startPage=0&pageSize={}'.format(max_articles)

    def _get_results(self, source, soup, database, key_words, doi_from_db, connection):
        """Данная функция обрабатывает статьи"""
        authors = []
        stacked_article = list()
        if source == search_sources[0]:
            articles = soup.find_all("div", {"class": "issue-item_metadata"})

            for i in range(len(articles)):


                doi = articles[i].find('div', {'class': 'issue-item_info'})
                try:
                    public_date = doi.find('span', {'class': 'pub-date-value'}).get_text().split(' ')[-1]
                except:
                    public_date = 'No pub data'
                doi = re.search(patterns['doi'], doi.contents[-2].get_text())
                doi = doi.group(0)


                if doi not in doi_from_db:
                    title = articles[i].h5.get_text()

                    for author in articles[i].ul:
                        try:
                            author_test = author.text
                            if ',' in author_test:
                                author_test = re.findall(patterns['author_parcing'], author_test)[0]

                            if 'ufeff' in author_test:
                                author_test = re.sub(r"b\ufeff\b", '', author_test)
                            authors.append(author_test)
                        except:
                            authors.append('I dont know author')

                    sci_author = authors[0].split(' ')[-1]
                    main_author = re.findall(patterns['author'], sci_author)[0].lower()
                    authors_to_db = ','.join(authors)
                    authors = []

                    try:
                        annotation = articles[i].find('div', {"class": "accordion__content"}).get_text()
                    except:
                        annotation = 'No annotation'

                    if main_author != 'author':
                        try:
                            sci_hash = hashlib.md5(bytes(doi,encoding='utf-8')).hexdigest()
                            res_hub = 'https://dacemirror.sci-hub.se/journal-article/' + sci_hash + '/' + main_author + public_date + '.pdf?download=true'
                        except:
                            "Oops, captcha!"

                    database.insert_to_results(connection, key_words, title, authors_to_db, doi, annotation, res_hub)
                else:
                    article = database.select_by_value(connection, 'search_results', 'doi', doi)
                    stacked_article.append(article)

        if len(stacked_article) != 0:
            arr = np.array(stacked_article)
            print(np.array(stacked_article).shape)

            if len(np.array(stacked_article).shape) > 2:
                return self._stack_and_reshape(arr, (int(arr.size/arr.shape[-1]), arr.shape[-1]))

            return self._stack_and_reshape(arr, arr.shape)


    @staticmethod
    def _parse_scihub(doi):
        r = requests.get(scihub_url + doi)
        hub = BeautifulSoup(r.text, 'lxml')
        res = hub.find('div', {'id': 'buttons'}).ul.contents[3].a['onclick']
        res_hub = re.findall(patterns['url'], res)[0]
        if res_hub.startswith('https://'):
            sci_request = res_hub
        else:
            sci_request = 'https://' + res[2:]
        return sci_request


    @staticmethod
    def parse_captcha(artcle_url, response_text):
        hub = BeautifulSoup(response_text, 'lxml')
        image = hub.find('img', {'id': 'captcha'})['src']
        id = hub.find('input', {'name': 'id'})['value']
        return artcle_url[7:].split('/')[1] + image, id

    @staticmethod
    def check_url(function):

        def wrapper(bot, update, article_url, doi, filename, context=None, user_data=None):
            db = DataBase(database_connection_settings)
            connection = db.make_connection()
            print('im here bitch')
            print(article_url)

            session = requests.Session()
            headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:67.0) Gecko/20100101 Firefox/67.0'}
            article = session.get(article_url, headers=headers)

            print(article.status_code)

            if article.status_code == 404:
                print('getting 404')
                new_article_url = BotParser._parse_scihub(doi)
                DataBase.update_url(connection, new_article_url)
                db.close_connection(connection)
                return function(bot, update, new_article_url, doi, filename, context=context, user_data=user_data)

            else:
                db.close_connection(connection)
                return function(bot, update, article_url, doi, filename, context=context, user_data=user_data)

        return wrapper

    def _stack_and_reshape(self, array, shape):
        stacked = np.stack(array)
        stacked = stacked.reshape(shape[0], shape[1])
        return stacked

    def _prepare_results(self, results, stored):
        d2 = {str(results[i:i + 1, 3][0]): results[i:i + 1, :] for i in range(len(results))}
        d1 = {str(stored[i:i + 1, 3][0]): stored[i:i + 1, :5] for i in range(len(stored))}
        value = {k: d2[k] for k in set(d2) - set(d1)}
        return self._stack_and_reshape(value.values(), (len(value.values()), 6))

    def _prepare_keywords(self, keywords):
        keywords = keywords.lower()
        keywords = re.sub(', ', ',', keywords)
        keywords = re.sub(' ', ',', keywords)
        keywords = keywords.split(',')
        return sorted(keywords)

    def _check_keywords(self, keywords):
        checker = SpellChecker()
        return checker.unknown(keywords)

    def register_watched(self, key_words, title, authors, doi, annotation, chat_id, scihub_url):
        """Registers resutl into the database"""
        
        global connection
        
        database = DataBase(database_connection_settings)
        connection = database.make_connection()
        database.insert_to_stored(connection, key_words, title, authors, doi, annotation, chat_id, scihub_url)
        database.close_connection(connection)

    def parse(self, keywords, chat_id, max_articles):

        query_string = self._prepare_keywords(keywords)
        checked_keywords = self._check_keywords(query_string)
        query_string = ', '.join(self._prepare_keywords(keywords))
        print(query_string)
        print(checked_keywords)
        # print(query_string)

        if len(checked_keywords) != 0:
            # print('Я не знаю таких слов: ' + ', '.join(checked_keywords))
            return 0
            #TODO need to write correct return

        connection = self.database.make_connection()
        keywords = self.database.get_keywords(connection, query_string)
        doi_from_db = self.database.get_doi(connection)

        with requests.Session() as session:
            if query_string in keywords:
                all_results = self.database.select_by_value(connection, 'search_results', 'key_words', query_string)
                stored_results = self.database.select_by_value(connection, 'users_stored_articles', 'key_words',
                                                          query_string, ('chat_id', chat_id))
                results = self._prepare_results(all_results, stored_results)
                self.database.close_connection(connection)
                return results
            else:
                for source in self.parser_settings['sources']:
                    query = self._make_url(source, query_string, max_articles=max_articles)
                    response = session.get(query)
                    soup = BeautifulSoup(response.text, 'lxml')

                    # получаем спиоск имеющихся статей (если есть) и заносим в бд уникальные
                    results = self._get_results(source, soup, self.database, query_string, doi_from_db, connection)
                    all_results = self.database.select_by_value(connection, 'search_results', 'key_words', query_string)
                    stored_results = self.database.select_by_value(connection, 'users_stored_articles', 'chat_id',
                                                              chat_id)
                    if results is not None:
                        indexes = []
                        for i in range(len(results)):
                            if results[i][3] in stored_results[:, 3]:
                                indexes.append(i)
                        prepared_results = np.vstack((all_results, results[indexes]))
                    else:
                        prepared_results = all_results

                self.database.close_connection()
                return prepared_results




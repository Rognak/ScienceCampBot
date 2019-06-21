import psycopg2
import numpy as np
from AppSettings import *

class DataBase:

    def __init__(self, settings):
        self.connection_settings = settings
        self.db = list(self.connection_settings.values())


    def make_connection(self):
        connection = psycopg2.connect(
            dbname=self.db[0],
            user=self.db[1],
            password=self.db[2],
            host=self.db[3]
        )

        return connection

    def close_connection(self, connection):
        connection.close()
        return connection

    def get_keywords(self, connection, keyword):
        """Получение списка ключевых слов"""
        cursor = connection.cursor()
        cursor.execute("""SELECT key_words FROM search_results WHERE key_words = '%s' """ % keyword)
        results_from_database = cursor.fetchall()
        results_from_database = np.array(results_from_database)
        #print(results_from_database)
        cursor.close()
        if len(results_from_database) != 0:
            return results_from_database[:, 0]
        else:
            return results_from_database

    def get_doi(self, connection):
        """Получение списка doi"""
        cursor = connection.cursor()
        cursor.execute("""SELECT doi FROM search_results """)
        results_from_database = cursor.fetchall()
        results_from_database = np.array(results_from_database)
        cursor.close()
        if len(results_from_database) != 0:
            return results_from_database[:, 0]
        else:
            return results_from_database


    def insert_to_results(self, connection, key_words, title, authors, doi, annotation):
        """Вставка в результаты поиска"""
        cursor = connection.cursor()

        cursor.execute("""INSERT INTO search_results
                          (key_words, title, authors, doi, annotation)
                          VALUES (%s, %s, %s, %s, %s)
                       """, (str(key_words), str(title), str(authors), str(doi), str(annotation)))
        connection.commit()
        cursor.close()


    def select_by_value(self, connection, table, select_param, value, and_params = None):
        cursor = connection.cursor()
        #print(and_params)
        if and_params == None:
            cursor.execute("""SELECT * FROM %s WHERE %s = '%s'""" % (table, select_param, value))
        else:
            cursor.execute("""SELECT * FROM %s WHERE %s = '%s' AND %s = '%s' """% (table, select_param, value, and_params[0], and_params[1]))

        results_from_database = cursor.fetchall()
        results_from_database = np.array(results_from_database)
        cursor.close()
        return  results_from_database

    def insert_to_stored(self, connection, key_words, title, authors, doi, annotation, chat_id):
        cursor = connection.cursor()

        cursor.execute("""INSERT INTO users_stored_articles
                           (key_words, title, authors, doi, annotation, chat_id)
                           VALUES (%s, %s, %s, %s, %s, %s)
                        """, (str(key_words), str(title), str(authors), str(doi), str(annotation), str(chat_id)))
        connection.commit()
        cursor.close()


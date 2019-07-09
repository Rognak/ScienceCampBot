# -*- coding: utf-8 -*-
"""
Main telegram bot

Usage:
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import os
import sys
import logging
import json
import requests
import telegram
import traceback
import asyncio
from googletrans import Translator
from telegram import ParseMode
from telegram import ReplyKeyboardMarkup
from telegram.ext.dispatcher import run_async
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler, CallbackQueryHandler,
                          ConversationHandler)
import hashlib
from BusinessLogic import database_class

# import crossref
from crossref.restful import Works
import doi2bib

from AppSettings import *
# from BusinessLogic import EntryPoint
from BusinessLogic.BotEntry import BotParser
from BusinessLogic.database_class import DataBase

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

LOGGER = logging.getLogger(__name__)

IDLE, SEARCH_RESULTLS, SENDING_CAPCHA, TYPING_REPLY = range(4)

with open('api.json', 'r', encoding='UTF-8') as local_file:
    data = json.loads(local_file.read())
    __TOCKEN__ = data['API']
    __BOT_NAME__ = data['BOT_NAME']
    __BOT_API_NAME__ = data['BOT_API_NAME']
    __URL__ = data['URL']
    del data

if not os.path.exists('renders'):
    os.mkdir('renders')
if not os.path.exists('downloads'):
    os.mkdir('downloads')

TRANSLATOR = Translator()

SEARCH_KEYBOARD = [['Искать!'],
                  ]

RESULTS_KEYBOARD = [['Следующий результат', 'Скачать',
                     'Цитировать', 'Предыдущий результат'],
                    ['Назад']]

SEARCH_MARKUP = ReplyKeyboardMarkup(SEARCH_KEYBOARD, one_time_keyboard=True)
RESULTS_MARKUP = ReplyKeyboardMarkup(RESULTS_KEYBOARD, one_time_keyboard=True)
db = database_class.DataBase(database_connection_settings)

def start(bot, update):
    """Starts conversation"""
    bot.send_message(chat_id=update.message.chat_id,
                     text="Привет! Я - Бот ScienceCamp и я помогу вам в ваших исследованиях."
                          " Просто введите ваш запрос и нажмите 'Искать!' на клавиатуре",
                     reply_markup=SEARCH_MARKUP)

    connection = db.make_connection()
    db.register_user(connection, update.message.chat_id, update.message.from_user['username'])
    db.close_connection(connection)

    return IDLE

def facts_to_str(user_data):
    """Converts facts into str"""
    facts = list()

    for key, value in user_data.items():
        facts.append('{} - {}'.format(key, value))

    return "\n".join(facts).join(['\n', '\n'])

def cite_it(bot, chat_id, doi):
    """Returns citation for given DOI"""
    # headers = {"content-type":"application/x-bibtex"}
    # resp = requests.get("https://doi.org/" + DOI, headers=headers)
    # return resp.content
    works = Works()
    if not works.agency(doi):
        bot.send_message(chat_id=chat_id,
                         text="Этот документ не входит в базу цитирования CrossRef..."
                        )
        return SEARCH_RESULTLS
    else:
        record = works.doi(doi)
        found, meta_bib = doi2bib.crossref.get_bib(doi)
        if not found:
            bot.send_message(chat_id=chat_id,
                             text="Документ не найден..."
                            )
            return SEARCH_RESULTLS
        bot.send_message(chat_id=chat_id,
                         text="Цитирование по CrossRef:"
                        )
        filename = doi.replace('/', '-')
        with open(os.path.join('downloads', filename+'.bib'), 'wb+') as downloaded_file:
            downloaded_file.write(meta_bib)
        bot.send_document(chat_id=chat_id,
                          document=open(os.path.join('downloads', filename+'.bib'), 'rb'),
                         )
        return SEARCH_RESULTLS

#@BotParser.check_url
def download_it(bot, update, article_url, doi, filename, context=None, user_data=None):
    """downloads a file via url and writes it to the local storage with given name"""
    session = requests.Session()
    response = session.get(article_url)
    user_data['capcha-response'] = response
    user_data['file-name'] = filename
    user_data['article-url'] = article_url
    user_data['session'] = session
    user_data['doi'] = doi
    # print(response.headers['Content-Type'].split(' ')[0])
    if response.headers['Content-Type'].split(' ')[0] == 'application/pdf':
        with open(os.path.join('downloads', filename+'.pdf'), 'wb+') as downloaded_file:
            downloaded_file.write(response.content)
        bot.send_document(chat_id=update.message.chat_id,
                          document=open(os.path.join('downloads', filename+'.pdf'), 'rb'),
                          timeout=1000
                         )
        return SEARCH_RESULTLS
    else:
        print("Я попал в else download)it")
        func_resp = BotParser.parse_captcha(article_url, response.text)
        image_url = func_resp[0]
        id = func_resp[1]
        bot.send_photo(chat_id=update.message.chat_id,
                       photo=image_url,
                       caption="Решите следующую капчу и напишите ответ в сообщении:",
                       timeout=1000
                      )
        # reply = update.message.text
        user_data['capcha-id'] = id
        # session.post(article_url, data={"id": id, "answer": reply})
        #response = session.get(article_url)
        #user_data['capcha-response'] = response
        return TYPING_REPLY

def parsing_capcha(bot, update, context=None, user_data=None):
    """Handles capcha input"""
    response = user_data['capcha-response']
    filename = user_data['file-name']
    article_url = user_data['article-url']
    session = user_data['session']
    if not user_data.get('count-tries'):
        user_data['count-tries'] = 0
    id = user_data['capcha-id']
    print('Переданный id: ' + str(id))
    reply = update.message.text
    session.post(article_url, data={"id": id, "answer": reply})
    response = session.get(article_url)

    print(response.headers['Content-Type'].split(' ')[0])

    if response.headers['Content-Type'].split(' ')[0] == 'application/pdf':
        print('jojojojojo')
        with open(os.path.join('downloads', filename+'.pdf'), 'wb+') as downloaded_file:
            downloaded_file.write(response.content)
        print('Я скачал документ и назвал его %s' %(filename))
        bot.send_document(chat_id=update.message.chat_id,
                        #   caption="А вот и файл:",
                          document=open(os.path.join('downloads', filename+'.pdf'), 'rb'),
                          timeout=1000
                         )
        return SEARCH_RESULTLS
    else:
        if response.status_code == 404:
            print('getting 404')

            doi = user_data['doi']
            connection = db.make_connection()
            new_article_url = BotParser._parse_scihub(doi)
            DataBase.update_url(connection, article_url, new_article_url)
            db.close_connection(connection)

            res = download_it(bot, update, new_article_url,
                              doi, user_data['file-name'], user_data=user_data)
            return res

        if user_data['count-tries'] < 3:
            print("gfgjgfcffghjgdsdfghgfdgh")
            func_resp = BotParser.parse_captcha(article_url, response.text)
            image_url = func_resp[0]
            id = func_resp[1]
            bot.send_photo(chat_id=update.message.chat_id,
                           photo=image_url,
                           caption="Решите следующую капчу и напишите ответ в сообщении:",
                           timeout=1000
                        #    reply_markup=telegram.ForceReply()
                          )

            #session.post(article_url, data={"id": id, "answer": reply})
            # response = session.get(article_url)
            # bot.send_message(chat_id=update.message.chat_id,
            #                  text="Неверно!",
            #                 )
            user_data['capcha-id'] = id
            user_data['count-tries'] += 1
            return TYPING_REPLY
        else:
            bot.send_message(chat_id=update.message.chat_id,
                         text="Статью не удалось скачать из-за недоступности URL.")
            user_data['count-tries'] = 0
            return SEARCH_RESULTLS

def results_to_str(search_results):
    """Converts search results into str"""
    html_pages = []
    with open('templates/response_template.md', 'r', encoding='UTF-8') as template_file:
        template = template_file.read()
        for result in search_results:
            key_words, title, authors, doi, annotation = result
            download_link = 'None'
            key_words, title, authors, doi, annotation, download_link = result
            # title, authors, DOI, annotation, download_link = result
            # html_pages.append(template.format(page_title=title,
            #                                   authors=authors,
            #                                   DOI=DOI,
            #                                   annotation=annotation,
            #                                   download_link=download_link,
            #                                  ))
            # filename = 'renders/{}.md'.format(DOI)
            # rendered_authors = ''.join(' * ' + author + '\n' for author in authors)
            file_content = template.format(page_title=title,
                                           authors=authors,#rendered_authors,
                                           DOI=doi,
                                           annotation=annotation,
                                           translation=TRANSLATOR.translate(annotation,
                                                                            dest='ru').text
                                           # download_link=download_link,
                                          )
            html_pages.append([file_content, download_link, 
                               doi, [key_words, title, authors,
                                     doi, annotation, download_link]])
    return html_pages

def render_message(key_words, title, authors, doi, annotation, download_link):
    """Renders metadata into telegram message"""
    with open('templates/response_template.md', 'r', encoding='UTF-8') as ifile:
        template = ifile.read()
        message_content = template.format(page_title=title,
                                          authors=authors,
                                          DOI=doi,
                                          annotation=annotation,
                                          translation=TRANSLATOR.translate(annotation,
                                                                           dest='ru').text
                                         )
    return message_content, download_link, \
        doi, [key_words, title, authors, \
            doi, annotation, download_link]

def back_to_idle(bot, update, context=None, user_data=None):
    """Returns to idle state"""
    bot.send_message(chat_id=update.message.chat_id,
                     text='Возвращаюсь в простой поиск.',
                     reply_markup=SEARCH_MARKUP)
    return IDLE

def received_search_results(bot, update, context=None, user_data=None):
    print('Ага!')
    """Shows results of the search one by one"""
    text = update.message.text
    if len(user_data['results']) == 0:
        if user_data.get('Запрос'):
            user_request = user_data['Запрос']
        else:
            user_request = facts_to_str(user_data)
        bot.send_message(chat_id=update.message.chat_id,
                         text="Ничего не найдено для '{}'...".format(
                             user_request), reply_markup=SEARCH_MARKUP)
        return IDLE
    else:
        if text == 'Следующий результат':
            if user_data['pagination'] >= len(user_data['results'])-1:
                if user_data.get('Запрос'):
                    bot.send_message(chat_id=update.message.chat_id,
                                    text="Ищу '{}'".format(user_data['Запрос']),
                                    reply_markup=RESULTS_MARKUP)
                    bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
                    # Some search actions
                    parser = BotParser(search_settings, db)
                    #TODO: Нужно добавить в поиск "перелистывание страниц", а пока вызывается старая функция parse
                    user_data['start-page'] += 1
                    results = parser.parse(user_data['Запрос'],
                                           update.message.chat_id,
                                           start_page=user_data['start-page'],
                                           max_articles=2
                                          )
                    print('Возвращенный результат: ' + str(results))
                    while results is None:
                        user_data['start-page'] += 1
                        results = parser.parse(user_data['Запрос'],
                                               update.message.chat_id,
                                               start_page=user_data['start-page'],
                                               max_articles=2
                                              )
                    user_data['results'] += results
            user_data['pagination'] += 1
            result = user_data['results'][user_data['pagination']]
            key_words, title, authors, doi, annotation, download_link = result
            bot.send_message(chat_id=update.message.chat_id,
                             text="Может вам подойдет это:\n",
                             reply_markup=RESULTS_MARKUP)
            bot.send_message(chat_id=update.message.chat_id,
                                text=render_message(key_words, title, authors, doi, annotation, download_link)[0],
                            #  parse_mode="MARKDOWN"
                            )
            bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
            parser = BotParser(search_settings, db)
            parser.register_watched(key_words, title,
                                    authors, doi, annotation, update.message.chat_id, download_link)
            bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
            bot.send_message(chat_id=update.message.chat_id,
                             text="Чтобы показать другие результаты, нажмите "
                                  "'Следующий результат' или 'Предыдущий результат'."
                                  " Для возврата к поиску, нажмите 'Назад'",
                             reply_markup=RESULTS_MARKUP)
            return SEARCH_RESULTLS
            # else:
                # bot.send_message(chat_id=update.message.chat_id,
                #                  text="Это последний из найденных результатов.")
        elif text == 'Скачать':
            key_words, title, authors, doi, annotation, download_link = user_data['results'][user_data['pagination']]
            try:
                bot.send_chat_action(chat_id=update.message.chat_id,
                                    action=telegram.ChatAction.UPLOAD_DOCUMENT)
                #hashlib.md5(bytes(doi, encoding='utf-8')).hexdigest()
                res = download_it(bot, update,
                                  render_message(key_words, title, authors,
                                                 doi, annotation, download_link)[1],
                                                 doi,
                                                 doi.replace('/', '-'),
                                                 user_data=user_data)
                return res
            except telegram.TelegramError:
                bot.send_message(chat_id=update.message.chat_id,
                                text="Что-то пошло не так. Я не смог отправить вам этот документ.")
                print(traceback.format_exc())
                return SEARCH_RESULTLS
        elif text == 'Цитировать':
            print("Я тут")
            key_words, title, authors, doi, annotation, download_link = user_data['results'][user_data['pagination']]
            return cite_it(bot, update.message.chat_id, doi)
            # try:
            #     cite_it(bot, update.message.chat_id, doi)
            #     return SEARCH_RESULTLS
            # except telegram.TelegramError:
            #     bot.send_message(chat_id=update.message.chat_id,
            #                      text="Что-то пошло не так. Я не смог отправить вам этот документ.")
            #     print(traceback.format_exc())
            #     return SEARCH_RESULTLS
        elif text == 'Предыдущий результат':
            if not user_data['pagination'] == 0:
                user_data['pagination'] -= 1
                key_words, title, authors, doi, annotation, download_link = user_data['results'][user_data['pagination']]
                bot.send_message(chat_id=update.message.chat_id,
                                 text="Может вам подойдет это:\n",
                                 reply_markup=RESULTS_MARKUP)
                bot.send_message(chat_id=update.message.chat_id,
                                 text=render_message(key_words, title, authors, doi, annotation, download_link)[0],
                                #  parse_mode="MARKDOWN"
                                )
                key_words, title, authors, doi, annotation, scihub_url = render_message(key_words, title, authors, doi, annotation, download_link)[-1]
                parser = BotParser(search_settings, db)
                parser.register_watched(key_words, title,
                                authors, doi, annotation, update.message.chat_id, scihub_url)
                bot.send_message(chat_id=update.message.chat_id,
                                 text="Чтобы показать другие результаты, нажмите "
                                      "'Следующий результат' или 'Предыдущий результат'."
                                      " Для возврата к поиску, нажмите 'Назад'",
                                 reply_markup=RESULTS_MARKUP)
            else:
                bot.send_message(chat_id=update.message.chat_id,
                                 text="Это первый из найденных результатов.")
        else:
            print(text)
            return SEARCH_RESULTLS

def idle_callback(bot, update, context=None, user_data=None):
    """Commits search type"""
    # user_data = context.user_data
    current_action = update.message.text
    if current_action == 'Искать!':
        # if not user_data and context:
        #     user_data = context.user_data
        if user_data.get('Запрос'):
            bot.send_message(chat_id=update.message.chat_id,
                             text="Ищу '{}'".format(user_data['Запрос']),
                             reply_markup=RESULTS_MARKUP)
            bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
            user_data['start-page'] = 0
            # Some search actions
            parser = BotParser(search_settings, db)
            results = parser.parse(user_data['Запрос'],
                                   update.message.chat_id,
                                   user_data['start-page'],
                                   2
                                  )
            while results is None:
                user_data['start-page'] += 1
                results = parser.parse(user_data['Запрос'],
                                       update.message.chat_id,
                                       start_page=user_data['start-page'],
                                       max_articles=2
                                      )
            user_data['results'] = results
            user_data['pagination'] = 0
            key_words, title, authors, doi, annotation, download_link = user_data['results'][user_data['pagination']]
            bot.send_message(chat_id=update.message.chat_id,
                             text="Может вам подойдет это:\n",
                             reply_markup=RESULTS_MARKUP,
                             )
            bot.send_message(chat_id=update.message.chat_id,
                             text=render_message(key_words, title, authors, 
                                                       doi, annotation, download_link)[0],
                            )

            # print(result[-1])
            key_words, title, authors, doi, annotation, scihub_url = render_message(key_words, title, authors, 
                                                                                    doi, annotation, download_link)[-1]
            parser.register_watched(key_words, title,
                                authors, doi, annotation, update.message.chat_id, scihub_url)
            bot.send_message(chat_id=update.message.chat_id,
                             text="Чтобы показать другие результаты, нажмите "
                                  "'Следующий результат' или 'Предыдущий результат'."
                                  " Для возврата к поиску, нажмите 'Назад'",
                             reply_markup=RESULTS_MARKUP)
            return SEARCH_RESULTLS
        else:
            bot.send_message(chat_id=update.message.chat_id,
                             text="Кажется вы пока не ввели никакого "
                                  "запроса или я что-то пропустил."
                                  " Отправьте ваш запрос в ответном сообщении.", 
                             reply_markup=SEARCH_MARKUP)
            return IDLE
    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text="Окей, чтобы осуществить поиск нажмите 'Искать!'",
                         reply_markup=SEARCH_MARKUP)
        user_data['Запрос'] = update.message.text

def done(bot, update, context=None, user_data=None):
    """Ends conversation."""
    # user_data = context.user_data
    if 'choice' in user_data:
        del user_data['choice']

    bot.send_message(chat_id=update.message.chat_id,
                     text="Работа с ботом завершена.")

    user_data.clear()
    return ConversationHandler.END

def error(bot, update, context=None, user_data=None):
    """Log Errors caused by Updates."""
    LOGGER.warning('Update "%s" caused error "%s"', update, error)

# def main():
#     parser = EntryPoint.MainParser(search_settings)
#     parser.start_console()

def main():
    """Bot's main function."""

    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # REQUEST_KWARGS = {
    #     'proxy_url': 'socks5://orbtl.s5.opennetwork.cc',
    #     'read_timeout': 6,
    #     'connect_timeout': 7,
    #     # 'port':'999',
    #     # Optional, if you need authentication:
    #     # 'username': '438137587',
    #     # 'password': 'zGJXDdm7',
    #     'urllib3_proxy_kwargs': {
    #         'username': '438137587',
    #         'password': 'zGJXDdm7',
    #     }
    # }
    updater = Updater(__TOCKEN__) #request_kwargs=REQUEST_KWARGS)
    # Get the dispatcher to register handlers
    bot_dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            IDLE : [MessageHandler(Filters.text,
                                   idle_callback,
                                   pass_user_data=True
                                  )],
            SEARCH_RESULTLS: [RegexHandler('^(Следующий результат|Скачать|Цитировать|Предыдущий результат)$',
                                           received_search_results,
                                           pass_user_data=True),
                              RegexHandler('^Назад$',
                                           back_to_idle,
                                           pass_user_data=True),
                             ],
            TYPING_REPLY: [MessageHandler(Filters.text,
                                          parsing_capcha,
                                          pass_user_data=True)
                          ],
            },

        fallbacks=[RegexHandler('^Закончить.$', done, pass_user_data=True)]
    )
    # bot_dispatcher.add_handler(CommandHandler("start", start))
    # bot_dispatcher.add_handler(CommandHandler("done", done))
    bot_dispatcher.add_handler(conv_handler)

    # log all errors
    bot_dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == "__main__":
    main()

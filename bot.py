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
from telegram import ParseMode
from telegram import ReplyKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)

from AppSettings import *
from BusinessLogic import EntryPoint

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

LOGGER = logging.getLogger(__name__)

IDLE, SEARCH_RESULTLS, CHOOSING, TYPING_CHOICE, SETTING_CHANGING, SETTING_CHOOSING, TYPING_REPLY = range(7)

RENDERED_VIEWS = []

SETTINGS_STRINGS = """\n
\r'Максимальное число результатов' - определяет, сколько статей найти (сейчас - {0});\n
\r'Стандартная база данных поиска' - определяет базу данных поиска:\n
    - 'https://pubs.acs.org/'\n
    - 'https://www.sciencedirect.com/'\n
сейчас - {1}\n
\n"""
STANDART_SETTINGS = {'Максимальное число результатов': 50,
                     'Стандартная база данных поиска':search_sources[0]}

with open('api.json', 'r', encoding='UTF-8') as file:
    data = json.loads(file.read())
    __TOCKEN__ = data['API']
    __BOT_NAME__ = data['BOT_NAME']
    __BOT_API_NAME__ = data['BOT_API_NAME']
    __URL__ = data['URL']
    del data

if not os.path.exists('renders'):
    os.mkdir('renders')
if not os.path.exists('downloads'):
    os.mkdir('downloads')

SEARCH_KEYBOARD = [['Искать!', 'Мои настройки'],
                   ['Продвинутый поиск']
                  ]

ADD_TAGS_KEYBOARD = [['Автор', 'Год издания', 'Название'],
                     ['Аннотация', 'Ключевые слова'],
                     ['Искать!'],
                     ['Что-то другое...', 'Назад']]

SETTINGS_KEYBOARD = [['Максимальное число результатов', 'Стандартная база данных поиска'], 
                     ['Назад']]

RESULTS_KEYBOARD = [['Следующий результат', 'Скачать', 'Предыдущий результат'], 
                    ['Назад']]

SEARCH_MARKUP = ReplyKeyboardMarkup(SEARCH_KEYBOARD, one_time_keyboard=True)
TAGS_MARKUP = ReplyKeyboardMarkup(ADD_TAGS_KEYBOARD, one_time_keyboard=True)
SETTINGS_MARKUP = ReplyKeyboardMarkup(SETTINGS_KEYBOARD, one_time_keyboard=True)
RESULTS_MARKUP = ReplyKeyboardMarkup(RESULTS_KEYBOARD, one_time_keyboard=True)

def start(bot, update):
    """Starts conversation"""
    bot.send_message(chat_id=update.message.chat_id,
                     text="Привет! Я - Бот ScienceCamp и я помогу вам в ваших исследованиях."
                          " Просто введите ваш запрос и нажмите 'Искать!' на клавиатуре",
                     reply_markup=SEARCH_MARKUP)
    return IDLE

# def start(bot, update, context):
#     """Starts conversation"""
#     update.message.reply_text("Привет! Я - ScienceCamp Бот и я помогу вам в ваших исследованиях."
#                               " Давай начнем! Какой вид поиска вы хотите произвести:",
#                               reply_markup=SEARCH_MARKUP)

#     return CHOOSING

def facts_to_str(user_data):
    """Converts facts into str"""
    facts = list()

    for key, value in user_data.items():
        facts.append('{} - {}'.format(key, value))

    return "\n".join(facts).join(['\n', '\n'])

def download_it(url, filename):
    response = requests.get(url, stream=True)
    with open(os.path.join('downloads', filename+'.pdf'), 'wb+') as file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                file.write(chunk)
    return os.path.join('downloads', filename+'.pdf')


def results_to_str(search_results):
    """Converts search results into str"""
    html_pages = []
    with open('templates/response_template.md', 'r', encoding='UTF-8') as ifile:
        template = ifile.read()
        for result in search_results:
            title, authors, DOI, annotation, download_link = result
            # html_pages.append(template.format(page_title=title,
            #                                   authors=authors,
            #                                   DOI=DOI,
            #                                   annotation=annotation,
            #                                   download_link=download_link,
            #                                  ))
            filename = 'renders/{}.md'.format(DOI)
            html_pages.append([filename, download_link, DOI])
            rendered_authors = ''.join(' * ' + author + '\n' for author in authors)
            with open(filename, 'w+', encoding='UTF-8') as ofile:
                ofile.write(template.format(page_title=title,
                                            authors=rendered_authors,
                                            DOI=DOI,
                                            annotation=annotation,
                                            # download_link=download_link,
                                            ))
    return html_pages

def back_to_idle(bot, update, context=None, user_data=None):
    """Returns to idle state"""
    bot.send_message(chat_id=update.message.chat_id,
                     text='Возвращаюсь в простой поиск.',
                     reply_markup=SEARCH_MARKUP)
    return IDLE

def regular_choice(bot, update, context=None, user_data=None):
    """Gets regular category from the keyboard for extended search"""
    global RENDERED_VIEWS

    text = update.message.text
    # if user_data:
    #     user_data['choice'] = text
    user_data['choice'] = text
    if user_data.get('Запрос'):
        del user_data['Запрос']

    if text == 'Назад':
        bot.send_message(chat_id=update.message.chat_id,
                         text='Возвращаюсь в простой поиск.',
                         reply_markup=SEARCH_MARKUP)
        return IDLE
    elif text == 'Искать!':
        del user_data['choice']
        bot.send_message(chat_id=update.message.chat_id,
                         text="Я ищу:"
                         " {} "
                         "Подождите немного...".format(
                             facts_to_str(user_data)),
                         reply_markup=RESULTS_MARKUP)
        bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
        # parser = EntryPoint.MainParser(search_settings)
        # results = parser.search(user_data['Запрос'], max_res=50)
        results = [['Боба Фетт', ['ХЗ'], '3545465', 'нет', 'https://github.com/dhansel/Altair8800/raw/master/Documentation.pdf'],
                   ['Старый Штиблет', ['Сатана', 'Я'], '1244567', 'нет', 'https://github.com/dhansel/Altair8800/raw/master/Documentation.pdf'],
                   ['Водка, Черти, Пистолет', ['Я'], '454554', 'нет', 'https://github.com/dhansel/Altair8800/raw/master/Documentation.pdf']]
        RENDERED_VIEWS = results_to_str(results)
        user_data['results'] = RENDERED_VIEWS
        user_data['pagination'] = 0
        result = user_data['results'][user_data['pagination']]
        bot.send_message(chat_id=update.message.chat_id,
                         text="Может вам подойдет это:\n"
                              " {} \n"
                              "Чтобы показать другие результаты, нажмите "
                              "'Следующий результат' или 'Предыдущий результат'."
                              " Для возврата к поиску, нажмите 'Назад'".format(
                                  result[0]), reply_markup=RESULTS_MARKUP)
        return SEARCH_RESULTLS
    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text='Назовёте "{}"? Это может мне помочь!'.format(text.lower()))

        return TYPING_REPLY

def custom_choice(bot, update, context=None, user_data=None):
    """Adds custom category to the context"""
    bot.send_message(chat_id=update.message.chat_id,
                     text='Окей, сначала скажи что это будет, '
                          'например: "DOI"')

    return TYPING_CHOICE

def received_information(bot, update, context=None, user_data=None):
    """Shows what context has been formed"""
    # user_data = context.user_data
    text = update.message.text
    category = user_data['choice']
    user_data[category] = text
    del user_data['choice']

    bot.send_message(chat_id=update.message.chat_id,
                     text="Окей! Вы сказали, что мы посмотрим на:"
                          "{}"
                          "Вы можете упомянуть что-то еще или сменить тему разговора.".format(
                              facts_to_str(user_data)), reply_markup=TAGS_MARKUP)

    return CHOOSING

def received_search_results(bot, update, context=None, user_data=None):
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
            if user_data['pagination'] < len(user_data['results'])-1:
                user_data['pagination'] += 1
                result = user_data['results'][user_data['pagination']]
                bot.send_message(chat_id=update.message.chat_id,
                                 text="Может вам подойдет это:\n",
                                 reply_markup=RESULTS_MARKUP)
                bot.send_message(chat_id=update.message.chat_id,
                                 text=open(result[0], 'r', encoding='UTF-8').read(),
                                #  parse_mode=ParseMode.MARKDOWN
                                )
                bot.send_message(chat_id=update.message.chat_id,
                                 text="Чтобы показать другие результаты, нажмите "
                                      "'Следующий результат' или 'Предыдущий результат'."
                                      " Для возврата к поиску, нажмите 'Назад'",
                                 reply_markup=RESULTS_MARKUP)
            else:
                bot.send_message(chat_id=update.message.chat_id,
                                 text="Это последний из найденных результатов.")
        elif text == 'Скачать':
            result = user_data['results'][user_data['pagination']]
            try:
                bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.UPLOAD_DOCUMENT)
                local_file = download_it(result[1], result[2])
                bot.send_document(chat_id=update.message.chat_id,
                                #   caption="А вот и файл:",
                                  document=open(local_file, 'rb'),
                                 )
            except telegram.TelegramError:
                bot.send_message(chat_id=update.message.chat_id,
                                 text="Что-то пошло не так. Я не смог отправить вам этот документ.")
                print(traceback.format_exc())
        elif text == 'Предыдущий результат':
            if not user_data['pagination'] == 0:
                user_data['pagination'] -= 1
                result = user_data['results'][user_data['pagination']]
                bot.send_message(chat_id=update.message.chat_id,
                                 text="Может вам подойдет это:\n",
                                 reply_markup=RESULTS_MARKUP)
                bot.send_message(chat_id=update.message.chat_id,
                                 text=open(result[0], 'r', encoding='UTF-8').read(),
                                #  parse_mode=ParseMode.MARKDOWN
                                )
                bot.send_message(chat_id=update.message.chat_id,
                                 text="Чтобы показать другие результаты, нажмите "
                                      "'Следующий результат' или 'Предыдущий результат'."
                                      " Для возврата к поиску, нажмите 'Назад'",
                                 reply_markup=RESULTS_MARKUP)
            else:
                bot.send_message(chat_id=update.message.chat_id,
                                 text="Это первый из найденных результатов.")
        return SEARCH_RESULTLS

def idle_callback(bot, update, context=None, user_data=None):
    """Commits search type"""
    global RENDERED_VIEWS

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
            # Some search actions
            # parser = EntryPoint.MainParser(search_settings)
            # results = parser.search(user_data['Запрос'], max_res=50)
            results = [['Боба Фетт', ['ХЗ'], '435465', 'нет', 'https://github.com/dhansel/Altair8800/raw/master/Documentation.pdf'],
                       ['Старый Штиблет', ['Сатана', 'Я'], '2434565', 'нет', 'https://github.com/dhansel/Altair8800/raw/master/Documentation.pdf'],
                       ['Водка, Черти, Пистолет', ['Я'], '454554', 'нет', 'https://github.com/dhansel/Altair8800/raw/master/Documentation.pdf']]
            RENDERED_VIEWS = results_to_str(results)
            user_data['results'] = RENDERED_VIEWS
            user_data['pagination'] = 0
            result = user_data['results'][user_data['pagination']]
            bot.send_message(chat_id=update.message.chat_id,
                             text="Может вам подойдет это:\n",
                             reply_markup=RESULTS_MARKUP)
            bot.send_message(chat_id=update.message.chat_id,
                             text=open(result[0], 'r', encoding='UTF-8').read(),
                            #  parse_mode='MARKDOWN'
                            )
            # bot.send_document(chat_id=update.message.chat_id,
            #                   caption=open(result, 'r', encoding='UTF-8').read(),
            #                   document=open(result, 'rt').read(),
            #                   parse_mode=ParseMode.MARKDOWN)
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
    elif current_action == 'Продвинутый поиск':
        bot.send_message(chat_id=update.message.chat_id,
                         text="Выбран продвинутый поиск.",
                         reply_markup=TAGS_MARKUP)
        return CHOOSING
    elif current_action == 'Мои настройки':
        # if not user_data and context:
        #     user_data = context.user_data
        if not user_data.get('settings'):
            user_data['settings'] = STANDART_SETTINGS
        bot.send_message(chat_id=update.message.chat_id,
                         text="Загружаю настройки: \n {}".format(
                             SETTINGS_STRINGS.format(user_data['settings'].get(
                                 'Максимальное число результатов'),
                                                     user_data['settings'].get(
                                                         'Стандартная база данных поиска')
                                                    )),
                         reply_markup=SETTINGS_MARKUP)
        # Settings
        return SETTING_CHOOSING
    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text="Окей, чтобы осуществить поиск нажмите 'Искать!'",
                         reply_markup=SEARCH_MARKUP)
        user_data['Запрос'] = update.message.text


def settings_callback(bot, update, context=None, user_data=None):
    """Changes settings"""
    text = update.message.text
    if user_data:
        user_data['choice'] = text
    else:
        context.user_data['choice'] = text
    if text == 'Назад':
        bot.send_message(chat_id=update.message.chat_id,
                         text='Завершаем смену настроек', reply_markup=SEARCH_MARKUP,
                         disable_web_page_preview=True)
        return IDLE
    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text='Назовёте {}? '
                              'Просто напишите значение мне в ответ'.format(text.lower()),
                         reply_markup=SETTINGS_MARKUP, 
                         disable_web_page_preview=True)
        return SETTING_CHANGING

def received_setting_value(bot, update, context=None, user_data=None):
    """Shows what context has been formed"""
    # user_data = context.user_data
    text = update.message.text
    category = user_data['choice']
    if category == 'Максимальное число результатов':
        try:
            user_data['settings'][category] = int(text)
        except ValueError:
            bot.send_message(chat_id=update.message.chat_id,
                             text="Нельзя присваивать в 'Максимальное число результатов' НЕ ЧИСЛО.",
                             reply_markup=SETTINGS_MARKUP, 
                             disable_web_page_preview=True)
    elif category == 'Стандартная база данных поиска':
        if category not in search_sources:
            bot.send_message(chat_id=update.message.chat_id,
                             text="Я пока не умею работать "
                                  "с ресурсом '{0}'."
                                  " Выберите один из следующих: {1}".format(text,
                                                                            str(search_settings)), 
                             disable_web_page_preview=True)

    del user_data['choice']

    bot.send_message(chat_id=update.message.chat_id,
                     text="Окей! Теперь ваши настройки следующие:"
                          " {} "
                          "Вы можете упомянуть что-то еще или "
                          "сменить тему разговора нажав кнопку 'Назад'.".format(
                              facts_to_str(user_data['settings'])), reply_markup=SETTINGS_MARKUP, 
                     disable_web_page_preview=True)

    return SETTING_CHOOSING

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
    updater = Updater(__TOCKEN__,) #request_kwargs=REQUEST_KWARGS)
    # Get the dispatcher to register handlers
    bot_dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            IDLE : [MessageHandler(Filters.text,
                                   idle_callback,
                                   pass_user_data=True
                                  )],
            SEARCH_RESULTLS: [RegexHandler('^(Следующий результат|Скачать|Предыдущий результат)$',
                                           received_search_results,
                                           pass_user_data=True),
                              RegexHandler('^Назад$',
                                           back_to_idle,
                                           pass_user_data=True),
                             ],

            SETTING_CHOOSING: [RegexHandler('^(Максимальное число результатов|Стандартная база данных поиска|Назад)$',
                                            settings_callback,
                                            pass_user_data=True),
                              ],

            SETTING_CHANGING: [MessageHandler(Filters.text,
                                              received_setting_value,
                                              pass_user_data=True),
                              ],

            CHOOSING: [RegexHandler('^(Автор|Год издания|Название|Аннотация|Ключевые слова)$',
                                    regular_choice,
                                    pass_user_data=True),
                       RegexHandler('^Искать!$',
                                    regular_choice,
                                    pass_user_data=True),
                       RegexHandler('^Назад$',
                                    back_to_idle,
                                    pass_user_data=True),
                       RegexHandler('^Что-то еще...$',
                                    custom_choice,
                                    pass_user_data=True),
                      ],

            TYPING_CHOICE: [MessageHandler(Filters.text,
                                           regular_choice,
                                           pass_user_data=True),
                           ],

            TYPING_REPLY: [MessageHandler(Filters.text,
                                          received_information,
                                          pass_user_data=True),
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

# Список сайтов для поиска
search_sources = [
    'https://pubs.acs.org/',
    #'https://api.elsevier.com/content/search/sciencedirect'
]


# sci hub url
scihub_url = 'https://sci-hub.se/'


# Шаблоны регулярных выражений для поиска
patterns = {
    "author_parcing": r'([.\-\sA-Za-z]+),w*',
    "author": r'\w+[^\*&?!\d+\b\ufeff\b]',
    "doi": r'[^\bDOI\b:\s]+',
    'url': r'href=[\'"]?([^\'" >]+)'
}
headers={"Accept": "application/xml", "user-agent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) snap Chromium/75.0.3770.80 Chrome/75.0.3770.80 Safari/537.36'}
# Параметры поиска. Вы можете задать свои настройки.
search_settings = {
    "api_key": {'key_1': '519a4a4db985c8287d5b95e356efe86c', 'key_2': '357eef3f0ec4f4ebe247fb4aa12c2770'},
    "max_articles": 25,
    "sources": search_sources,
    "content_type": "all"  #TODO books, monography, articles
}

database_connection_settings = {
    'dbname': 'uquery_db',
    'user': 'danil',
    'password': '123',
    'host': 'localhost'
}
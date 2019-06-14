# Список сайтов для поиска
search_sources = [
    'https://pubs.acs.org/'
]

# sci hub url
scihub_url = 'https://sci-hub.se/'


# Шаблоны регулярных выражений для поиска
patterns = {
    "doi": r'[^\bDOI\b:\s]+',
    'url': r'href=[\'"]?([^\'" >]+)'
}

# Параметры поиска. Вы можете задать свои настройки.
search_settings = {
    "max_articles": 5,
    "sources": search_sources,
    "content_type": "all"  #TODO books, monography, articles
}

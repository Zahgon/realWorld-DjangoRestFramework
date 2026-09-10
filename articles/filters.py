"""
Query-string filtering for the article list.

The five parameters (``tag``, ``author``, ``favorited``, ``limit``, ``offset``)
are applied in that declared order, so ``limit`` slices before ``offset`` does.
``limit`` and ``offset`` are numeric; a non-numeric value is a validation error
and a negative one is a slicing error, exactly as before.
"""

from decimal import Decimal, InvalidOperation

NUMBER_FIELDS = ('limit', 'offset')
FIELDS = ('tag', 'author', 'favorited', 'limit', 'offset')


class FilterValidationError(Exception):
    """Raised when a numeric parameter is not a number."""

    def __init__(self, detail):
        self.detail = detail
        super().__init__(detail)


def _to_number(raw):
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return None


class ArticleFilter:
    """Mirrors the filter set the article list has always been wired to."""

    def __init__(self, params):
        self.params = params
        self.limit = None
        self.offset = None

        errors = {}
        for name in NUMBER_FIELDS:
            raw = params.get(name)
            if raw in (None, ''):
                continue
            value = _to_number(raw)
            if value is None:
                errors[name] = ['Enter a number.']
                continue
            setattr(self, name, value)
        if errors:
            raise FilterValidationError(errors)

    def filter(self, articles):
        articles = list(articles)

        tag = self.params.get('tag')
        if tag:
            articles = [a for a in articles if any(t.name == tag for t in a.tags)]

        author = self.params.get('author')
        if author:
            needle = author.lower()
            articles = [a for a in articles if needle in a.author.username.lower()]

        favorited = self.params.get('favorited')
        if favorited:
            needle = favorited.lower()
            articles = [a for a in articles
                        if any(needle in fan.username.lower() for fan in a.favorites)]

        if self.limit is not None:
            articles = articles[:_index(self.limit)]

        if self.offset is not None:
            articles = articles[_index(self.offset):]

        return articles


def _index(value):
    if value < 0:
        raise ValueError('Negative indexing is not supported.')
    return int(value)

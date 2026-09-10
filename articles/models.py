import re
import unicodedata
from datetime import datetime, timezone

import markdown
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base

article_favorites = Table(
    'articles_article_favorites',
    Base.metadata,
    Column('id', BigInteger, primary_key=True, autoincrement=True),
    Column('article_id', BigInteger, ForeignKey('articles_article.id', ondelete='CASCADE'), nullable=False),
    Column('user_id', BigInteger, ForeignKey('accounts_user.id', ondelete='CASCADE'), nullable=False),
)

article_tags = Table(
    'articles_article_tags',
    Base.metadata,
    Column('id', BigInteger, primary_key=True, autoincrement=True),
    Column('article_id', BigInteger, ForeignKey('articles_article.id', ondelete='CASCADE'), nullable=False),
    Column('tag_id', BigInteger, ForeignKey('articles_tag.id', ondelete='CASCADE'), nullable=False),
)


def slugify(value, allow_unicode=False):
    """The slug rule the stored slugs were produced with."""
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


class Tag(Base):
    __tablename__ = 'articles_tag'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, default='')
    slug: Mapped[str] = mapped_column(String(100), unique=True, default='')

    def __str__(self):
        return self.name


class Article(Base):
    __tablename__ = 'articles_article'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('accounts_user.id', ondelete='CASCADE'))
    title: Mapped[str] = mapped_column(String(150), unique=True, default='')
    summary: Mapped[str] = mapped_column(Text, default='')
    content: Mapped[str] = mapped_column(Text, default='')
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # The project has always written this once, at creation, and never again.
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    slug: Mapped[str] = mapped_column(String(255), unique=True, default='')

    author = relationship('User')
    tags = relationship('Tag', secondary=article_tags, lazy='selectin', order_by='Tag.id')
    favorites = relationship('User', secondary=article_favorites, lazy='selectin')

    def save(self):
        self.slug = slugify(self.title)

    def as_markdown(self):
        return markdown.markdown(self.content, safe_mode='escape', extensions=['extra'])

    def __str__(self):
        return self.title

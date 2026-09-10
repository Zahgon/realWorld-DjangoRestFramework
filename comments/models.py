from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base


class Comment(Base):
    __tablename__ = 'comments_comment'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('articles_article.id', ondelete='CASCADE'))
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('accounts_user.id', ondelete='CASCADE'))
    content: Mapped[str] = mapped_column(Text, default='')
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    article = relationship('Article', lazy='joined')
    author = relationship('User', lazy='joined')

    def __str__(self):
        return self.content

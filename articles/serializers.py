"""
Payload shapes for articles.

Field order is contract: an article is rendered as ``slug, title, description,
body, tagList, createdAt, updatedAt, favorited, favoritesCount, author``, and
its author block as ``username, bio, image, following``.
"""

from datetime import timezone

from pydantic import BaseModel, ConfigDict, Field

TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

ARTICLE_FIELDS = ['slug', 'title', 'description', 'body', 'tagList', 'createdAt',
                  'updatedAt', 'favorited', 'favoritesCount', 'author']
READ_ONLY_FIELDS = ['slug', 'createdAt', 'updatedAt', 'author']


def format_timestamp(value):
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc)
    return value.strftime(TIMESTAMP_FORMAT)


class ArticleSerializer(BaseModel):
    """Validates the writable half of an article payload."""

    model_config = ConfigDict(extra='ignore')

    title: str = Field(min_length=1, max_length=150)
    description: str = Field(min_length=1)
    body: str = Field(min_length=1)
    tagList: list[str] | None = None


class TagSerializer(BaseModel):
    tags: list[str]


def author_data(user, request_user=None):
    following = False
    if request_user is not None:
        following = any(follower.id == request_user.id for follower in user.followers)
    return {
        'username': user.username,
        'bio': user.bio,
        'image': user.image,
        'following': following,
    }


def article_data(article, request_user=None):
    favorited = False
    if request_user is not None:
        favorited = any(fan.id == request_user.id for fan in article.favorites)
    return {
        'slug': article.slug,
        'title': article.title,
        'description': article.summary,
        'body': article.content,
        'tagList': [tag.name for tag in article.tags],
        'createdAt': format_timestamp(article.created),
        'updatedAt': format_timestamp(article.updated),
        'favorited': favorited,
        'favoritesCount': len(article.favorites),
        'author': author_data(article.author, request_user),
    }

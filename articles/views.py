"""Article and tag endpoints.

Ported one-for-one from the original view set.  Every status code, response
envelope and swallowed exception is reproduced exactly, including the ones that
look like bugs: the article feed answers under a ``comments`` key, creating an
article without a ``tagList`` raises and is reported as 404, and favouriting an
already favourited article answers 200 with an error envelope.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.auth import current_user, current_user_or_none
from config.database import get_session
from config.parsers import parse_body, raw_body
from config.responses import api_response

from .filters import ArticleFilter
from .models import Article, Tag
from .serializers import ArticleSerializer, TagSerializer, article_data
from accounts.models import User

router = APIRouter()

BAD_REQUEST = {"errors": {"body": ["Bad Request"]}}
UNAUTHORIZED_ACTION = {"errors": {"body": ["UnAuthorized Action"]}}
ALREADY_FAVOURITED = {"errors": {"body": ["Already Favourited Article"]}}


def _queryset(session):
    # The original declared no ordering, so rows arrive in whatever order the
    # database hands them back; reproducing that means not ordering either.
    return list(session.scalars(select(Article)))


def _get_article(session, slug):
    article = session.scalars(select(Article).where(Article.slug == slug)).first()
    if article is None:
        raise LookupError(slug)
    return article


def _tags_for(session, names):
    tags = []
    for name in names:
        tag = session.scalars(select(Tag).where(Tag.name == name)).first()
        if tag is None:
            tag = Tag(name=name, slug=name)
            session.add(tag)
            session.flush()
        tags.append(tag)
    return tags


@router.get("/articles")
def article_list(
    request: Request,
    session: Session = Depends(get_session),
    viewer=Depends(current_user_or_none),
):
    articles = ArticleFilter(dict(request.query_params)).filter(_queryset(session))
    return api_response([article_data(article, viewer) for article in articles])


@router.post("/articles")
def article_create(
    request: Request,
    body: bytes = Depends(raw_body),
    session: Session = Depends(get_session),
    user=Depends(current_user),
):
    try:
        payload = parse_body(request, body)["article"]
        serializer = ArticleSerializer(**payload)
        tags = serializer.tagList
        if tags is None:
            raise KeyError("tags")
        article = Article(
            author=user,
            title=serializer.title,
            summary=serializer.description,
            content=serializer.body,
        )
        article.save()
        article.tags.extend(_tags_for(session, tags))
        session.add(article)
        session.commit()
        session.refresh(article)
        return api_response({"article": article_data(article, user)}, status_code=201)
    except Exception:
        session.rollback()
        return api_response(BAD_REQUEST, status_code=404)


@router.get("/articles/feed")
def article_feed(
    request: Request,
    session: Session = Depends(get_session),
    user=Depends(current_user),
):
    try:
        followed = [
            candidate
            for candidate in session.scalars(select(User)).all()
            if any(follower.id == user.id for follower in candidate.followers)
        ]
        followed_ids = {candidate.id for candidate in followed}
        articles = [
            article
            for article in sorted(_queryset(session), key=lambda a: a.created, reverse=True)
            if article.author_id in followed_ids
        ]
        articles = ArticleFilter(dict(request.query_params)).filter(articles)
        payload = [article_data(article, user) for article in articles]
        return api_response({"comments": payload, "articleCount": len(payload)})
    except Exception:
        return api_response(BAD_REQUEST, status_code=404)


@router.get("/articles/{slug}")
def article_retrieve(
    slug: str,
    session: Session = Depends(get_session),
    viewer=Depends(current_user_or_none),
):
    try:
        article = _get_article(session, slug)
        return api_response({"article": article_data(article, viewer)})
    except Exception:
        return api_response(BAD_REQUEST, status_code=404)


@router.put("/articles/{slug}")
def article_update(
    slug: str,
    request: Request,
    body: bytes = Depends(raw_body),
    session: Session = Depends(get_session),
    user=Depends(current_user),
):
    try:
        article = _get_article(session, slug)
        if article.author_id != user.id:
            return api_response(UNAUTHORIZED_ACTION, status_code=401)
        payload = parse_body(request, body)["article"]
        serializer = ArticleSerializer(**payload)
        tags = serializer.tagList
        if tags is None:
            raise KeyError("tags")
        article.title = serializer.title
        article.summary = serializer.description
        article.content = serializer.body
        article.save()
        article.tags.clear()
        article.tags.extend(_tags_for(session, tags))
        session.commit()
        session.refresh(article)
        return api_response({"article": article_data(article, user)})
    except Exception:
        session.rollback()
        return api_response(BAD_REQUEST, status_code=404)


@router.delete("/articles/{slug}")
def article_destroy(
    slug: str,
    session: Session = Depends(get_session),
    user=Depends(current_user),
):
    try:
        article = _get_article(session, slug)
        if article.author_id != user.id:
            return api_response(UNAUTHORIZED_ACTION, status_code=401)
        session.delete(article)
        session.commit()
        return api_response(status_code=200)
    except Exception:
        session.rollback()
        return api_response(BAD_REQUEST, status_code=404)


@router.post("/articles/{slug}/favorite")
def article_favorite(
    slug: str,
    session: Session = Depends(get_session),
    user=Depends(current_user),
):
    try:
        article = _get_article(session, slug)
        if any(fan.id == user.id for fan in article.favorites):
            return api_response(ALREADY_FAVOURITED)
        article.favorites.append(session.get(User, user.id))
        session.commit()
        session.refresh(article)
        return api_response({"article": article_data(article, user)})
    except Exception:
        session.rollback()
        return api_response(BAD_REQUEST, status_code=404)


@router.delete("/articles/{slug}/favorite")
def article_unfavorite(
    slug: str,
    session: Session = Depends(get_session),
    user=Depends(current_user),
):
    try:
        article = _get_article(session, slug)
        fan = next(fan for fan in article.favorites if fan.id == user.id)
        article.favorites.remove(fan)
        session.commit()
        session.refresh(article)
        return api_response({"article": article_data(article, user)})
    except Exception:
        session.rollback()
        return api_response(BAD_REQUEST, status_code=404)


@router.get("/tags")
def tag_list(session: Session = Depends(get_session)):
    try:
        tags = [tag.name for tag in session.scalars(select(Tag).order_by(Tag.id))]
        return api_response(TagSerializer(tags=tags).model_dump())
    except Exception:
        return api_response(BAD_REQUEST, status_code=404)

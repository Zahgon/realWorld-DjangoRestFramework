"""Comment endpoints.

Ported one-for-one from the original views.  Two oddities are preserved on
purpose: creating a comment answers 200 rather than 201, and deleting one
requires no authentication at all because the original delete view declared no
permission classes.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.auth import current_user, current_user_or_none
from config.database import get_session
from config.parsers import parse_body, raw_body
from config.responses import api_response

from articles.models import Article

from .models import Comment
from .serializers import CommentSerializer, comment_data

router = APIRouter()

BAD_REQUEST = {"errors": {"body": ["Bad Request"]}}


def _get_article(session, slug):
    article = session.scalars(select(Article).where(Article.slug == slug)).first()
    if article is None:
        raise LookupError(slug)
    return article


@router.get("/articles/{slug}/comments")
def comment_list(
    slug: str,
    session: Session = Depends(get_session),
    viewer=Depends(current_user_or_none),
):
    try:
        article = _get_article(session, slug)
        comments = session.scalars(
            select(Comment)
            .where(Comment.article_id == article.id)
            .order_by(Comment.created.desc(), Comment.id.desc())
        ).all()
        return api_response({"comments": [comment_data(c, viewer) for c in comments]})
    except Exception:
        return api_response(BAD_REQUEST, status_code=404)


@router.post("/articles/{slug}/comments")
def comment_create(
    slug: str,
    request: Request,
    body: bytes = Depends(raw_body),
    session: Session = Depends(get_session),
    user=Depends(current_user),
):
    try:
        article = _get_article(session, slug)
        payload = parse_body(request, body)["comment"]
        serializer = CommentSerializer(**payload)
        comment = Comment(content=serializer.body, author=user, article=article)
        session.add(comment)
        session.commit()
        session.refresh(comment)
        return api_response({"comment": comment_data(comment, user)})
    except Exception:
        session.rollback()
        return api_response(BAD_REQUEST, status_code=404)


@router.delete("/articles/{slug}/comments/{id}")
def comment_destroy(
    slug: str,
    id: int,
    session: Session = Depends(get_session),
    viewer=Depends(current_user_or_none),
):
    try:
        article = _get_article(session, slug)
        comment = session.scalars(
            select(Comment).where(Comment.id == id, Comment.article_id == article.id)
        ).one()
        session.delete(comment)
        session.commit()
        return api_response(status_code=204)
    except Exception:
        session.rollback()
        return api_response(BAD_REQUEST, status_code=404)

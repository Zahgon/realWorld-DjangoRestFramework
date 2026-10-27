"""Account and profile endpoints.

Every handler keeps the response envelope, the status code and the
swallow-everything error behaviour of the implementation this was ported
from.  Where the original silently returned an odd status (a 202 on login,
a 200 carrying an error envelope on the profile list) the oddity is kept.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from config.auth import current_user, current_user_or_none
from config.database import get_session
from config.parsers import parse_body, raw_body
from config.responses import api_response
from config.security import access_token_for

from .models import User, UserManager
from .serializers import UserSerializer, profile_data, user_data

router = APIRouter()


def _user_payload(request_data):
    """`request.data.get('user')` - a non-dict wrapper raises, as before."""
    return request_data.get('user')


@router.post('/users')
def account_registration(
    request: Request,
    body: bytes = Depends(raw_body),
    session: Session = Depends(get_session),
):
    try:
        user_data_in = _user_payload(parse_body(request, body))
        serializer = UserSerializer(**user_data_in)
        manager = UserManager(session)
        user = manager.create_user(
            email=serializer.email,
            password=serializer.password,
            username=serializer.username,
            bio=serializer.bio,
            image=serializer.image,
        )
        session.commit()
        session.refresh(user)
        return api_response({"user": user_data(user)}, status_code=201)
    except Exception:
        session.rollback()
        return api_response(status_code=400)


@router.post('/users/login')
def account_login(
    request: Request,
    body: bytes = Depends(raw_body),
    session: Session = Depends(get_session),
):
    try:
        user_data_in = _user_payload(parse_body(request, body))
        user = session.scalars(
            select(User).where(User.email == user_data_in['email'])
        ).one_or_none()
        if user is None or not user.check_password(user_data_in['password']):
            raise ValueError('invalid credentials')
        if not user.is_active:
            raise ValueError('inactive user')
        payload = user_data(user)
        # UPDATE_LAST_LOGIN is on, so issuing the token touches the row.
        user.last_login = _now()
        payload['token'] = access_token_for(user)
        session.commit()
        return api_response({"user": payload}, status_code=202)
    except Exception:
        session.rollback()
        return api_response(status_code=400)


def _now():
    return datetime.now(timezone.utc)


@router.get('/user')
def user_view_get(user: User = Depends(current_user)):
    return api_response(user_data(user))


@router.put('/user')
def user_view_put(
    request: Request,
    body: bytes = Depends(raw_body),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    # No guard here in the original either: a missing key propagates.
    payload = _user_payload(parse_body(request, body))
    user.email = payload['email']
    user.bio = payload['bio']
    user.image = payload['image']
    session.commit()
    session.refresh(user)
    return api_response(user_data(user))


@router.get('/profiles')
def profile_list(
    request: Request,
    session: Session = Depends(get_session),
    viewer: User | None = Depends(current_user_or_none),
):
    # The router hands `username=None` to this handler, so the lookup below
    # always raises and the error envelope is returned with a 200.
    try:
        username = request.path_params.get('username')
        user = session.scalars(
            select(User).where(User.username == username)
        ).one()
        return api_response(profile_data(user, viewer))
    except Exception:
        return api_response({"errors": {"body": ["Invalid User"]}})


@router.post('/profiles')
def profile_create(
    request: Request,
    body: bytes = Depends(raw_body),
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    payload = parse_body(request, body)
    created = User(
        username=payload.get('username'),
        bio=payload.get('bio', ''),
        image=payload.get('image'),
    )
    session.add(created)
    session.commit()
    session.refresh(created)
    return api_response(profile_data(created, user), status_code=201)


def _get_profile(session, username):
    user = session.scalars(
        select(User).where(User.username == username)
    ).first()
    if user is None:
        raise NotFound()
    return user


class NotFound(Exception):
    detail = {"detail": "Not found."}


@router.get('/profiles/{username}')
def profile_retrieve(
    username: str,
    session: Session = Depends(get_session),
    viewer: User = Depends(current_user),
):
    return api_response(profile_data(_get_profile(session, username), viewer))


@router.delete('/profiles/{username}')
def profile_destroy(
    username: str,
    session: Session = Depends(get_session),
    viewer: User = Depends(current_user),
):
    session.delete(_get_profile(session, username))
    session.commit()
    return api_response(status_code=204)


@router.post('/profiles/{username}/follow')
def profile_follow(
    username: str,
    session: Session = Depends(get_session),
    follower: User = Depends(current_user),
):
    profile = _get_profile(session, username)
    if profile.id == follower.id:
        return api_response(
            {"errors": {"body": ["Invalid follow Request"]}}, status_code=400
        )
    if not any(f.id == follower.id for f in profile.followers):
        profile.followers.append(follower)
        session.commit()
        session.refresh(profile)
    return api_response({"profile": profile_data(profile, follower)})


@router.delete('/profiles/{username}/follow')
def profile_unfollow(
    username: str,
    session: Session = Depends(get_session),
    follower: User = Depends(current_user),
):
    profile = _get_profile(session, username)
    if profile.id == follower.id:
        return api_response(
            {"errors": {"body": ["Invalid follow Request"]}}, status_code=400
        )
    existing = [f for f in profile.followers if f.id == follower.id]
    if not existing:
        return api_response(
            {"errors": {"body": ["Invalid follow Request"]}}, status_code=400
        )
    profile.followers.remove(existing[0])
    session.commit()
    session.refresh(profile)
    return api_response({"profile": profile_data(profile, follower)})

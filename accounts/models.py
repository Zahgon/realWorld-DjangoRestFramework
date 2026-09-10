from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base
from config.security import check_password, make_password, make_unusable_password

user_followers = Table(
    'accounts_user_followers',
    Base.metadata,
    Column('id', BigInteger, primary_key=True, autoincrement=True),
    Column('from_user_id', BigInteger, ForeignKey('accounts_user.id', ondelete='CASCADE'), nullable=False),
    Column('to_user_id', BigInteger, ForeignKey('accounts_user.id', ondelete='CASCADE'), nullable=False),
)


class User(Base):
    __tablename__ = 'accounts_user'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    password: Mapped[str] = mapped_column(String(128), default='')
    last_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, default='')
    username: Mapped[str] = mapped_column(String(60), default='')
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    date_joined: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    bio: Mapped[str] = mapped_column(Text, default='')
    image: Mapped[str] = mapped_column(String(200), nullable=True)

    followers = relationship(
        'User',
        secondary=user_followers,
        primaryjoin=lambda: User.id == user_followers.c.from_user_id,
        secondaryjoin=lambda: User.id == user_followers.c.to_user_id,
        lazy='selectin',
    )

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def set_unusable_password(self):
        self.password = make_unusable_password()

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    @property
    def is_authenticated(self):
        return True

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

    def __str__(self):
        return self.email


class UserManager:
    """Creation helpers, kept as the model-level entry points they always were."""

    def __init__(self, session):
        self.session = session

    def create_user(self, email, password=None, **other_fields):
        user = User(email=email, **other_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        self.session.add(user)
        self.session.commit()
        return user

    def create_superuser(self, email, password=None, **other_fields):
        other_fields.setdefault('is_staff', True)
        other_fields.setdefault('is_superuser', True)
        other_fields.setdefault('is_active', True)

        if other_fields.get('is_staff') is not True:
            raise ValueError('Superuser must be assigned to is_staff=True.')
        if other_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must be assigned to is_superuser=True.')

        return self.create_user(email, password, **other_fields)

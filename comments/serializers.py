"""
Payload shape for comments.

Field order is contract: ``id, createdAt, updatedAt, body, author``.
"""

from pydantic import BaseModel, ConfigDict, Field

from articles.serializers import author_data, format_timestamp

COMMENT_FIELDS = ['id', 'createdAt', 'updatedAt', 'body', 'author']


class CommentSerializer(BaseModel):
    model_config = ConfigDict(extra='ignore')

    body: str = Field(min_length=1)


def comment_data(comment, request_user=None):
    return {
        'id': comment.id,
        'createdAt': format_timestamp(comment.created),
        'updatedAt': format_timestamp(comment.updated),
        'body': comment.content,
        'author': author_data(comment.author, request_user),
    }

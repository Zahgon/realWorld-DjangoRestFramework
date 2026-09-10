from config.testing import APITestCase, AccessToken, create, create_user
from config import status
from articles.models import Article
from comments.models import Comment


class CommentViewTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = create_user(
            username='testuser',
            password='testpassword',
            email='test@email.email'
        )
        self.access_token = str(AccessToken.for_user(self.user))
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.access_token)

        self.new_article_data = {
            'author': self.user,
            'title': 'Old Title',
            'summary': 'Old summary',
            'content': 'Old content',
            'slug': 'test-slug'
        }
        self.article = create(Article, **self.new_article_data)

    def test_get_comments_list(self):
        url = f'/api/articles/{self.article.slug}/comments'

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_comment(self):
        url = f'/api/articles/{self.article.slug}/comments'
        data = {
            'comment': {
                'body': 'This is a test comment'
            }
        }

        response = self.client.post(url, data=data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DeleteCommentViewTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = create_user(
            username='testuser',
            password='testpassword',
            email='email@email.email'
        )
        self.article = create(
            Article,
            title='Test Article',
            summary='test-summary',
            content='test-content',
            author=self.user
        )
        self.comment = create(
            Comment,
            article=self.article,
            author=self.user,
            content='Test comment'
        )

    def test_delete_comment(self):
        url = f'/api/articles/{self.article.slug}/comments/{self.comment.id}'

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class CommentSurfaceTestCase(APITestCase):
    """Covers the comment surface the inherited suite never reached."""

    def setUp(self):
        super().setUp()
        self.user = create_user(
            username='commenter',
            password='commenter-password',
            email='commenter@example.com',
        )
        self.access_token = str(AccessToken.for_user(self.user))
        self.auth = {'Authorization': 'Token ' + self.access_token}
        self.article = create(
            Article,
            author=self.user,
            title='Commented article',
            summary='A summary',
            content='Some content',
        )
        self.url = f'/api/articles/{self.article.slug}/comments'

    def test_comment_str(self):
        comment = create(
            Comment, article=self.article, author=self.user, content='A comment'
        )
        self.assertEqual(str(comment), 'A comment')

    def test_comments_come_back_newest_first(self):
        self.client.post(self.url, data={'comment': {'body': 'first'}}, headers=self.auth)
        self.client.post(self.url, data={'comment': {'body': 'second'}}, headers=self.auth)
        response = self.client.get(self.url)
        bodies = [item['body'] for item in response.json()['comments']]
        self.assertEqual(bodies, ['second', 'first'])

    def test_comment_keys_and_author_block(self):
        self.client.post(self.url, data={'comment': {'body': 'a body'}}, headers=self.auth)
        response = self.client.get(self.url)
        comment = response.json()['comments'][0]
        self.assertEqual(
            list(comment.keys()), ['id', 'createdAt', 'updatedAt', 'body', 'author']
        )
        self.assertEqual(
            list(comment['author'].keys()), ['username', 'bio', 'image', 'following']
        )

    def test_create_returns_two_hundred_not_two_hundred_and_one(self):
        response = self.client.post(
            self.url, data={'comment': {'body': 'a body'}}, headers=self.auth
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(response.json().keys()), ['comment'])

    def test_create_without_a_body(self):
        response = self.client.post(self.url, data={'comment': {}}, headers=self.auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {'errors': {'body': ['Bad Request']}})

    def test_list_for_an_unknown_article(self):
        response = self.client.get('/api/articles/no-such-slug/comments')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {'errors': {'body': ['Bad Request']}})

    def test_delete_an_unknown_comment(self):
        response = self.client.delete(f'{self.url}/999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_without_authentication(self):
        response = self.client.post(self.url, data={'comment': {'body': 'a body'}})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.headers['Allow'], 'GET, POST, HEAD, OPTIONS')

    def test_head_needs_authentication_because_the_check_names_get_literally(self):
        response = self.client.head(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_options_describes_the_endpoint(self):
        response = self.client.options(self.url, headers=self.auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload['name'], 'Comment')
        self.assertEqual(payload['renders'], ['application/json', 'text/html'])
        self.assertEqual(
            payload['parses'],
            [
                'application/json',
                'application/x-www-form-urlencoded',
                'multipart/form-data',
            ],
        )
        self.assertEqual(
            sorted(payload['actions']['POST'].keys()),
            ['author', 'body', 'createdAt', 'id', 'updatedAt'],
        )

from config.testing import APITestCase, APIClient, AccessToken, create, create_user, session
from config import status
from articles.models import Article


class ArticleViewSetTest(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = create_user(
            username='testuser', email='test@email@test', password='testpassword'
            )
        self.access_token = str(AccessToken.for_user(self.user))

        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.access_token
        )
        self.article_data = {
            "article": {
                "title": "How dragon",
                "description": "Ever wonder how?",
                "body": "You have to believe",
                "tagList": ["rs", "ans", "dragons"]
            }
        }

        self.article_create_data = {
            'author': self.user, 
            'title' :'Old Title', 
            'summary' : 'Old summary',
            'content' : 'Old content',
            'slug' : 'test-slug'
        }

    def test_get_articles(self):
        url = '/api/articles'
        new_client = APIClient()

        response = new_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_article_feed(self):
        url = '/api/articles/feed'

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_article(self):
        url = '/api/articles'

        response = self.client.post(url, data=self.article_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_article(self):
        article = create(Article, **self.article_create_data)
        url = f'/api/articles/{article.slug}'

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_article(self):
        article = create(Article, **self.article_create_data)
        url = f'/api/articles/{article.slug}'
        updated_article_data = {
            "article": {
                "slug": "how-to-train-your-dragon",
                "title": "Updating how to train you dragon",
                "description": "Ever wonder how dragon",
                "body": "Believe in being updated lower and lower",
                "tagList": ["34-love"]
            }
        }

        response = self.client.put(url, data=updated_article_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_article(self):
        article = create(
            Article,
            author=self.user,
            title='Old Title',
            summary='Old summary',
            content='Old content',
            slug='test-slug'
        )
        url = f'/api/articles/{article.slug}'

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_favorite_article(self):
        article = create(Article, **self.article_create_data)
        url = f'/api/articles/{article.slug}/favorite'

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unfavorite_article(self):
        article = create(Article, **self.article_create_data)
        article.favorites.append(self.user)
        session.commit()
        url = f'/api/articles/{article.slug}/favorite'

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TagViewSet(APITestCase):
    def test_list_tags(self):
        url = '/api/tags'

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ArticleSurfaceTestCase(APITestCase):
    """Covers the article surface the inherited suite never reached.

    Every expectation here was taken from the recorded responses of the original
    application, including the ones that look wrong, so the migration is held to
    what was observed rather than to what a framework would prefer to do.
    """

    def setUp(self):
        super().setUp()
        self.author = create_user(
            username='author', email='author@example.com', password='author-password'
        )
        self.reader = create_user(
            username='reader', email='reader@example.com', password='reader-password'
        )
        self.auth = {'Authorization': 'Token ' + str(AccessToken.for_user(self.author))}
        self.reader_auth = {
            'Authorization': 'Token ' + str(AccessToken.for_user(self.reader))
        }
        self.article = create(
            Article,
            author=self.author,
            title='A tagged article',
            summary='A summary',
            content='Some content',
        )
        self.client.post(
            '/api/articles',
            data={
                'article': {
                    'title': 'Second article',
                    'description': 'Second summary',
                    'body': 'Second body',
                    'tagList': ['dragons', 'training'],
                }
            },
            headers=self.auth,
        )

    def test_article_str(self):
        self.assertEqual(str(self.article), 'A tagged article')

    def test_tag_str(self):
        from articles.models import Tag

        tag = session.query(Tag).filter(Tag.name == 'dragons').one()
        self.assertEqual(str(tag), 'dragons')

    def test_as_markdown(self):
        rendered = self.article.as_markdown()
        self.assertIn('Some content', rendered)

    def test_model_delete(self):
        self.article.delete()
        response = self.client.get(f'/api/articles/{self.article.slug}')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_article_list_is_a_bare_array(self):
        response = self.client.get('/api/articles')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertIsInstance(payload, list)
        self.assertEqual(
            list(payload[0].keys()),
            [
                'slug',
                'title',
                'description',
                'body',
                'tagList',
                'createdAt',
                'updatedAt',
                'favorited',
                'favoritesCount',
                'author',
            ],
        )
        self.assertEqual(
            list(payload[0]['author'].keys()), ['username', 'bio', 'image', 'following']
        )

    def test_filter_by_tag(self):
        response = self.client.get('/api/articles?tag=dragons')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['slug'] for item in response.json()], ['second-article'])

    def test_filter_by_author(self):
        response = self.client.get('/api/articles?author=author')
        self.assertEqual(len(response.json()), 2)

    def test_filter_by_favorited(self):
        self.client.post(f'/api/articles/{self.article.slug}/favorite', headers=self.reader_auth)
        response = self.client.get('/api/articles?favorited=reader')
        self.assertEqual([item['slug'] for item in response.json()], ['a-tagged-article'])

    def test_filter_by_limit(self):
        response = self.client.get('/api/articles?limit=1')
        self.assertEqual(len(response.json()), 1)

    def test_filter_by_offset(self):
        response = self.client.get('/api/articles?offset=1')
        self.assertEqual(len(response.json()), 1)

    def test_filter_by_limit_zero(self):
        response = self.client.get('/api/articles?limit=0')
        self.assertEqual(response.json(), [])

    def test_filter_by_a_limit_that_is_not_a_number(self):
        response = self.client.get('/api/articles?limit=abc')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {'limit': ['Enter a number.']})
        self.assertEqual(response.headers['Allow'], 'GET, POST')

    def test_filter_by_a_negative_limit_is_a_server_error(self):
        response = self.client.get('/api/articles?limit=-1')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.headers['Content-Type'], 'text/html; charset=utf-8')

    def test_unknown_slug(self):
        response = self.client.get('/api/articles/no-such-slug')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {'errors': {'body': ['Bad Request']}})

    def test_create_without_a_tag_list(self):
        response = self.client.post(
            '/api/articles',
            data={
                'article': {
                    'title': 'No tags',
                    'description': 'No tags',
                    'body': 'No tags',
                }
            },
            headers=self.auth,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {'errors': {'body': ['Bad Request']}})

    def test_create_with_a_duplicate_title(self):
        response = self.client.post(
            '/api/articles',
            data={
                'article': {
                    'title': 'Second article',
                    'description': 'Again',
                    'body': 'Again',
                    'tagList': [],
                }
            },
            headers=self.auth,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_as_someone_who_is_not_the_author(self):
        response = self.client.put(
            f'/api/articles/{self.article.slug}',
            data={
                'article': {
                    'title': 'Hijacked',
                    'description': 'Hijacked',
                    'body': 'Hijacked',
                    'tagList': [],
                }
            },
            headers=self.reader_auth,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.json(), {'errors': {'body': ['UnAuthorized Action']}}
        )

    def test_delete_as_someone_who_is_not_the_author(self):
        response = self.client.delete(
            f'/api/articles/{self.article.slug}', headers=self.reader_auth
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_favourite_twice(self):
        self.client.post(f'/api/articles/{self.article.slug}/favorite', headers=self.reader_auth)
        response = self.client.post(
            f'/api/articles/{self.article.slug}/favorite', headers=self.reader_auth
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(), {'errors': {'body': ['Already Favourited Article']}}
        )

    def test_unfavourite_something_never_favourited(self):
        response = self.client.delete(
            f'/api/articles/{self.article.slug}/favorite', headers=self.reader_auth
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_feed_returns_articles_under_the_comments_key(self):
        self.reader.followers.append(self.author)
        session.commit()
        response = self.client.get('/api/articles/feed', headers=self.auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(sorted(payload.keys()), ['articleCount', 'comments'])
        self.assertEqual(payload['articleCount'], len(payload['comments']))

    def test_feed_without_authentication(self):
        response = self.client.get('/api/articles/feed')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.headers['Allow'], 'GET')

    def test_tags_list(self):
        response = self.client.get('/api/tags')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'tags': ['dragons', 'training']})
        self.assertEqual(response.headers['Allow'], 'GET')

    def test_patch_is_not_allowed(self):
        response = self.client.patch('/api/articles', data={}, headers=self.auth)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.json(), {'detail': 'Method "PATCH" not allowed.'})
        self.assertEqual(response.headers['Allow'], 'GET, POST')

    def test_patch_without_authentication_is_refused_before_the_method_is_checked(self):
        response = self.client.patch('/api/articles', data={})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_head_on_the_article_list(self):
        response = self.client.head('/api/articles')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.headers['Allow'], 'GET, POST')
        self.assertEqual(response.content, b'')

    def test_options_on_the_article_list(self):
        response = self.client.options('/api/articles', headers=self.auth)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_an_unacceptable_accept_header(self):
        response = self.client.get(
            '/api/articles', headers={'Accept': 'application/xml'}
        )
        self.assertEqual(response.status_code, status.HTTP_406_NOT_ACCEPTABLE)
        self.assertEqual(
            response.json(), {'detail': 'Could not satisfy the request Accept header.'}
        )

    def test_a_format_suffix_is_accepted(self):
        response = self.client.get('/api/articles.json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json(), list)

    def test_a_trailing_slash_is_not_a_route(self):
        response = self.client.get('/api/articles/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.headers['Content-Type'], 'text/html; charset=utf-8')

    def test_an_unknown_route(self):
        response = self.client.get('/api/does-not-exist')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.headers['Content-Type'], 'text/html; charset=utf-8')

    def test_the_api_root_lists_only_profiles(self):
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(response.json().keys()), ['profiles'])
        self.assertTrue(response.json()['profiles'].endswith('/api/profiles'))

    def test_the_documentation_page(self):
        response = self.client.get('/swagger/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers['Content-Type'], 'text/html; charset=utf-8')
        self.assertEqual(response.headers['Allow'], 'GET, HEAD, OPTIONS')
        self.assertEqual(response.headers['Vary'], 'Accept, Cookie')

    def test_the_catch_all_serves_a_file_from_the_working_directory(self):
        response = self.client.get('/manage.py')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers['Content-Type'], 'text/x-python')
        self.assertEqual(
            response.headers['Content-Disposition'], 'inline; filename="manage.py"'
        )

    def test_the_catch_all_reports_a_missing_file(self):
        response = self.client.get('/no-such-file.txt')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.headers['Content-Type'], 'text/html; charset=utf-8')

    def test_the_catch_all_refuses_to_climb_out_of_the_directory(self):
        response = self.client.get('/../etc/passwd')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_the_application_starts_up(self):
        from fastapi.testclient import TestClient

        from config.main import app

        with TestClient(app) as client:
            self.assertEqual(client.get('/api/tags').status_code, status.HTTP_200_OK)

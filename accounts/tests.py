from config.testing import APITestCase, AccessToken, create_user, reverse, session
from config import status

from accounts.models import UserManager


class AccountRegistrationTestCase(APITestCase):
    def test_account_registration(self):
        url = '/api/users'
        user_data = {
            'user': {
                'email': 'test@example.com',
                'password': 'testpassword',
                'username': 'testuser'
            }
        }

        response = self.client.post(url, user_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_account_registration_invalid_data(self):
        url = '/api/users'
        invalid_user_data = {
            'user': { }
        }

        response = self.client.post(url, invalid_user_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AccountLoginTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.email = 'test@example.com'
        self.username = 'testuser'
        self.password = 'testpassword'
        self.user = create_user(
            email=self.email,
            username=self.username,
            password=self.password
        )
        self.url = '/api/users/login'

    def tearDown(self):
        self.user.delete
        super().tearDown()

    def test_account_login(self):
        login_data = {
            'user': {
                'email': self.email,
                'password': self.password
            }
        }

        response = self.client.post(self.url, login_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_account_login_invalid_data(self):
        invalid_login_data = {
            'user': { }
        }

        response = self.client.post(self.url, invalid_login_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserViewTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.email = 'test@example.com'
        self.username = 'testuser'
        self.password = 'testpassword'
        self.user = create_user(
            email=self.email,
            username=self.username,
            password=self.password
        )
        self.access_token = str(AccessToken.for_user(self.user))
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.access_token)
        self.url = reverse('user-account')

    def test_user_view_get(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_view_put(self):
        updated_email = 'updated@example.com'
        updated_bio = 'Updated bio'
        updated_image = 'http://example.com/updated-image.jpg'

        updated_user_data = {
            'user': {
                'email': updated_email,
                'bio': updated_bio,
                'image': updated_image
            }
        }

        response = self.client.put(self.url, updated_user_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProfileDetailViewTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self.email = 'test@example.com'
        self.username = 'testuser'
        self.password = 'testpassword'
        self.user = create_user(
            email=self.email,
            username=self.username,
            password=self.password
        )
        self.access_token = str(AccessToken.for_user(self.user))
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.access_token)
        self.url = f'/api/profiles/{self.user.username}'

    def test_profile_detail_view_get(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_profile_detail_view_follow(self):
        second_user = create_user(
            email='test2@gmail.com',
            username='test2user',
            password='password'
        )
        follow_url = f'/api/profiles/{second_user.username}/follow'

        response = self.client.post(follow_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_profile_detail_view_unfollow(self):
        second_user = create_user(
            email='test2@gmail.com',
            username='test2user',
            password='password'
        )
        second_user.followers.append(self.user)
        session.commit()
        unfollow_url = f'/api/profiles/{second_user.username}/follow'

        response = self.client.delete(unfollow_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AccountSurfaceTestCase(APITestCase):
    """Covers the parts of the account surface the inherited suite never reached.

    These cases were written from the recorded responses of the original
    application, so they hold the migration to the behaviour that was observed
    rather than to the behaviour of whatever framework serves it.
    """

    def setUp(self):
        super().setUp()
        self.user = create_user(
            email='surface@example.com', username='surface', password='surface-password'
        )
        self.access_token = str(AccessToken.for_user(self.user))
        self.auth = {'Authorization': 'Token ' + self.access_token}

    def test_user_model_surface(self):
        self.assertTrue(self.user.is_authenticated)
        self.assertEqual(self.user.get_full_name(), 'surface')
        self.assertEqual(self.user.get_short_name(), 'surface')
        self.assertEqual(str(self.user), 'surface@example.com')

    def test_unusable_password_never_matches(self):
        self.user.set_unusable_password()
        self.assertFalse(self.user.check_password('surface-password'))

    def test_create_superuser(self):
        admin = UserManager(session).create_superuser(
            email='admin@example.com', username='admin', password='admin-password'
        )
        session.commit()
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)

    def test_create_superuser_requires_staff(self):
        with self.assertRaises(ValueError):
            UserManager(session).create_superuser(
                email='nope@example.com',
                username='nope',
                password='nope-password',
                is_staff=False,
            )

    def test_response_header_block(self):
        response = self.client.get('/api/user', headers=self.auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [name.decode() for name, _ in response.headers.raw]
        self.assertEqual(
            names,
            [
                'Date',
                'Server',
                'Content-Type',
                'Vary',
                'Allow',
                'X-Frame-Options',
                'Content-Length',
                'X-Content-Type-Options',
                'Referrer-Policy',
                'Cross-Origin-Opener-Policy',
            ],
        )
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        self.assertEqual(response.headers['Vary'], 'Accept')
        self.assertEqual(response.headers['Allow'], 'GET, PUT, HEAD, OPTIONS')
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['Referrer-Policy'], 'same-origin')
        self.assertEqual(response.headers['Cross-Origin-Opener-Policy'], 'same-origin')

    def test_current_user_body(self):
        response = self.client.get('/api/user', headers=self.auth)
        self.assertEqual(
            response.json(),
            {
                'username': 'surface',
                'email': 'surface@example.com',
                'bio': '',
                'image': None,
            },
        )

    def test_missing_authorization(self):
        response = self.client.get('/api/user')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.json(),
            {'detail': 'Authentication credentials were not provided.'},
        )
        self.assertEqual(response.headers['WWW-Authenticate'], 'Token realm="api"')

    def test_bearer_scheme_is_not_accepted(self):
        response = self.client.get(
            '/api/user', headers={'Authorization': 'Bearer ' + self.access_token}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.json(),
            {'detail': 'Authentication credentials were not provided.'},
        )

    def test_authorization_without_a_value(self):
        response = self.client.get('/api/user', headers={'Authorization': 'Token'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.json(),
            {
                'detail': 'Authorization header must contain two space-delimited values',
                'code': 'bad_authorization_header',
            },
        )

    def test_authorization_with_three_parts(self):
        response = self.client.get('/api/user', headers={'Authorization': 'Token a b'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json()['code'], 'bad_authorization_header')

    def test_garbage_token(self):
        response = self.client.get('/api/user', headers={'Authorization': 'Token garbage'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.json(),
            {
                'detail': 'Given token not valid for any token type',
                'code': 'token_not_valid',
                'messages': [
                    {
                        'token_class': 'AccessToken',
                        'token_type': 'access',
                        'message': 'Token is invalid or expired',
                    }
                ],
            },
        )

    def test_user_put_without_every_key_is_a_server_error(self):
        response = self.client.put(
            '/api/user', data={'user': {'email': 'moved@example.com'}}, headers=self.auth
        )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.headers['Content-Type'], 'text/html; charset=utf-8')

    def test_registration_rejects_an_invalid_email(self):
        response = self.client.post(
            '/api/users',
            data={'user': {'email': 'not-an-email', 'password': 'p', 'username': 'u'}},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.content, b'')

    def test_registration_rejects_an_invalid_image(self):
        response = self.client.post(
            '/api/users',
            data={
                'user': {
                    'email': 'image@example.com',
                    'password': 'p',
                    'username': 'u',
                    'image': 'not-a-url',
                }
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_rejects_a_missing_wrapper(self):
        response = self.client.post(
            '/api/users', data={'email': 'flat@example.com'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_rejects_an_unparseable_body(self):
        response = self.client.post(
            '/api/users',
            data='not json at all',
            format=None,
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_rejects_an_unsupported_content_type(self):
        response = self.client.post(
            '/api/users',
            data='body',
            format=None,
            headers={'Content-Type': 'text/plain'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_rejects_an_absent_content_type(self):
        response = self.client.post(
            '/api/users', data='body', format=None, headers={'Content-Type': None}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_a_wrong_password(self):
        response = self.client.post(
            '/api/users/login',
            data={'user': {'email': 'surface@example.com', 'password': 'wrong'}},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.content, b'')

    def test_login_with_an_unknown_email(self):
        response = self.client.post(
            '/api/users/login',
            data={'user': {'email': 'nobody@example.com', 'password': 'p'}},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profiles_list_reports_an_invalid_user(self):
        response = self.client.get('/api/profiles')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'errors': {'body': ['Invalid User']}})
        self.assertEqual(response.headers['Allow'], 'GET, POST')

    def test_profile_create(self):
        response = self.client.post(
            '/api/profiles',
            data={'username': 'zed', 'bio': 'z', 'image': None},
            headers=self.auth,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json(),
            {'username': 'zed', 'bio': 'z', 'image': None, 'following': False},
        )

    def test_profile_destroy(self):
        other = create_user(
            email='other@example.com', username='other', password='other-password'
        )
        response = self.client.delete(f'/api/profiles/{other.username}', headers=self.auth)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_profile_unknown(self):
        response = self.client.get('/api/profiles/nobody', headers=self.auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json(), {'detail': 'Not found.'})

    def test_follow_yourself_is_refused(self):
        response = self.client.post(
            f'/api/profiles/{self.user.username}/follow', headers=self.auth
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(), {'errors': {'body': ['Invalid follow Request']}}
        )

    def test_unfollow_someone_you_do_not_follow(self):
        other = create_user(
            email='stranger@example.com', username='stranger', password='stranger-password'
        )
        response = self.client.delete(
            f'/api/profiles/{other.username}/follow', headers=self.auth
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(), {'errors': {'body': ['Invalid follow Request']}}
        )

from http import HTTPStatus

from django.core.cache import cache
from django.test import Client, TestCase

from ..models import Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',)
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',)
        cls.private_urls = (
            ('/create/', 'posts/create_post.html'),
            (f'/posts/{cls.post.id}/edit/', 'posts/create_post.html'))
        cls.public_urls = (
            ('/', 'posts/index.html'),
            (f'/group/{cls.group.slug}/', 'posts/group_list.html'),
            (f'/profile/{cls.user.username}/', 'posts/profile.html'),
            (f'/posts/{cls.post.id}/', 'posts/post_detail.html'))
        cls.redirect_urls = (
            ('/create/', '/auth/login/?next=/create/'),
            (f'/posts/{cls.post.id}/edit/',
             f'/auth/login/?next=/posts/{cls.post.id}/edit/'))

    def setUp(self):
        self.author = Client()
        self.author.force_login(user=self.post.author)
        cache.clear()

    def test_guests_urls_exist_at_desired_location(self):
        """Страницы доступны любому пользователю."""
        self.guest_client = Client()
        for url, __ in self.public_urls:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_and_edit_urls_exist_at_desired_location(self):
        """Страницы '/create/' и '/posts/<post_id>/edit/'
        доступны авторизованному автору поста.
        """
        for url, __ in self.private_urls:
            with self.subTest(url=url):
                response = self.author.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_and_edit_url_redirect_anonymous_on_login(self):
        """Страницы /create/ и '/posts/<post_id>/edit/' перенаправят
        анонимного пользователя на страницу логина.
        """
        self.guest_client = Client()
        for url, redirect in self.redirect_urls:
            with self.subTest(url=url):
                response = self.guest_client.get(url, follow=True)
                self.assertRedirects(
                    response, redirect)

    def test_edit_url_not_author_redirect_on_login(self):
        """Страница по адресу '/posts/<post_id>/edit/'при заходе
        не автора поста перенаправит на страницу описания поста.
        """
        self.authorized_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client.force_login(self.user)
        response = self.authorized_client.get(
            f'/posts/{self.post.id}/edit/', follow=True)
        self.assertRedirects(
            response, (f'/posts/{self.post.id}/'))

    def test_unexisting_page_returns_error(self):
        """Запрос к несуществующей странице возвращает ошибку 404."""
        response = self.author.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Follow, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',)
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=cls.uploaded,)

        cls.index_url = ('posts:index', 'posts/index.html', None)

        cls.group_url = ('posts:group_list', 'posts/group_list.html',
                         (cls.group.slug,))

        cls.profile_url = ('posts:profile', 'posts/profile.html',
                           (cls.user.username,))

        cls.post_detail_url = ('posts:post_detail', 'posts/post_detail.html',
                               (cls.post.id,))

        cls.create_post_url = ('posts:post_create', 'posts/create_post.html',
                               None)

        cls.edit_post_url = ('posts:post_edit', 'posts/create_post.html',
                             (cls.post.id,))

        cls.paginated_urls = (cls.index_url, cls.group_url, cls.profile_url)

        cls.create_edit_post_urls = (cls.create_post_url, cls.edit_post_url)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_paginator(self):
        """Паджинатор выводит нужное количество постов на страницу."""
        Post.objects.bulk_create(
            Post(author=self.user, text=f'Тестовый пост{i}', group=self.group)
            for i in range(13))

        for url, __, args in self.paginated_urls:
            with self.subTest(url=url):
                self.assertEqual(
                    len(self.client.get(
                        reverse(url, args=args)).context['page_obj']),
                    settings.POSTS_ON_PAGE)
                self.assertEqual(
                    len(self.client.get(
                        reverse(url, args=args)
                        + '?page=2').context['page_obj']),
                    4)

    def test_post_with_group_shows_correctly(self):
        """Пост с группой появляется на странице этой группы
        и не появляется на страницах других групп.
        """
        group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug2',
            description='Тестовое описание 2',)
        for url, __, args in self.paginated_urls:
            self.assertContains(
                self.authorized_client.get(reverse(url, args=args)),
                self.post)
        self.assertNotContains(self.authorized_client.get(
            reverse('posts:group_list',
                    args={group2.slug})), self.post)

    def test_pages_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for url, template, args in (self.paginated_urls
                                    + self.create_edit_post_urls
                                    + (self.post_detail_url,)):
            with self.subTest(url=url):
                response = self.authorized_client.get(reverse(url, args=args))
                self.assertTemplateUsed(response, template)
        error404_response = self.authorized_client.get(
            'core.views.page_not_found')
        self.assertTemplateUsed(error404_response, 'core/404.html')

    def test_pages_show_correct_context(self):
        """Шаблоны 'index', 'group_list', 'profile', 'post_detail'
        сформированы с правильным контекстом."""
        for url, __, args in (self.paginated_urls + (self.post_detail_url,)):
            request = self.authorized_client.get(reverse(url, args=args))
            if "page_obj" in request.context:
                post = request.context['page_obj'][0]
            else:
                post = request.context['post']
            self.assertEqual(post.author, self.post.author)
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.group, self.post.group)
            self.assertEqual(post.image, self.post.image)

    def test_create_and_edit_pages_show_correct_context(self):
        """Шаблон 'create_post' сформирован с правильным контекстом."""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField}
        for url, __, args in self.create_edit_post_urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(reverse(url, args=args))
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context.get(
                            'form').fields[value]
                        self.assertIsInstance(form_field, expected)
                        self.assertIsInstance(response.context.get('form'),
                                              PostForm)
        response = self.authorized_client.get(
            reverse('posts:post_edit', args={self.post.id}))
        self.assertIn('is_edit', response.context)
        self.assertIsInstance(response.context.get('is_edit'), bool)

    def test_index_cache_works(self):
        """После удаления поста он остается в кэше."""
        new_post = Post.objects.create(
            author=self.user,
            text='Пост для проверки кэша',
            group=self.group,
            image=self.uploaded,)
        content1 = self.authorized_client.get(reverse('posts:index')).content
        new_post.delete()
        content2 = self.authorized_client.get(reverse('posts:index')).content
        self.assertEqual(content1, content2)
        cache.clear()
        content3 = self.authorized_client.get(reverse('posts:index')).content
        self.assertNotEqual(content1, content3)


class FollowViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author',)
        cls.follower = User.objects.create_user(username='follower',)
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.follower_client = Client()
        self.follower_client.force_login(self.follower)

    def test_following_works_correctly(self):
        """Авторизованный пользователь может подписываться на
        других пользователей и отписываться."""
        follower_count = Follow.objects.count()
        response1 = self.follower_client.post(
            reverse('posts:profile_follow', args={self.author}))
        self.assertRedirects(
            response1, reverse('posts:profile', args={self.author}))
        self.assertEqual(Follow.objects.count(), follower_count + 1)
        response2 = self.follower_client.post(
            reverse('posts:profile_unfollow', args={self.author}))
        self.assertRedirects(
            response2, reverse('posts:profile', args={self.author}))
        self.assertEqual(Follow.objects.count(), follower_count)

    def test_post_shows_on_follow_page(self):
        """Новая запись автора появляется у подписчиков,
        но не у других пользователей."""
        self.follower_client.post(
            reverse('posts:profile_follow', args={self.author}))
        response_follower = self.follower_client.get(
            reverse('posts:follow_index'))
        self.assertContains(response_follower, self.post)
        response_not_follower = self.author_client.get(
            reverse('posts:follow_index'))
        self.assertNotContains(response_not_follower, self.post)

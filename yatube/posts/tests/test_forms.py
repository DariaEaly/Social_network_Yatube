import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        post_count = Post.objects.count()
        form_data = {
            'author': self.user,
            'text': 'Записанный в форму текст',
            'group': self.group.id,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             reverse('posts:profile',
                                     args={self.user.username}))
        self.assertEqual(Post.objects.count(), post_count + 1)
        post_first = Post.objects.first()
        self.assertEqual(form_data['text'], post_first.text)
        self.assertEqual(form_data['group'], post_first.group.id)
        self.assertEqual(form_data['author'], post_first.author)
        self.assertEqual('posts/small.gif', post_first.image)

    def test_edit_post(self):
        """При отправке валидной формы происходит изменение поста в БД."""
        post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            group=self.group,
        )
        post_count = Post.objects.count()
        form_data = {
            'text': 'Измененный тестовый пост',
            'group': self.group.id, }
        response = self.authorized_client.post(
            reverse('posts:post_edit', args={post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     args={post.id}))
        post_first = Post.objects.first()
        self.assertEqual(Post.objects.count(), post_count)
        self.assertEqual(form_data['text'], post_first.text)
        self.assertEqual(post.author, post_first.author)
        self.assertEqual(post.group, post_first.group)

    def test_create_post_as_guest(self):
        """Анонимный пользователь не сможет создать запись."""
        self.guest_client = Client()
        post_count = Post.objects.count()
        form_data = {
            'text': 'Записанный в форму текст',
            'group': self.group.id,
            'image': self.uploaded,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, f'{reverse("users:login")}'
            f'?next={reverse("posts:post_create")}')
        self.assertEqual(Post.objects.count(), post_count)

    def test_edit_post_as_guest(self):
        """Анонимный пользователь не сможет изменить запись."""
        self.guest_client = Client()
        post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            group=self.group
        )
        post_count = Post.objects.count()
        form_data = {
            'text': 'Измененный тестовый пост',
            'group': self.group.id}
        response = self.guest_client.post(
            reverse('posts:post_edit', args={post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, f'{reverse("users:login")}'
            f'?next={reverse("posts:post_edit", args={post.id})}')
        post_first = Post.objects.first()
        self.assertEqual(Post.objects.count(), post_count)
        self.assertEqual(post.text, post_first.text)
        self.assertEqual(post.author, post_first.author)
        self.assertEqual(post.group, post_first.group)


class CommentCreateFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
        )

    def test_comments_as_auth(self):
        """Авторизованный пользователь может комментировать посты."""
        comments_count = Comment.objects.count()
        commenter = User.objects.create_user(username='commenter')
        self.commenter_client = Client()
        self.commenter_client.force_login(commenter)
        form_data = {
            'author': commenter,
            'text': 'Комментарий',
            'post': self.post,
        }
        response = self.commenter_client.post(
            reverse('posts:add_comment', args={self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             reverse('posts:post_detail', args={self.post.id}))
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        comment = Comment.objects.first()
        self.assertEqual(form_data['text'], comment.text)
        self.assertEqual(form_data['author'], comment.author)
        self.assertEqual(form_data['post'], comment.post)
        post_detail = self.commenter_client.get(
            reverse('posts:post_detail', args={self.post.id}))
        self.assertContains(post_detail, comment)

    def test_comments_as_guest(self):
        """Анонимный пользователь не может комментировать посты."""
        comments_count = Comment.objects.count()
        self.guest_client = Client()
        form_data = {
            'text': 'Комментарий',
            'post': self.post,
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', args={self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, f'{reverse("users:login")}?next='
            f'{reverse("posts:post_detail", args={self.post.id})}comment/')
        self.assertEqual(Comment.objects.count(), comments_count)

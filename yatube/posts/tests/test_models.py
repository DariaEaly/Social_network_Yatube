from django.test import TestCase

from ..models import Group, Post, User


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug',
            description='Тестовое описание',)
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост, в котором больше 15 символов',)

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        expected_object_names = {self.post: self.post.text[:15],
                                 self.group: self.group.title}
        for field, expected_value in expected_object_names.items():
            with self.subTest(field=field):
                self.assertEqual(expected_value, str(field))

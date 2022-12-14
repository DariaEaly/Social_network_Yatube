from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Group(models.Model):
    title = models.CharField('Название группы', max_length=200,
                             help_text='Введите название группы')
    slug = models.SlugField('URL группы', unique=True,
                            help_text='Введите URL группы')
    description = models.TextField('Описание группы',
                                   help_text='Опишите группу')

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField(
        'Текст поста',
        help_text='Введите текст поста')
    pub_date = models.DateTimeField(
        'Дата публикации',
        auto_now_add=True,
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Автор поста'
    )
    group = models.ForeignKey(
        Group,
        related_name='posts',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name='Группа',
        help_text="Группа, к которой будет относиться пост"
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ['-pub_date']

    def __str__(self):
        return self.text[:15]


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        related_name='comments',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        verbose_name='Ссылка на оригинальный пост')
    author = models.ForeignKey(
        User,
        related_name='comments',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        verbose_name='Автор комментария')
    text = models.TextField(
        'Текст комментария',
        help_text='Введите текст комментария')
    created = models.DateTimeField(
        'Дата публикации',
        auto_now_add=True,
    )

    def __str__(self):
        return self.text[:15]


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        related_name='follower',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        verbose_name='Подписчик')
    author = models.ForeignKey(
        User,
        related_name='following',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        verbose_name='Пользователь, на которого подписываются')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'author'],
                                               name='unique_follow')]

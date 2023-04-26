from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Group, Post, User
from .utils import paginator


@cache_page(20, key_prefix='index_page')
def index(request):
    """Главная страница."""
    post_list = Post.objects.select_related('group', 'author')
    context = {
        'page_obj': paginator(request, post_list),
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    """Все посты группы."""
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.select_related('author')
    context = {
        'group': group,
        'page_obj': paginator(request, post_list),
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    """Профиль пользователя."""
    author = get_object_or_404(User, username=username)
    post_list = author.posts.select_related('group')
    following = (
        request.user.is_authenticated
        and author.following.filter(user=request.user).exists())
    context = {
        'author': author,
        'page_obj': paginator(request, post_list),
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """Страница отдельного поста."""
    post = get_object_or_404(Post, pk=post_id)
    comments = post.comments.all()
    form = CommentForm(request.POST or None)
    context = {'post': post,
               'form': form,
               'comments': comments}
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    """Создание поста."""
    form = PostForm(request.POST or None,
                    files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', post.author)
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    """Редактирование поста."""
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post.pk)
    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=post)
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post.pk)
    context = {
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    """Добавить комментарий."""
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """Посты избранных авторов."""
    post_list = Post.objects.filter(
        author__following__user=request.user)
    context = {'page_obj': paginator(request, post_list)}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    """Подписаться на автора."""
    author = get_object_or_404(User, username=username)
    if author != request.user:
        author.following.get_or_create(user=request.user)
    return redirect('posts:profile', username)


@login_required
def profile_unfollow(request, username):
    """Отписаться от автора."""
    author = get_object_or_404(User, username=username)
    following = author.following.filter(user=request.user)
    if following.exists():
        following.delete()
    return redirect('posts:profile', username)

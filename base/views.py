from functools import wraps
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.utils.translation import gettext as _
from django.contrib import messages

from .models import *
from .forms import (
    ArticleForm, LoginForm, UserRegisterForm, CommentForm,
    UserEditForm,
)


# Help functions and decorators
def check_owner(model: type, key: str, owner_pk: str):

    def decor_func(func):

        @wraps(func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            obj = get_object_or_404(model, **{key: kwargs.pop(key)})
            if not request.user.is_superuser and getattr(obj, owner_pk) != request.user.pk:
                messages.warning(request, _("You aren't allowed here!"))
                return redirect(request.META.get('HTTP_REFERER', 'home'))
            return func(request, obj, *args, **kwargs)

        return wrapper

    return decor_func


# View functions
# user views
def show_users(request):
    users = User.objects.all()
    context = {'users': users}
    return render(request, 'base/users.html', context=context)


def register_user(request: HttpRequest):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _("Account has been created"))
            messages.info(request, _("You are now logged as '%s'") %
                          form.cleaned_data['username'])
            return redirect('edit_profile')
        messages.error(request, _('Something went wrong!'))
    else:
        form = UserRegisterForm()
    context = {'form': form, 'title': 'Register',
               'submit': 'register'}
    return render(request, 'base/login.html', context=context)


def login_user(request: HttpRequest):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        form.is_valid()
        print(form.cleaned_data)
        user = authenticate(request, **form.cleaned_data)
        if user is not None:
            messages.info(request, _("You are now logged as '%s'") %
                          form.cleaned_data['username'])
            login(request, user)
            return redirect('home')
        messages.error(request, _('Incorrect username or password!'))
    else:
        form = LoginForm()
    context = {'form': form, 'title': 'Login',
               'submit': 'login', 'is_login': True}
    return render(request, 'base/login.html', context=context)


def show_profile(request: HttpRequest, slug: str):
    user = get_object_or_404(User, slug=slug)
    posts = user.posts.all()
    comments = user.post_comments.all()
    following = user.following.all()
    context = {'posts': posts, 'comments': comments,
               'user': user, 'following': following}
    return render(request, 'base/user_profile.html', context=context)


@login_required(login_url='login')
def follow_user(request: HttpRequest, slug: str):
    following = get_object_or_404(User, slug=slug)
    try:
        following.followers.add(request.user)
    except Exception as e:
        messages.error(request, _(str(e)))
    else:
        messages.info(request, _("You followed '%s' ") %
                      following.username)
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required(login_url='login')
def unfollow_user(request: HttpRequest, slug: str):
    following = get_object_or_404(User, slug=slug)
    try:
        following.followers.remove(request.user)
    except Exception as e:
        messages.error(request, _(str(e)))
    else:
        messages.info(request, _("You unfollowed '%s' ") %
                      following.username)
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required(login_url='login')
def logout_user(request: HttpRequest):
    messages.info(request, _("You are logged out from '%s'") %
                  request.user.username)
    logout(request)
    return redirect('home')


@login_required(login_url='login')
def edit_profile(request: HttpRequest,):
    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES,
                            instance=request.user)
        if form.is_valid():
            messages.success(request, _('Changes have been saved'))
            form.save()
            return redirect('home')
        messages.error(request, _('Something went wrong'))
    else:
        form = UserEditForm(instance=request.user)
    context = {
        'form': form, 'title': f"Edit {request.user}",
        'submit': 'edit', 'send_file': True, }
    return render(request, 'base/edit_profile.html', context=context)


# post views
def posts_page(request: HttpRequest):
    posts = Article.objects.all()
    context = {'posts': posts}
    return render(request, 'base/home.html', context=context)


@login_required(login_url='login')
def add_post(request: HttpRequest):
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            messages.info(request, _("Post has been added!"))
            post = form.save(request.user)
            return redirect(post)
        messages.success(request, _("Something went wrong!"))
    else:
        form = ArticleForm()
    context = {'form': form, 'title': 'Add a Post',
               'submit': 'Add', 'send_file': True}
    return render(request, 'base/form.html', context=context)


def show_post(request: HttpRequest, pk: int):
    post = get_object_or_404(Article, pk=pk)
    comments = post.comments.all()
    comment_form = CommentForm()
    context = {'post': post, 'comment_form': comment_form,
               'comments': comments}
    return render(request, 'base/post.html', context=context)


@login_required(login_url='login')
@check_owner(Article, 'pk', 'author_id')
def edit_post(request: HttpRequest, post: Article):
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            messages.success(request, _("Changes have been saved!"))
            form.save()
            return redirect('home')
        messages.error(request, _("Something went wrong!"))
    else:
        form = ArticleForm(instance=post)
    context = {'form': form, 'title': f"Edit {post.title}",
               'submit': 'Edit', 'send_file': True}
    return render(request, 'base/form.html', context)


@login_required(login_url='login')
@check_owner(Article, 'pk', 'author_id')
def delete_post(request: HttpRequest, post: Article):
    messages.success(request, _("Post has been deleted!"))
    post.delete()
    return redirect('home')


# comment views
@login_required(login_url='login')
def post_comment(request: HttpRequest):
    if request.method != 'POST':
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    form = CommentForm(request.POST)
    if form.is_valid():
        form.save(request.user.pk, request.POST.get('post_pk'))
    return redirect(request.META.get('HTTP_REFERER', 'home'))

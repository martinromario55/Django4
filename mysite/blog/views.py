from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Comment
from django.http import Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from .forms import EmailPostForm, CommentForm, SearchForm
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from taggit.models import Tag
from django.db.models import Count
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity


# Create your views here.
def post_list(request, tag_slug=None):
    post_list = Post.published.all()
    tag = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        post_list = post_list.filter(tags__in=[tag])

    # Pagination with 3 posts per page
    paginator = Paginator(post_list, 3)
    page_number = request.GET.get('page', 1)

    # Handling pagination errors
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        # If page_number is not an integer
        posts = paginator.page(1)
    except EmptyPage:
        # If page_number is out of range
        posts = paginator.page(paginator.num_pages)

    return render(request, 'blog/post/list.html', {'posts' : posts, 'tag':tag})


def post_detail(request, year, month, day, post):
    # try:
    #     post = Post.published.get(id=id)
    # except Post.DoesNotExist:
    #     raise Http404('No Post found.')
    post = get_object_or_404(Post, status=Post.Status.PUBLISHED,
                                slug=post,
                                publish__year=year, publish__month=month, publish__day=day)

    # Adding comments to the post detail view
    comments = post.comments.filter(active=True) #Get all active comments related to the current post
    form = CommentForm() # Load an instance of the comment form

    # Listing similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count(
        'tags')).order_by('-same_tags', '-publish')[:4]

    return render(request, 'blog/post/detail.html', {'post': post, 'comments':comments, 'form':form, 'similar_posts':similar_posts})


# Using aclass-based view
class PostListView(ListView):
    '''
    Alternative Post List View
    '''

    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/post/list.html'


# Handling forms in views
def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    sent = False

    # Post was submitted
    if request.method == 'POST':
        form = EmailPostForm(request.POST) # a form instance with submitted data

        # Form validation
        if form.is_valid():
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            # Email build
            subject = f"{cd['name']} recommends you read {post.title}"
            message = f"Read {post.title} at {post_url}\n\n {cd['name']}\'s comments: {cd['comments']}."
            send_mail(subject, message, 'tuyiiya.web@gmail.com', [cd['to']])
            sent = True
    
    else:
        form = EmailPostForm() # An empty form instance

    return render(request, 'blog/post/share.html', {'post':post, 'form':form, 'sent':sent})


# Comment Form with ModelForms
@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    comment = None

    # Post
    form = CommentForm(data=request.POST) # Retrieve current POST
    if form.is_valid():
        # Create a Comment object without saving it
        comment = form.save(commit=False)
        # Assign the post to the comment
        comment.post = post
        # Save the comment to the database
        comment.save()
    
    return render(request, 'blog/post/comment.html', {'post':post, 'form':form, 'comment':comment})


# Building a search view
def post_search(request):
    form = SearchForm()
    query = None
    results = []

    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            # Stemming and ranking results
            # search_vector = SearchVector('title', 'body')
            # search_query = SearchQuery(query)

            # Searching with trigram similarity
            results = Post.published.annotate(
                similarity = TrigramSimilarity('title', query)
            ).filter(similarity__gt=0.1).order_by('-similarity')

    return render(request, 'blog/post/search.html', {'form':form, 'query':query, 'results':results})
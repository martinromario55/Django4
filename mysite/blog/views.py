from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Comment
from django.http import Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from .forms import EmailPostForm, CommentForm
from django.core.mail import send_mail
from django.views.decorators.http import require_POST


# Create your views here.
def post_list(request):
    post_list = Post.published.all()

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

    return render(request, 'blog/post/list.html', {'posts' : posts})


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

    return render(request, 'blog/post/detail.html', {'post': post, 'comments':comments, 'form':form})


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
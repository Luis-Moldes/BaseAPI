# Here the urls for the different views are defined. Django assigns them automatically.

from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from snippets import views
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken.views import obtain_auth_token

# API endpoints:
urlpatterns = format_suffix_patterns([
    path('', views.api_root),
    path('snippets/',
        views.SnippetList.as_view(),
        name='snippet-list'),
    path('snippets/<int:pk>/', #pk is one of the fields of the snippet, this is the syntax to include it in an url
        views.SnippetDetail.as_view(),
        name='snippet-detail'),
    path('snippets/<int:pk>/highlight/',
        views.SnippetHighlight.as_view(),
        name='snippet-highlight'),
    path('users/',
        views.UserList.as_view(),
        name='user-list'),
    path('users/<int:pk>/',
        views.UserDetail.as_view(),
        name='user-detail'),
    path('numbers/',
         views.NumberList.as_view(),
         name='num-list'),
    path('numbers/<int:pk>/',
         views.NumberDetail.as_view(),
         name='number-detail'),
    path('upload/', views.FileUploadView.as_view(), name='uploadimage'),
    path('api-token-auth/', obtain_auth_token, name='api-tokn-auth')
])

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
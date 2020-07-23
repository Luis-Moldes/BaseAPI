# Here the urls for the different views are defined. Django assigns them automatically.

from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from snippets import views, permissions
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.authtoken.views import obtain_auth_token
import rest_framework_simplejwt
from rest_framework_simplejwt import views as jwt_views

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
    path('data/',
         views.WarpList.as_view(),
         name='data-list'),
    path('data/<int:pk>/',
         views.WarpDetail.as_view(),
         name='warp-detail'),
    path('getdata/',
         views.WarpGetter.as_view(),
         name='data-retrieve'),
    path('upload/', views.FileUploadView.as_view(), name='uploadimage'),
    path('loaderio-8531c4531d7d162fdfb8d7bed24f9d6f/', views.FileDownloadListAPIView.as_view(), name='loader'),
    # path('api-token-auth/', obtain_auth_token, name='api-tokn-auth')
    path('api-token-auth/', views.obtain_expiring_auth_token, name='api-tokn-auth'),
    path('api-token/', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api-token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
])

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
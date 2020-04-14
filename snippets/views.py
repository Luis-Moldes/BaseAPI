from snippets.models import Snippet, Number, File, Warp
from snippets.serialyzers import SnippetSerializer, UserSerializer, NumberSerializer, NumberSerializerForAll,\
    FileSerializer, WarpSerializer, WarpSerializerForAll
from snippets.permissions import IsOwnerOrReadOnly, IsOwnerOrNothing
from django.contrib.auth.models import User
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework import permissions
from rest_framework import viewsets
from rest_framework import generics
from rest_framework import renderers
from rest_framework.response import Response
import datetime
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt

# Here the functions to be used are defined. They are defined as classes based on the built-in REST 'generic' models, so
# they have a series of methods and characteristics already defined, which can be consulted here:
# https://www.django-rest-framework.org/api-guide/generic-views/
# The workings of this functions can be more easily seen in the commented codes below: first using the generic REST view,
# and then using regular REST code.

# "List" classes provide the complete list of each of the classes, while "Detail" provide the particular instance to
# each element. Each of them have their own particular methods, inherent to their respective generic models.

class SnippetList(generics.ListCreateAPIView):
    queryset = Snippet.objects.all()
    serializer_class = SnippetSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class SnippetDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Snippet.objects.all()
    serializer_class = SnippetSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,IsOwnerOrReadOnly]

class NumberList(generics.ListCreateAPIView):
    queryset = Number.objects.all()
    serializer_class = NumberSerializerForAll
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class NumberDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Number.objects.all()
    serializer_class = NumberSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,IsOwnerOrNothing]


class WarpList(generics.ListCreateAPIView):
    queryset = Warp.objects.all()
    serializer_class = WarpSerializerForAll
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class WarpDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Warp.objects.all()
    serializer_class = WarpSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,IsOwnerOrNothing]


class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetail(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

# If we want a display of only the highlighted html code
class SnippetHighlight(generics.GenericAPIView):
    queryset = Snippet.objects.all()
    renderer_classes = [renderers.StaticHTMLRenderer]

    def get(self, request, *args, **kwargs): # An override of the default "get" command
        snippet = self.get_object()
        return Response(snippet.highlighted)


class FileUploadView(generics.ListAPIView):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def post(self, request, *args, **kwargs):

      file_serializer = FileSerializer(data=request.data)

      if file_serializer.is_valid():
          file_serializer.save(owner=self.request.user)
          return Response(file_serializer.data, status=status.HTTP_201_CREATED)
      else:
          return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# class FileUploadView(APIView):
#     parser_class = (FileUploadParser,)
#
#     def post(self, request, *args, **kwargs):
#
#       file_serializer = FileSerializer(data=request.data)
#
#       if file_serializer.is_valid():
#           file_serializer.save()
#           return Response(file_serializer.data, status=status.HTTP_201_CREATED)
#       else:
#           return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET']) # This produces the main page (without this there is only http://... /snippets)
def api_root(request, format=None):
    return Response({
        'users': reverse('user-list', request=request, format=format),
        'snippets': reverse('snippet-list', request=request, format=format),
        'numbers': reverse('num-list', request=request, format=format),
        'data': reverse('data-list', request=request, format=format),
        'upload': reverse('uploadimage', request=request, format=format)

    })


from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.response import Response


#  We override the default rest framework login view
class ObtainExpiringAuthToken(ObtainAuthToken):
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            token, created =  Token.objects.get_or_create(user=serializer.validated_data['user'])

            if not created:
                # update the created time of the token to keep it valid
                token.created = datetime.datetime.utcnow()
                token.save()

            return Response({'token': token.key})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

obtain_expiring_auth_token = ObtainExpiringAuthToken.as_view()



'''
from rest_framework import mixins
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class SnippetList(mixins.ListModelMixin,
                  mixins.CreateModelMixin,
                  generics.GenericAPIView):
    queryset = Snippet.objects.all()
    serializer_class = SnippetSerializer

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class SnippetDetail(mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin,
                    mixins.DestroyModelMixin,
                    generics.GenericAPIView):
    queryset = Snippet.objects.all()
    serializer_class = SnippetSerializer

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

'''

''' 
class SnippetList(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, format=None):
        snippets = Snippet.objects.all() # Get all the snippets there are in the database
        serializer = SnippetSerializer(snippets, many=True) # Serialize them (convert them into a usable format)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = SnippetSerializer(data=request.data) # Turn the request data into a serialized snippet
        if serializer.is_valid():
            serializer.save() # Add it to the database
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SnippetDetail(APIView):
    """
    Retrieve, update or delete a snippet instance.
    """
    def get_object(self, pk):
        try:
            return Snippet.objects.get(pk=pk)
        except Snippet.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        snippet = self.get_object(pk)
        serializer = SnippetSerializer(snippet)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        snippet = self.get_object(pk)
        serializer = SnippetSerializer(snippet, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        snippet = self.get_object(pk)
        snippet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

'''
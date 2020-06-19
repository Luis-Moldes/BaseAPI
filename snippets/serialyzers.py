from rest_framework import serializers
from snippets.models import Snippet, LANGUAGE_CHOICES, STYLE_CHOICES, Number, File, Warp
from django.contrib.auth.models import User
from snippets.ExecScript_api import WarpRetrieve

# This is the link between our classes and the environment, what allows it to interpret them as representations such as json.
# All the data will be
# sent and received in this format, as it can be seen in Views. Serializers include functions to create and delete instances
# of the classes they refer to. The simplified REST syntax will be used, but a more comprehensible way can be seen in the
# commented code below: first using ModelSerializer and the using basic REST code.

class SnippetSerializer(serializers.HyperlinkedModelSerializer): #
    owner = serializers.ReadOnlyField(source='owner.username')
    highlight = serializers.HyperlinkedIdentityField(view_name='snippet-highlight', format='html')

    class Meta:
        model = Snippet
        fields = ['url', 'id', 'highlight', 'owner',
                  'title', 'code', 'linenos', 'language', 'style']

class NumberSerializer(serializers.HyperlinkedModelSerializer): #
    owner = serializers.ReadOnlyField(source='owner.username')
    sqrt = serializers.ReadOnlyField()
    square = serializers.ReadOnlyField()
    file = serializers.FileField(max_length=None, use_url=True)
    # file = serializers.ReadOnlyField()
    class Meta:
        model = Number
        fields = ['url', 'id',  'owner', 'num', 'sqrt', 'square', 'created', 'file']
        # readonly_fields = ['file']

class NumberSerializerForAll(serializers.HyperlinkedModelSerializer): #
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = Number
        fields = ['id',  'owner', 'num', 'url']


# class WarpSerializer(serializers.HyperlinkedModelSerializer): #
#     owner = serializers.ReadOnlyField(source='owner.username')
#     meanSOG = serializers.ReadOnlyField()
#     # file = serializers.FileField(max_length=None, use_url=True)
#
#     class Meta:
#         model = Warp
#         fields = ['id', 'owner', 'retrieved', 'meanSOG', 'boat_id', 'event', 'url', 'meanCOG']

class WarpSerializer(serializers.HyperlinkedModelSerializer):

    meanSOG = serializers.ReadOnlyField()
    meanCOG = serializers.ReadOnlyField()

    class Meta:
        model = Warp
        fields = ['meanSOG', 'meanCOG']

class WarpSerializerForAll(serializers.HyperlinkedModelSerializer): #

    owner = serializers.ReadOnlyField(source='owner.username')
    meanSOG = serializers.ReadOnlyField()
    meanCOG = serializers.ReadOnlyField()

    class Meta:
        model = Warp
        fields = ['id', 'owner', 'retrieved', 'url', 'boat_id', 'event', 'meanSOG', 'meanCOG']


class WarpSerializerForGet(serializers.HyperlinkedModelSerializer): #

    boat_id = serializers.CharField()
    event_id = serializers.CharField()
    # meanSOG = serializers.FloatField(default=0)
    # meanCOG = serializers.FloatField(default=0)
    # start = serializers.CharField(default='None')
    # stop = serializers.CharField(default='None')
    # twd = serializers.FloatField(default=10000)
    # tws = serializers.FloatField(default=10000)

    class Meta:
        model = Warp
        fields = ['boat_id', 'event_id']#, 'meanSOG', 'meanCOG', 'start', 'stop', 'twd', 'tws']



class UserSerializer(serializers.HyperlinkedModelSerializer):
    snippets = serializers.HyperlinkedRelatedField(many=True, view_name='snippet-detail', read_only=True)
    numbers = serializers.HyperlinkedRelatedField(many=True, view_name='number-detail', read_only=True)

    class Meta:
        model = User
        fields = ['url', 'id', 'username', 'snippets', 'numbers']


class FileSerializer(serializers.ModelSerializer):

    image = serializers.ImageField(max_length=None, use_url=True)
    file = serializers.FileField(max_length=None, use_url=True)
    class Meta:
        model = File
        fields = ['title', 'id', 'owner', 'image', 'file']


'''
class UserSerializer(serializers.ModelSerializer):
    snippets = serializers.PrimaryKeyRelatedField(many=True, queryset=Snippet.objects.all())
    class Meta:
        model = User
        fields = ['id', 'username', 'snippets']

class SnippetSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    class Meta:
        model = Snippet
        fields = ['id', 'title', 'code', 'linenos', 'language', 'style', 'owner']
'''

'''
    def create(self, validated_data):
        """
        Create and return a new `Snippet` instance, given the validated data.
        """
        return Snippet.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """
        Update and return an existing `Snippet` instance, given the validated data.
        """
        instance.title = validated_data.get('title', instance.title)
        instance.code = validated_data.get('code', instance.code)
        instance.linenos = validated_data.get('linenos', instance.linenos)
        instance.language = validated_data.get('language', instance.language)
        instance.style = validated_data.get('style', instance.style)
        instance.save()
        return instance
'''
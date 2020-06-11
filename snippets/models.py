from django.db import models
from pygments.lexers import get_all_lexers
from pygments.styles import get_all_styles
from pygments.lexers import get_lexer_by_name
from pygments.formatters.html import HtmlFormatter
from pygments import highlight
from snippets.functions import squareroot, squared
from rest_framework.exceptions import ParseError
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response
from rest_framework.views import APIView
from snippets.docxmaker import quickhacktogetadocx_API
from snippets.ExecScript_api import WarpRetrieve
import datetime


LEXERS = [item for item in get_all_lexers() if item[1]]
LANGUAGE_CHOICES = sorted([(item[1][0], item[0]) for item in LEXERS])
STYLE_CHOICES = sorted([(item, item) for item in get_all_styles()])

# Here the classes that are going to be used are defined, in the django syntax. Its interpretation for REST will be done by the serializers.

# As an example, 'snippets' will be used: strings of code with added properties

class Snippet(models.Model):
    # Django models also have a series of auto defined fields, each with its characteristics. You can consult them at
    # https://docs.djangoproject.com/en/3.0/ref/models/fields/#model-field-types

    created = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100, blank=True, default='')
    code = models.TextField()
    linenos = models.BooleanField(default=False)
    language = models.CharField(choices=LANGUAGE_CHOICES, default='python', max_length=100)
    style = models.CharField(choices=STYLE_CHOICES, default='friendly', max_length=100)
    owner = models.ForeignKey('auth.User', related_name='snippets', on_delete=models.CASCADE)
    highlighted = models.TextField()

    def save(self, *args, **kwargs): # This method will override the default save(), adding the highlighted field
        """
        Use the `pygments` library to create a highlighted HTML
        representation of the code snippet.
        """
        # The pygments library contains a seris of functions to work with highlighted HTML representation
        lexer = get_lexer_by_name(self.language)
        linenos = 'table' if self.linenos else False
        options = {'title': self.title} if self.title else {}
        formatter = HtmlFormatter(style=self.style, linenos=linenos,
                                  full=True, **options)
        self.highlighted = highlight(self.code, lexer, formatter)
        super(Snippet, self).save(*args, **kwargs)

    class Meta:
        ordering = ['created']


class Number(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    num = models.BigIntegerField()
    sqrt = models.BigIntegerField(default=0)
    square = models.BigIntegerField(default=0)
    file = models.FileField(upload_to='Files/', default='Files/None/No-img.pdf')
    owner = models.ForeignKey('auth.User', related_name='numbers', on_delete=models.CASCADE)
    nolookfield = models.BigIntegerField(default=69)

    def save(self, *args, **kwargs): # This method will override the default save(), adding the highlighted field
        self.square = squared(self.num)
        self.sqrt = squareroot(self.num)
        self.file = quickhacktogetadocx_API(self.num,self.sqrt,self.square,'snippets/template_soloreport.docx', self.owner,
                                            datetime.datetime.now().strftime('%Y-%m-%d'))
        super(Number, self).save(*args, **kwargs)

    class Meta:
        ordering = ['created']


class File(models.Model):

    title = models.CharField(max_length=100, blank=True, default='')
    image = models.ImageField(upload_to='Images/', default='Images/None/No-img.jpg')
    file = models.FileField(upload_to='Files/', default='Files/None/No-img.pdf')
    owner = models.ForeignKey('auth.User', related_name='files', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    # def __str__(self):
    #     return '%s' % self.title

    class Meta:
        ordering = ['created']


class Warp(models.Model):

    # def Calculate(self): # This method willpy override the default save(), adding the highlighted field
    #     return WarpRetrieve(self.boat_id, self.event)

    retrieved = models.DateTimeField(auto_now_add=True)

    boat_id = models.CharField(max_length=200, default='aaaaa')
    event_id = models.CharField(max_length=200)
    meanSOG = models.FloatField(default=0)
    meanCOG = models.FloatField(default=0)
    start = models.CharField(max_length=200, default='None')
    stop = models.CharField(max_length=200, default='None')
    TWD = models.FloatField(default=10000)
    TWS = models.FloatField(default=10000)
    # file = models.FileField(upload_to='Files/', default='Files/None/No-img.pdf')
    owner = models.ForeignKey('auth.User', related_name='data', on_delete=models.CASCADE)
    # [meanSOG, meanCOG] = WarpRetrieve(boat_id, event)


    def save(self, *args, **kwargs): # This method willpy override the default save(), adding the highlighted field
        [self.meanSOG, self.meanCOG] = WarpRetrieve(self.boat_id, self.event_id)

        # self.file = quickhacktogetadocx_API(self.num,self.sqrt,self.square,'snippets/template_soloreport.docx', self.owner,
        #                                     datetime.datetime.now().strftime('%Y-%m-%d'))
        super(Warp, self).save(*args, **kwargs)


    class Meta:
        ordering = ['retrieved']
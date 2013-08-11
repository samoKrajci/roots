from django.db import models
from django.contrib import admin
from base.util import with_author, with_timestamp


# Content-related models
@with_author
@with_timestamp
class Post(models.Model):
    '''
    Represents a post on the wall. This can be restricted to certain competition
    or can be general.
    '''

    title = models.CharField(max_length=100)
    competition = models.ForeignKey('competitions.Competition', blank=True)

    def __unicode__(self):
        return self.title


@with_author
@with_timestamp
class Gallery(models.Model):
    '''
    Represents a gallery of photos. This can be restricted to certain
    competition or event.
    '''

    name = models.CharField(max_length=50)
    competition = models.ForeignKey('competitions.Competition')
    event = models.ForeignKey('events.Event')
    date = models.DateTimeField()

    def __unicode__(self):
        return self.name

# Register to the admin site
admin.site.register(Post)
admin.site.register(Gallery)

import datetime
import os.path

from django.db import models
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.utils.translation import ugettext as _

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5
try:
    from PIL import ImageFile
except ImportError:
    import ImageFile

from avatar import AVATAR_STORAGE_DIR, AVATAR_RESIZE_METHOD

def avatar_file_path(instance=None, filename=None, user=None):
    user = user or instance.user
    return os.path.join(AVATAR_STORAGE_DIR, user.username, filename)

class Avatar(models.Model):
    email_hash = models.CharField(max_length=128, blank=True)
    user = models.ForeignKey(User)
    primary = models.BooleanField(default=False)
    avatar = models.ImageField(max_length=1024, upload_to=avatar_file_path, blank=True)
    date_uploaded = models.DateTimeField(default=datetime.datetime.now)
    
    def __unicode__(self):
        return _(u'Avatar for %s') % self.user
    
    def save(self, force_insert=False, force_update=False):
        self.email_hash = md5(self.user.email).hexdigest().lower()
        if self.primary:
            avatars = Avatar.objects.filter(user=self.user, primary=True)\
                .exclude(id=self.id)
            avatars.update(primary=False)
        super(Avatar, self).save(force_insert, force_update)
    
    def thumbnail_exists(self, size):
        return self.avatar.storage.exists(self.avatar_name(size))
    
    def create_thumbnail(self, size):
        orig = self.avatar.storage.open(self.avatar.name, 'rb').read()
        p = ImageFile.Parser()
        p.feed(orig)
        try:
            image = p.close()
        except IOError:
            return # What should we do here?  Render a "sorry, didn't work" img?
        (w, h) = image.size
        if w > h:
            diff = (w - h) / 2
            image = image.crop((diff, 0, w - diff, h))
        else:
            diff = (h - w) / 2
            image = image.crop((0, diff, w, h - diff))
        image = image.resize((size, size), AVATAR_RESIZE_METHOD)
        thumb = StringIO()
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(thumb, "JPEG")
        thumb_file = ContentFile(thumb.getvalue())
        thumb = self.avatar.storage.save(self.avatar_name(size), thumb_file)
    
    def avatar_url(self, size):
        return self.avatar.storage.url(self.avatar_name(size))
    
    def avatar_name(self, size):
        return os.path.join(AVATAR_STORAGE_DIR, self.user.username,
            'resized', str(self.id), '-'.join([str(size), self.avatar.name]))
from django.db import models

class Avatar(models.Model):
    name = models.CharField(max_length=100)
    idle_video = models.URLField(help_text="URL to Cloudinary idle video")
    talking_video = models.URLField(help_text="URL to Cloudinary talking video")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

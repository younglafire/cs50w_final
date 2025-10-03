from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now

class User(AbstractUser):
    pass


class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        "taxonomy.Category",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="goals"
    )
    unit = models.ForeignKey(
        "taxonomy.Unit",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="goals"
    )
    target_value = models.FloatField()
    deadline = models.DateField(null=True, blank=True)
    is_public = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True, db_index=True)

    def __str__(self):
        return f"Goal: {self.title}, User: {self.user.username}"

    # Simple data access methods (keep these in model)
    def days_remaining(self):
        """Return number of days left until deadline (or None if no deadline)."""
        if self.deadline:
            delta = self.deadline - now().date()
            return delta.days
        return None

    def get_current_value(self):
        """Sum of all progress values for this goal."""
        return sum(p.value for p in self.progresses.all())

    def has_today_progress(self, user):
        """Check if user has logged progress today."""
        return self.progresses.filter(user=user, date=now().date()).first()

    # Social features (simple counts - these are fine in model)
    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def comments_count(self):
        return self.comments.count()

    def is_liked_by(self, user):
        return self.likes.filter(user=user).exists()

    # For backward compatibility in templates
    # These now delegate to services
    @property
    def status(self):
        """Return a single status label: active / completed / overdue."""
        from .services import goal_get_status
        return goal_get_status(self)
    
    def progress_percentage(self):
        """Calculate progress as a percentage (0-100)."""
        from .services import goal_progress_percentage
        return goal_progress_percentage(self)

    def is_completed(self):
        """Check if goal has reached target value."""
        from .services import goal_is_completed
        return goal_is_completed(self)

    def is_overdue(self):
        """Check if goal is past deadline and not completed."""
        from .services import goal_is_overdue
        return goal_is_overdue(self)


class Progress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="progresses")
    value = models.FloatField()
    date = models.DateField(default=now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'goal', 'date'], name='unique_daily_progress')
        ]

    def __str__(self):
        return f"{self.user.username} - {self.goal.title} - {self.value} on {self.date}"
    
    def is_today(self):
        """Check if this progress entry is from today."""
        return self.date == now().date()


class ProgressPhoto(models.Model):
    progress = models.ForeignKey("Progress", on_delete=models.CASCADE, related_name="photos")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def validate_image(image):
        max_size = 5 * 1024 * 1024  # 5 MB
        if image.size > max_size:
            raise ValidationError("Image file too large (max 5MB).")
        if not image.content_type.startswith("image/"):
            raise ValidationError("Invalid file type. Only images allowed.") 
    
    image = models.ImageField(upload_to="progress_photos/", validators=[validate_image])
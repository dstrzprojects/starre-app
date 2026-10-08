from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=80)
    show_name_on_lists = models.BooleanField(default=True)
    phone = models.CharField(max_length=30, blank=True)
    def __str__(self): return self.display_name

class Event(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_events')
    title = models.CharField(max_length=180)
    description = models.TextField()
    topic_summary = models.TextField(blank=True, max_length=4000)
    starts_at = models.DateTimeField(db_index=True)
    place = models.CharField(max_length=180)
    anonymous_author = models.BooleanField(default=False)
    image = models.ImageField(upload_to='events/%Y/%m/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['starts_at', 'id']
    def __str__(self): return self.title

class Announcement(models.Model):
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='announcements')
    body = models.TextField()
    anonymous_author = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta: ordering = ['-created_at', '-id']

class Signup(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='signups')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    guest_token = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['event','user'], condition=models.Q(user__isnull=False), name='unique_event_user'),models.UniqueConstraint(fields=['event','guest_token'], condition=~models.Q(guest_token=''), name='unique_event_guest')]

class Task(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=180)
    position = models.PositiveIntegerField(default=0)
    class Meta: ordering = ['position', 'id']

class TaskClaim(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='claims')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: constraints = [models.UniqueConstraint(fields=['task','user'], name='unique_task_user')]

class RateLimit(models.Model):
    # Only a digest is stored, never an email address or a raw client IP.
    key = models.CharField(max_length=64, primary_key=True)
    hits = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)

class Goal(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)
    class Meta: ordering = ['position', 'id']

def validate_transfer_details(phone, account):
    digits=''.join(str(account).split())
    if phone and (not phone.isdigit() or len(phone)!=9):
        raise ValidationError('Numer BLIK musi mieć 9 cyfr.')
    if digits and (not digits.isdigit() or len(digits)!=26 or int(digits[2:]+'2521'+digits[:2])%97!=1):
        raise ValidationError('Numer rachunku musi mieć 26 cyfr i poprawne cyfry kontrolne.')

class PaymentSettings(models.Model):
    name = models.CharField(max_length=180, blank=True)
    address = models.CharField(max_length=250, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    bank_account = models.CharField(max_length=34, blank=True)
    class Meta: verbose_name_plural = 'Ustawienia przelewów'
    def clean(self):validate_transfer_details(self.phone, self.bank_account)

class Notice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notices')
    text = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    class Meta: ordering = ['-created_at']

class CreatorSupport(models.Model):
    visible = models.BooleanField(default=True, verbose_name='Pokazuj sekcję wsparcia użytkownikom')
    name = models.CharField(max_length=180, blank=True)
    address = models.CharField(max_length=250, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    bank_account = models.CharField(max_length=34, blank=True)
    class Meta:
        verbose_name = 'Ustawienie wsparcia'
        verbose_name_plural = 'Wsparcie'
    def clean(self):validate_transfer_details(self.phone, self.bank_account)

class ContactSettings(models.Model):
    visible = models.BooleanField(default=True, verbose_name='Widoczna dla użytkowników')
    name = models.CharField(max_length=180, blank=True)
    email = models.EmailField(max_length=254, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=250, blank=True)
    class Meta:
        verbose_name = 'Ustawienie kontaktu'
        verbose_name_plural = 'Kontakt'
    def __str__(self): return 'Kontakt'

class NavigationTab(models.Model):
    class Key(models.TextChoices):
        HOME = 'home', 'Start'
        ANNOUNCEMENTS = 'announcements', 'Ogłoszenia'
        EVENTS = 'events', 'Spotkania'
        FINANCE = 'finance', 'Finanse'
        TASKS = 'tasks', 'Grafik'
    key = models.CharField(max_length=24, choices=Key.choices, unique=True)
    visible = models.BooleanField(default=True, verbose_name='Widoczna dla użytkowników')
    class Meta:
        verbose_name = 'Ustawienie zakładki'
        verbose_name_plural = 'Pozostałe zakładki'
        ordering = ['key']
    def __str__(self): return self.get_key_display()

class Presence(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='confirmations')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    guest_token = models.CharField(max_length=64, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['event','user'], condition=models.Q(user__isnull=False), name='unique_presence_user'),models.UniqueConstraint(fields=['event','guest_token'], condition=~models.Q(guest_token=''), name='unique_presence_guest')]

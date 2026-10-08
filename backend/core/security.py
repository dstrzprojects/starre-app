import hashlib
import ipaddress
import secrets
from datetime import timedelta

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from .models import RateLimit


def client_ip(request):
    # The reverse proxy must overwrite X-Real-IP. Direct requests cannot set it.
    from django.conf import settings
    source = request.META.get('HTTP_X_REAL_IP') if settings.SECURE_PROXY_SSL_HEADER else None
    source = source or request.META.get('REMOTE_ADDR', '')
    try:
        return str(ipaddress.ip_address(source))
    except ValueError:
        return str(request.META.get('REMOTE_ADDR', 'unknown'))


def _key(scope, identity):
    return hashlib.sha256(f'{scope}:{identity}'.encode()).hexdigest()


def limited(scope, identity, limit):
    row = RateLimit.objects.filter(pk=_key(scope, identity)).first()
    return bool(row and row.expires_at > timezone.now() and row.hits >= limit)


def consume(scope, identity, limit, seconds):
    now = timezone.now()
    with transaction.atomic():
        row, _ = RateLimit.objects.select_for_update().get_or_create(
            pk=_key(scope, identity), defaults={'expires_at': now + timedelta(seconds=seconds)}
        )
        if row.expires_at <= now:
            row.hits = 0
            row.expires_at = now + timedelta(seconds=seconds)
        if row.hits >= limit:
            return False
        row.hits += 1
        row.save(update_fields=['hits', 'expires_at'])
    # Keep the throttle table bounded over time without a separate scheduler.
    if secrets.randbelow(100) == 0:
        old_ids = list(RateLimit.objects.filter(expires_at__lt=now).values_list('key', flat=True)[:100])
        if old_ids:
            RateLimit.objects.filter(pk__in=old_ids).delete()
    return True


def too_many():
    response = JsonResponse({'error': 'Zbyt wiele prób. Spróbuj ponownie później.'}, status=429)
    response['Retry-After'] = '600'
    return response


class AdminLoginThrottleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/admin/login/' and request.method == 'POST':
            if not consume('admin-login', client_ip(request), 15, 600):
                return too_many()
        return self.get_response(request)


class AppHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/media/'):
            response['Content-Security-Policy'] = "default-src 'none'; sandbox"
            response['X-Content-Type-Options'] = 'nosniff'
            return response
        if not request.path.startswith('/admin/') and response.get('Content-Type', '').startswith('text/html'):
            response['Content-Security-Policy'] = (
                "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; "
                "connect-src 'self'; worker-src 'self'; object-src 'none'; "
                "base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
            )
        return response

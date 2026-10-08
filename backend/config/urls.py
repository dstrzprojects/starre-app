from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve
from django.conf import settings
from core import views

urlpatterns = [path('admin/', admin.site.urls),path('api/bootstrap',views.bootstrap),path('api/admin/settings',views.admin_settings),path('api/auth/register',views.register),path('api/auth/login',views.sign_in),path('api/auth/logout',views.sign_out),path('api/profile',views.profile),path('api/events',views.events),path('api/events/<int:pk>',views.event),path('api/events/<int:pk>/signup',views.signup),path('api/events/<int:pk>/presence',views.presence),path('api/events/<int:pk>/tasks',views.event_tasks),path('api/events/<int:pk>/image',views.event_image),path('api/tasks/<int:pk>/claim',views.claim),path('api/announcements',views.announcements),path('api/announcements/<int:pk>',views.announcement),path('api/goals',views.goals),path('api/notices',views.notices),path('api/contact',views.contact)]
if settings.DEBUG:
    urlpatterns += [re_path(r'^media/(?P<path>.*)$', serve, {'document_root':settings.MEDIA_ROOT})]
urlpatterns += [re_path(r'^(?!api/|admin/|static/|media/).*$',views.app_shell)]

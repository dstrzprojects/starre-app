import json
from django.contrib.auth.models import User
from django.test import Client, TestCase
from .models import Announcement, ContactSettings, CreatorSupport, Event, NavigationTab, Profile, RateLimit, Task

class CoreFlowTests(TestCase):
    def setUp(self):
        self.owner=User.objects.create_user(username='autor@example.org',email='autor@example.org',password='bezpieczne-haslo-123')
        Profile.objects.create(user=self.owner,display_name='Autor')
        self.other=User.objects.create_user(username='drugi@example.org',email='drugi@example.org',password='bezpieczne-haslo-456')
        Profile.objects.create(user=self.other,display_name='Drugi')
        self.client=Client(enforce_csrf_checks=True)
        self.client.get('/api/bootstrap')
        self.token=self.client.cookies['csrftoken'].value
    def post(self,url,data,client=None,method='post'):
        c=client or self.client
        return getattr(c,method)(url,data=json.dumps(data),content_type='application/json',HTTP_X_CSRFTOKEN=c.cookies['csrftoken'].value)
    def test_account_event_guest_signup_and_shared_task(self):
        self.client.force_login(self.owner)
        event=self.post('/api/events',{'title':'Spotkanie','description':'Wspólny czas','topicSummary':'Rozmowa o wspólnocie.','startsAt':'2026-10-09T18:00:00+02:00','place':'Sala'}).json()
        self.assertEqual(event['topicSummary'],'Rozmowa o wspólnocie.')
        pk=event['id']
        tasks=self.post(f'/api/events/{pk}/tasks',{'tasks':[{'title':'Przygotuj salę'}]},method='put').json()['tasks']
        guest=Client(enforce_csrf_checks=True);guest.get('/api/bootstrap')
        signup=self.post(f'/api/events/{pk}/signup',{'anonymous':True},guest).json()
        self.assertEqual(signup['signupCount'],1)
        self.assertTrue(signup['signedUp'])
        self.assertEqual(self.client.get(f'/api/events/{pk}').json()['participants'],['Anonimowy uczestnik'])
        self.client.force_login(self.other)
        self.assertEqual(self.post(f'/api/events/{pk}',{'title':'Zmienione'},method='patch').status_code,403)
        self.assertEqual(self.post(f'/api/events/{pk}',{},method='delete').status_code,403)
        self.assertEqual(self.post(f'/api/tasks/{tasks[0]["id"]}/claim',{}).status_code,200)
        self.client.force_login(self.owner)
        self.assertEqual(len(self.post(f'/api/tasks/{tasks[0]["id"]}/claim',{}).json()['tasks'][0]['people']),2)
    def test_moderator_removes_foreign_announcement_without_editing(self):
        a=Announcement.objects.create(creator=self.owner,body='Komunikat')
        self.other.is_staff=True;self.other.save()
        self.client.force_login(self.other)
        self.assertEqual(self.post(f'/api/announcements/{a.id}',{'body':'Zmienione'},method='patch').status_code,403)
        self.assertEqual(self.post(f'/api/announcements/{a.id}',{},method='delete').status_code,200)
        self.assertEqual(self.owner.notices.count(),1)
    def test_registration_and_presence_window(self):
        from datetime import timedelta
        from django.utils import timezone
        visitor=Client(enforce_csrf_checks=True);visitor.get('/api/bootstrap')
        result=self.post('/api/auth/register',{'email':'nowy@example.org','name':'Nowy','password':'Dobre-Haslo-876543'},visitor)
        self.assertEqual(result.status_code,201)
        self.assertEqual(result.json()['user']['name'],'Nowy')
        e=Event.objects.create(creator=self.owner,title='Jutro',description='Opis',starts_at=timezone.now()+timedelta(hours=2),place='Sala')
        guest=Client(enforce_csrf_checks=True);guest.get('/api/bootstrap')
        self.assertEqual(self.post(f'/api/events/{e.pk}/presence',{},guest).status_code,403)
        self.assertEqual(self.post(f'/api/events/{e.pk}/signup',{'anonymous':True},guest).status_code,200)
        self.assertEqual(self.post(f'/api/events/{e.pk}/presence',{},guest).status_code,200)
        self.assertTrue(guest.get(f'/api/events/{e.pk}').json()['presenceConfirmed'])
        self.assertEqual(self.post(f'/api/events/{e.pk}/presence',{},guest,method='delete').status_code,200)
        self.assertFalse(guest.get(f'/api/events/{e.pk}').json()['presenceConfirmed'])
        self.assertEqual(self.post(f'/api/events/{e.pk}/presence',{},guest).status_code,200)
        cancelled=self.post(f'/api/events/{e.pk}/signup',{},guest,method='delete').json()
        self.assertFalse(cancelled['signedUp'])
        self.assertFalse(cancelled['presenceConfirmed'])
    def test_admin_cannot_edit_foreign_content(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from .admin import EventAdmin, AnnouncementAdmin
        e=Event.objects.create(creator=self.owner,title='Cudze',description='Opis',starts_at=__import__('django').utils.timezone.now(),place='Sala')
        a=Announcement.objects.create(creator=self.owner,body='Cudze')
        self.other.is_staff=True;self.other.is_superuser=True;self.other.save()
        request=RequestFactory().get('/admin/');request.user=self.other
        self.assertFalse(EventAdmin(Event,admin.site).has_change_permission(request,e))
        self.assertFalse(EventAdmin(Event,admin.site).has_delete_permission(request,e))
        self.assertNotIn('image',EventAdmin(Event,admin.site).get_fields(request,e))
        self.assertFalse(AnnouncementAdmin(Announcement,admin.site).has_change_permission(request,a))
        self.assertTrue(AnnouncementAdmin(Announcement,admin.site).has_delete_permission(request,a))
    def test_csrf_required(self):
        self.client.force_login(self.owner)
        response=self.client.post('/api/events',data='{}',content_type='application/json')
        self.assertEqual(response.status_code,403)

    def test_support_tab_visibility_can_be_changed_from_admin_list(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from .admin import CreatorSupportAdmin
        support=CreatorSupport.objects.order_by('pk').first()
        self.assertIsNotNone(support)
        self.assertTrue(self.client.get('/api/bootstrap').json()['navigation']['support'])
        admin_user=User.objects.create_superuser(username='admin-wsparcia',password='Bezpieczne-Haslo-123')
        request=RequestFactory().get('/admin/core/creatorsupport/')
        request.user=admin_user
        model_admin=CreatorSupportAdmin(CreatorSupport,admin.site)
        self.assertIn('visible',model_admin.list_editable)
        admin_client=Client()
        admin_client.force_login(admin_user)
        admin_page=admin_client.get('/admin/core/creatorsupport/')
        self.assertEqual(admin_page.status_code,200)
        self.assertContains(admin_page,'name="form-0-visible"')
        support.visible=False
        support.save()
        self.assertFalse(self.client.get('/api/bootstrap').json()['navigation']['support'])

    def test_each_navigation_tab_has_an_admin_checkbox_and_hides_only_its_link(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from .admin import ContactSettingsAdmin, NavigationTabAdmin
        admin_user=User.objects.create_superuser(username='admin-zakladek',password='Bezpieczne-Haslo-123')
        admin_client=Client()
        admin_client.force_login(admin_user)
        index=admin_client.get('/admin/')
        self.assertContains(index, 'Kontakt')
        self.assertContains(index, 'Wsparcie')
        self.assertContains(index, '/admin/core/contactsettings/add/')
        self.assertContains(index, '/admin/core/contactsettings/')
        self.assertContains(index, '/admin/core/creatorsupport/add/')
        self.assertContains(index, '/admin/core/creatorsupport/')
        contact_admin=ContactSettingsAdmin(ContactSettings,admin.site)
        navigation_admin=NavigationTabAdmin(NavigationTab,admin.site)
        self.assertIn('visible', contact_admin.list_editable)
        self.assertIn('visible', navigation_admin.list_editable)
        self.assertContains(admin_client.get('/admin/core/contactsettings/'), 'name="form-0-visible"')
        self.assertContains(admin_client.get('/admin/core/navigationtab/'), 'name="form-0-visible"')
        contact=ContactSettings.objects.first()
        contact.visible=False
        contact.save()
        events_tab=NavigationTab.objects.get(key='events')
        events_tab.visible=False
        events_tab.save()
        navigation=self.client.get('/api/bootstrap').json()['navigation']
        self.assertFalse(navigation['contact'])
        self.assertFalse(navigation['events'])
        self.assertTrue(navigation['support'])
        self.assertTrue(navigation['home'])

    def test_superuser_can_manage_app_settings_but_not_other_peoples_content(self):
        event=Event.objects.create(creator=self.owner,title='Cudze spotkanie',description='Opis',starts_at=__import__('django').utils.timezone.now(),place='Sala')
        announcement=Announcement.objects.create(creator=self.owner,body='Cudze ogłoszenie')
        admin_user=User.objects.create_superuser(username='admin-ustawien',password='Bezpieczne-Haslo-123')
        self.client.force_login(admin_user)
        self.assertEqual(self.client.get('/api/admin/settings').status_code,200)
        settings_payload={
            'contact':{'visible':True,'name':'Sekretariat','email':'kontakt@example.org','phone':'123456789','address':'Ulica 1'},
            'payment':{'name':'Wspólnota','address':'Ulica 2','phone':'','account':''},
            'support':{'visible':True,'name':'Wspólnota','address':'Ulica 2','phone':'','account':''},
            'navigation':{'home':True,'announcements':True,'events':True,'finance':True,'tasks':True,'contact':False,'support':True},
        }
        result=self.post('/api/admin/settings',settings_payload,method='patch')
        self.assertEqual(result.status_code,200,result.content)
        bootstrap=self.client.get('/api/bootstrap').json()
        self.assertEqual(bootstrap['contactDetails']['email'],'kontakt@example.org')
        self.assertFalse(bootstrap['navigation']['contact'])
        self.assertEqual(bootstrap['payment']['name'],'Wspólnota')
        from unittest.mock import patch
        with patch.dict('os.environ',{'CONTACT_TO_EMAIL':''}), patch('core.views.EmailMessage') as mail:
            self.assertEqual(self.post('/api/contact',{'reply':'nadawca@example.org','subject':'Pytanie','message':'Treść'}).status_code,200)
            self.assertEqual(mail.call_args.args[3],['kontakt@example.org'])
        self.assertEqual(self.post(f'/api/events/{event.pk}',{'title':'Zmiana superusera'},method='patch').status_code,403)
        self.assertEqual(self.post(f'/api/announcements/{announcement.pk}',{'body':'Zmiana superusera'},method='patch').status_code,403)

    def test_non_superuser_cannot_read_or_change_app_settings(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get('/api/admin/settings').status_code,403)
        result=self.post('/api/admin/settings',{},method='patch')
        self.assertEqual(result.status_code,403)

    def test_auth_limits_and_malformed_input(self):
        url='/api/auth/login'
        self.assertEqual(self.post(url,{'email':self.owner.email,'password':['wrong']}).status_code,400)
        for _ in range(10):
            self.assertEqual(self.post(url,{'email':self.owner.email,'password':'wrong'}).status_code,401)
        self.assertEqual(self.post(url,{'email':self.owner.email,'password':'bezpieczne-haslo-123'}).status_code,429)
        from django.utils import timezone
        from datetime import timedelta
        RateLimit.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.post(url,{'email':self.owner.email,'password':'bezpieczne-haslo-123'}).status_code,200)

    def test_invalid_task_ids_do_not_break_or_replace_other_tasks(self):
        from django.utils import timezone
        e=Event.objects.create(creator=self.owner,title='Spotkanie',description='Opis',starts_at=timezone.now(),place='Sala')
        t=Task.objects.create(event=e,title='Stare zadanie')
        self.client.force_login(self.owner)
        url=f'/api/events/{e.pk}/tasks'
        for item in ({'id':[t.pk],'title':'Zmienione'},{'id':True,'title':'Zmienione'}):
            self.assertEqual(self.post(url,{'tasks':[item]},method='put').status_code,400)
        self.assertEqual(self.post(url,{'tasks':[{'id':t.pk,'title':'A'},{'id':t.pk,'title':'B'}]},method='put').status_code,400)
        self.assertEqual(Task.objects.get(pk=t.pk).title,'Stare zadanie')

    def test_image_is_reencoded_with_safe_extension(self):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from django.utils import timezone
        import tempfile
        e=Event.objects.create(creator=self.owner,title='Spotkanie',description='Opis',starts_at=timezone.now(),place='Sala')
        self.client.force_login(self.owner)
        source=BytesIO()
        Image.new('RGB',(16,16),'red').save(source,'JPEG')
        upload=SimpleUploadedFile('falszywe.html',source.getvalue()+b'<script>alert(1)</script>',content_type='image/jpeg')
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            response=self.client.post(f'/api/events/{e.pk}/image',{'image':upload},HTTP_X_CSRFTOKEN=self.client.cookies['csrftoken'].value)
            self.assertEqual(response.status_code,200,response.content)
            e.refresh_from_db()
            self.assertTrue(e.image.name.endswith('.jpg'))
            with e.image.open('rb') as stored:
                self.assertNotIn(b'<script>',stored.read())
            missing=self.client.post(f'/api/events/{e.pk}/image',{},HTTP_X_CSRFTOKEN=self.token)
            self.assertEqual(missing.status_code,400)
            e.refresh_from_db()
            self.assertTrue(e.image.name.endswith('.jpg'))

    def test_admin_login_is_limited_and_api_does_not_cache_private_data(self):
        for _ in range(15):
            response=self.client.post('/admin/login/',{'username':'nieistniejacy','password':'wrong'},HTTP_X_CSRFTOKEN=self.token)
            self.assertNotEqual(response.status_code,429)
        self.assertEqual(self.client.post('/admin/login/',{'username':'nieistniejacy','password':'wrong'},HTTP_X_CSRFTOKEN=self.token).status_code,429)
        self.assertEqual(self.client.get('/api/bootstrap')['Cache-Control'],'no-store')

    def test_security_headers_on_app_and_media(self):
        from django.http import HttpResponse
        from .security import AppHeadersMiddleware
        middleware=AppHeadersMiddleware(lambda request:HttpResponse('<html></html>',content_type='text/html'))
        from django.test import RequestFactory
        factory=RequestFactory()
        page=middleware(factory.get('/'))
        self.assertIn("object-src 'none'",page['Content-Security-Policy'])
        media=middleware(factory.get('/media/a.jpg'))
        self.assertIn('sandbox',media['Content-Security-Policy'])

    def test_contact_limit_ignores_untrusted_forwarded_for(self):
        import os
        from unittest.mock import patch
        data={'reply':'autor@example.org','subject':'Pytanie','message':'Dzień dobry'}
        with patch.dict(os.environ,{'CONTACT_TO_EMAIL':'kontakt@example.org'}),patch('core.views.EmailMessage.send',return_value=1):
            for i in range(6):
                data['reply']=f'autor{i}@example.org'
                response=self.client.post('/api/contact',data=json.dumps(data),content_type='application/json',HTTP_X_CSRFTOKEN=self.token,HTTP_X_FORWARDED_FOR=f'10.0.0.{i}')
                if i<5:self.assertEqual(response.status_code,200,response.content)
                else:self.assertEqual(response.status_code,429)

    def test_registration_bounded_and_login_accepts_admin_username(self):
        for _ in range(30):
            self.assertEqual(self.post('/api/auth/register',{'email':'bad','name':'A','password':'bad'}).status_code,400)
        self.assertEqual(self.post('/api/auth/register',{'email':'good@example.org','name':'Nowy','password':'Bezpieczne-Haslo-123'}).status_code,429)
        admin=User.objects.create_superuser(username='Administrator',email='',password='super-bezpieczne-123')
        c=Client(enforce_csrf_checks=True);c.get('/api/bootstrap')
        self.assertEqual(self.post('/api/auth/login',{'email':admin.username,'password':'super-bezpieczne-123'},c).status_code,200)

    def test_bad_payload_and_feeds_are_bounded(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post('/api/events',data='x'*101_000,content_type='application/json',HTTP_X_CSRFTOKEN=self.token).status_code,400)
        self.assertEqual(self.post('/api/events',{'title':'Absurdalna data','description':'Opis','place':'Sala','startsAt':'9999-12-31T23:59:59Z'}).status_code,400)
        for i in range(105):Announcement.objects.create(creator=self.owner,body=f'Ogłoszenie {i}')
        response=self.client.get('/api/announcements')
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.json()),60)
        self.assertEqual(len(self.client.get('/api/announcements?offset=60').json()),45)
        self.assertEqual(self.client.get('/api/announcements?offset=10001').status_code,400)

    def test_event_feeds_are_paged_and_separated_by_date(self):
        from datetime import timedelta
        from django.utils import timezone
        tomorrow=timezone.now()+timedelta(days=2)
        Event.objects.bulk_create([Event(creator=self.owner,title=f'Spotkanie {i}',description='Opis',starts_at=tomorrow+timedelta(minutes=i),place='Sala') for i in range(62)])
        Event.objects.create(creator=self.owner,title='Dawne',description='Opis',starts_at=timezone.now()-timedelta(days=3),place='Sala')
        self.assertEqual(len(self.client.get('/api/events?scope=upcoming').json()),60)
        self.assertEqual(len(self.client.get('/api/events?scope=upcoming&offset=60').json()),2)
        past=self.client.get('/api/events?scope=past').json()
        self.assertEqual(len(past),1)
        self.assertTrue(past[0]['archived'])

    def test_archived_event_cannot_accept_new_signup_or_task(self):
        from datetime import timedelta
        from django.utils import timezone
        event=Event.objects.create(creator=self.owner,title='Wczoraj',description='Opis',starts_at=timezone.now()-timedelta(days=2),place='Sala')
        task=Task.objects.create(event=event,title='Pomoc')
        self.client.force_login(self.other)
        self.assertTrue(self.client.get(f'/api/events/{event.pk}').json()['archived'])
        self.assertEqual(self.post(f'/api/events/{event.pk}/signup',{'anonymous':False}).status_code,400)
        self.assertEqual(self.post(f'/api/tasks/{task.pk}/claim',{}).status_code,400)

import json
import os
import secrets
from datetime import datetime, time
from io import BytesIO
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import RequestDataTooBig, ValidationError
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import FileResponse, JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Announcement, ContactSettings, CreatorSupport, Event, Goal, NavigationTab, Notice, PaymentSettings, Presence, Profile, Signup, Task, TaskClaim
from .security import client_ip, consume, limited, too_many


def respond(data, status=200):
    response=JsonResponse(data, status=status, safe=not isinstance(data, list))
    response['Cache-Control']='no-store'
    return response
def error(message, status=400): return respond({'error':message}, status)
def payload(request):
    try:
        if int(request.META.get('CONTENT_LENGTH') or 0) > 100_000: return None
        body = request.body
        return json.loads(body) if len(body) <= 100_000 else None
    except (ValueError, UnicodeDecodeError, RequestDataTooBig): return None
def require(request, method):
    if request.method != method: return error('Niedozwolona metoda.', 405)
    return None
def signed_in(request):
    if not request.user.is_authenticated: return error('Zaloguj się.', 401)
    return None
def superuser_required(request):
    if not request.user.is_authenticated: return error('Zaloguj się.', 401)
    if not request.user.is_superuser: return error('Brak uprawnień.', 403)
    return None
def display(user):
    if not user: return 'Anonimowy uczestnik'
    try: return user.profile.display_name
    except Profile.DoesNotExist: return user.username.split('@')[0]
def public_name(user):
    try: return display(user) if user.profile.show_name_on_lists else 'Uczestnik prywatny'
    except Profile.DoesNotExist: return 'Uczestnik'
def author(user, anonymous): return 'Anonimowo' if anonymous else display(user)
def archived(e): return timezone.localdate(e.starts_at) < timezone.localdate()
def event_query():
    return Event.objects.select_related('creator','creator__profile').prefetch_related('tasks__claims__user__profile','signups__user__profile')
def fresh_event(event): return event_query().get(pk=event.pk)
def feed_offset(request):
    raw=request.GET.get('offset','0')
    if not raw.isascii() or not raw.isdigit() or len(raw)>5:return None
    offset=int(raw)
    return offset if offset<=10000 else None
def self_info(user):
    if not user.is_authenticated: return None
    profile, _ = Profile.objects.get_or_create(user=user, defaults={'display_name':user.username.split('@')[0]})
    return {'id':user.id,'email':user.email,'name':profile.display_name,'phone':profile.phone,'showName':profile.show_name_on_lists,'moderator':user.is_staff,'admin':user.is_superuser}
def event_data(e, request, detailed=False):
    data={'id':e.id,'title':e.title,'description':e.description,'topicSummary':e.topic_summary,'startsAt':e.starts_at.isoformat(),'place':e.place,'image':e.image.url if e.image else '', 'author':author(e.creator,e.anonymous_author),'mine':request.user.is_authenticated and e.creator_id==request.user.id,'anonymousAuthor':e.anonymous_author,'signupCount':e.signups.count(),'archived':archived(e)}
    data['tasks']=[]
    for t in e.tasks.all():
        claims=list(t.claims.all())
        data['tasks'].append({'id':t.id,'title':t.title,'people':[public_name(c.user) for c in claims],'mine':request.user.is_authenticated and any(c.user_id==request.user.id for c in claims)})
    if detailed:
        token=request.session.get('guest_signup_token','')
        account_signup=request.user.is_authenticated and e.signups.filter(user=request.user).exists()
        guest_signup=bool(token and e.signups.filter(guest_token=token).exists())
        data['signedUp']=account_signup or guest_signup
        data['signupMode']='Z kontem' if account_signup else 'Anonimowo'
        data['presenceAvailable']=data['signedUp'] and 0 <= (e.starts_at-timezone.now()).total_seconds() <= 86400
        data['presenceConfirmed']=(e.confirmations.filter(user=request.user).exists() if request.user.is_authenticated else False) or bool(token and e.confirmations.filter(guest_token=token).exists())
        signups=list(e.signups.all())
        data['participants']=[public_name(s.user) for s in signups if s.user_id]+['Anonimowy uczestnik' for s in signups if not s.user_id]
    return data

def announcement_data(a, request): return {'id':a.id,'body':a.body,'createdAt':a.created_at.isoformat(),'author':author(a.creator,a.anonymous_author),'mine':request.user.is_authenticated and a.creator_id==request.user.id,'canDelete':request.user.is_authenticated and (a.creator_id==request.user.id or request.user.is_staff),'anonymousAuthor':a.anonymous_author}

@ensure_csrf_cookie
def bootstrap(request):
    if (bad:=require(request,'GET')): return bad
    contact_info = contact_data()
    return respond({'user':self_info(request.user),'goals':[{'id':g.id,'title':g.title,'description':g.description} for g in Goal.objects.filter(active=True)],'payment':payment_data(),'support':support_data(),'navigation':navigation_data(),'contactDetails':contact_info,'contactAvailable':bool(contact_info['email'] or os.environ.get('CONTACT_TO_EMAIL'))})

def navigation_data():
    visible = {'home': True, 'announcements': True, 'events': True, 'finance': True, 'tasks': True, 'contact': True, 'support': True}
    for tab in NavigationTab.objects.all():
        visible[tab.key] = tab.visible
    contact = ContactSettings.objects.order_by('pk').first()
    if contact:
        visible['contact'] = contact.visible
    support = CreatorSupport.objects.order_by('pk').first()
    if support:
        visible['support'] = support.visible
    return visible

def support_data():
    p=CreatorSupport.objects.order_by('pk').first()
    return {'visible':p.visible if p else True, 'name':p.name if p else '', 'address':p.address if p else '', 'phone':p.phone if p else '', 'account':p.bank_account if p else ''}

def contact_data():
    p=ContactSettings.objects.order_by('pk').first()
    return {'visible':p.visible if p else True, 'name':p.name if p else '', 'email':p.email if p else '', 'phone':p.phone if p else '', 'address':p.address if p else ''}

def contact_recipient():
    configured=ContactSettings.objects.order_by('pk').first()
    return (configured.email if configured and configured.email else os.environ.get('CONTACT_TO_EMAIL','')).strip()

def admin_settings(request):
    if request.method not in ('GET','PATCH'): return error('Niedozwolona metoda.',405)
    if (bad:=superuser_required(request)): return bad
    if request.method=='GET':
        return respond({'contact':contact_data(),'payment':payment_data(),'support':support_data(),'navigation':navigation_data()})
    data=payload(request)
    if not isinstance(data,dict): return error('Nieprawidłowe dane.')
    try:
        with transaction.atomic():
            contact=ContactSettings.objects.order_by('pk').first() or ContactSettings()
            contact_data_in=data.get('contact')
            if not isinstance(contact_data_in,dict): raise ValidationError('Brak danych kontaktowych.')
            for field in ('name','email','phone','address'):
                value=contact_data_in.get(field,'')
                if not isinstance(value,str): raise ValidationError('Nieprawidłowe dane kontaktowe.')
                setattr(contact,field,value.strip())
            contact.visible=contact_data_in.get('visible',True)
            if type(contact.visible) is not bool: raise ValidationError('Nieprawidłowa widoczność zakładki Kontakt.')
            contact.full_clean()
            contact.save()

            payment_data_in=data.get('payment')
            support_data_in=data.get('support')
            for model,section,visible_field in ((PaymentSettings,payment_data_in,None),(CreatorSupport,support_data_in,'visible')):
                if not isinstance(section,dict): raise ValidationError('Brak danych ustawień przelewu lub wsparcia.')
                instance=model.objects.order_by('pk').first() or model()
                for source,target in (('name','name'),('address','address'),('phone','phone'),('account','bank_account')):
                    value=section.get(source,'')
                    if not isinstance(value,str): raise ValidationError('Nieprawidłowe dane ustawień.')
                    setattr(instance,target,value.strip())
                if visible_field:
                    instance.visible=section.get('visible',True)
                    if type(instance.visible) is not bool: raise ValidationError('Nieprawidłowa widoczność zakładki Wsparcie.')
                instance.full_clean()
                instance.save()

            nav=data.get('navigation')
            allowed={'home','announcements','events','finance','tasks','contact','support'}
            if not isinstance(nav,dict) or set(nav)!=allowed or any(type(v) is not bool for v in nav.values()):
                raise ValidationError('Nieprawidłowe ustawienia zakładek.')
            contact.visible=nav['contact'];contact.save(update_fields=['visible'])
            support=CreatorSupport.objects.order_by('pk').first()
            support.visible=nav['support'];support.save(update_fields=['visible'])
            for key in ('home','announcements','events','finance','tasks'):
                NavigationTab.objects.update_or_create(key=key,defaults={'visible':nav[key]})
    except ValidationError as exc:
        return error(' '.join(exc.messages))
    return respond({'saved':True})

def payment_data():
    p=PaymentSettings.objects.first()
    return {'name':p.name if p else '', 'address':p.address if p else '', 'phone':p.phone if p else '', 'account':p.bank_account if p else ''}

def register(request):
    if (bad:=require(request,'POST')): return bad
    if not consume('register-ip',client_ip(request),30,3600):return too_many()
    data=payload(request)
    if not isinstance(data,dict): return error('Nieprawidłowe dane.')
    if not isinstance(data.get('email'),str) or not isinstance(data.get('name'),str):return error('Nieprawidłowe dane.')
    email=data['email'].strip().lower(); name=data['name'].strip(); password=data.get('password','')
    if len(email)>150 or not isinstance(password,str) or len(password)>256:return error('Nieprawidłowe dane.')
    try: validate_email(email); validate_password(password)
    except ValidationError as exc: return error(' '.join(exc.messages))
    if not name or len(name)>80: return error('Podaj nazwę do 80 znaków.')
    try:
        with transaction.atomic():
            user=User.objects.create_user(username=email,email=email,password=password)
            Profile.objects.create(user=user,display_name=name)
    except IntegrityError: return error('Konto z takim adresem już istnieje.',409)
    login(request,user)
    return respond({'user':self_info(user)},201)

def sign_in(request):
    if (bad:=require(request,'POST')): return bad
    data=payload(request)
    if not isinstance(data,dict): return error('Nieprawidłowe dane.')
    if not isinstance(data.get('email'),str):return error('Nieprawidłowe dane.')
    identifier=data['email'].strip();password=data.get('password','')
    if not isinstance(password,str) or len(identifier)>150 or len(password)>256:return error('Nieprawidłowe dane.')
    username=identifier.lower() if '@' in identifier else identifier
    ip=client_ip(request)
    if limited('login-ip',ip,30) or limited('login-email',username.casefold(),10):return too_many()
    user=authenticate(request,username=username,password=password)
    if not user:
        consume('login-ip',ip,30,600)
        consume('login-email',username.casefold(),10,600)
        return error('Nieprawidłowa nazwa lub hasło.',401)
    login(request,user); return respond({'user':self_info(user)})

def sign_out(request):
    if (bad:=require(request,'POST')): return bad
    logout(request); return respond({'user':None})

def profile(request):
    if (bad:=signed_in(request)): return bad
    if request.method=='GET': return respond({'user':self_info(request.user)})
    if request.method!='PATCH': return error('Niedozwolona metoda.',405)
    data=payload(request)
    if not isinstance(data,dict): return error('Nieprawidłowe dane.')
    if not isinstance(data.get('name'),str) or not isinstance(data.get('phone',''),str):return error('Nieprawidłowe dane.')
    name=data['name'].strip(); phone=data.get('phone','').strip()
    if not name or len(name)>80 or len(phone)>30: return error('Sprawdź nazwę i numer telefonu.')
    if not isinstance(data.get('showName',True),bool):return error('Nieprawidłowe dane.')
    if not consume('profile-edit-user',request.user.id,120,3600):return too_many()
    p=request.user.profile;p.display_name=name;p.phone=phone;p.show_name_on_lists=data.get('showName',True);p.save()
    return respond({'user':self_info(request.user)})

def valid_event(data):
    if any(not isinstance(data.get(key),str) for key in ('title','description','place','startsAt')):return None
    if not isinstance(data.get('topicSummary',''),str) or type(data.get('anonymousAuthor',False)) is not bool:return None
    title=data['title'].strip();desc=data['description'].strip();place=data['place'].strip()
    try:dt=parse_datetime(data['startsAt'])
    except (ValueError, OverflowError, TypeError):return None
    if not title or len(title)>180 or not desc or len(desc)>10000 or not place or len(place)>180 or dt is None or not 2000 <= dt.year <= 2100: return None
    if timezone.is_naive(dt): dt=timezone.make_aware(dt,timezone.get_current_timezone())
    topic_summary=data.get('topicSummary','').strip()
    if len(topic_summary)>4000: return None
    return {'title':title,'description':desc,'topic_summary':topic_summary,'place':place,'starts_at':dt,'anonymous_author':data.get('anonymousAuthor',False)}

def events(request):
    if request.method=='GET':
        offset=feed_offset(request)
        if offset is None:return error('Nieprawidłowa strona listy.')
        scope=request.GET.get('scope','recent')
        if scope not in ('recent','upcoming','past'):return error('Nieprawidłowy widok listy.')
        query=event_query()
        if scope!='recent':
            midnight=timezone.make_aware(datetime.combine(timezone.localdate(),time.min))
            query=query.filter(starts_at__gte=midnight) if scope=='upcoming' else query.filter(starts_at__lt=midnight)
        query=query.order_by('starts_at','id') if scope=='upcoming' else query.order_by('-starts_at','-id')
        return respond([event_data(e,request) for e in query[offset:offset+60]])
    if (bad:=require(request,'POST')) or (bad:=signed_in(request)): return bad
    data=payload(request)
    if not isinstance(data,dict) or not (fields:=valid_event(data)): return error('Uzupełnij tytuł, datę, miejsce i opis.')
    if not consume('event-create-user',request.user.id,20,86400):return too_many()
    e=Event.objects.create(creator=request.user,**fields)
    return respond(event_data(fresh_event(e),request,True),201)

def event(request,pk):
    e=event_query().filter(pk=pk).first()
    if not e: return error('Nie znaleziono wydarzenia.',404)
    if request.method=='GET': return respond(event_data(e,request,True))
    if (bad:=signed_in(request)): return bad
    if e.creator_id != request.user.id: return error('Tylko autor może zmienić lub usunąć wydarzenie.',403)
    if request.method=='DELETE':
        e.delete();return respond({'deleted':True})
    if request.method!='PATCH': return error('Niedozwolona metoda.',405)
    data=payload(request)
    if not isinstance(data,dict) or not (fields:=valid_event(data)): return error('Uzupełnij tytuł, datę, miejsce i opis.')
    if not consume('event-edit-user',request.user.id,120,3600):return too_many()
    for key,value in fields.items(): setattr(e,key,value)
    e.save();return respond(event_data(fresh_event(e),request,True))

def signup(request,pk):
    e=Event.objects.filter(pk=pk).first()
    if not e: return error('Nie znaleziono wydarzenia.',404)
    if request.method not in ('POST','DELETE'): return error('Niedozwolona metoda.',405)
    data=payload(request) if request.method=='POST' else {}
    if request.method=='POST' and (not isinstance(data,dict) or type(data.get('anonymous')) is not bool):return error('Nieprawidłowy sposób zapisu.')
    anonymous=data.get('anonymous',False)
    token=request.session.get('guest_signup_token','')
    if request.method=='POST':
        if archived(e):return error('Spotkanie już się odbyło.',400)
        if not anonymous and not request.user.is_authenticated: return error('Zaloguj się lub wybierz zapis anonimowy.',401)
        if anonymous:
            if not consume('signup-guest-ip',client_ip(request),60,3600):return too_many()
        elif not consume('signup-user',request.user.id,100,3600):return too_many()
        if anonymous:
            if not token: token=secrets.token_urlsafe(32);request.session['guest_signup_token']=token
            if request.user.is_authenticated:
                e.signups.filter(user=request.user).delete()
                e.confirmations.filter(user=request.user).delete()
            Signup.objects.get_or_create(event=e,guest_token=token,defaults={'user':None})
        else:
            if token:
                e.signups.filter(guest_token=token).delete()
                e.confirmations.filter(guest_token=token).delete()
            Signup.objects.get_or_create(event=e,user=request.user,defaults={'guest_token':''})
    else:
        if request.user.is_authenticated:
            e.signups.filter(user=request.user).delete()
            e.confirmations.filter(user=request.user).delete()
        if token:
            e.signups.filter(guest_token=token).delete()
            e.confirmations.filter(guest_token=token).delete()
    return respond(event_data(fresh_event(e),request,True))

def presence(request,pk):
    if request.method not in ('POST','DELETE'):return error('Niedozwolona metoda.',405)
    e=Event.objects.filter(pk=pk).first()
    if not e:return error('Nie znaleziono wydarzenia.',404)
    if not (0 <= (e.starts_at-timezone.now()).total_seconds() <= 86400):return error('Potwierdzenie otwiera się 24 godziny przed spotkaniem.',400)
    token=request.session.get('guest_signup_token','')
    if request.method=='POST':
        if not ((request.user.is_authenticated and e.signups.filter(user=request.user).exists()) or (token and e.signups.filter(guest_token=token).exists())):
            return error('Najpierw zapisz się na spotkanie.',403)
        if request.user.is_authenticated:Presence.objects.get_or_create(event=e,user=request.user)
        else:
            if not token:token=secrets.token_urlsafe(32);request.session['guest_signup_token']=token
            Presence.objects.get_or_create(event=e,guest_token=token)
    else:
        if request.user.is_authenticated:e.confirmations.filter(user=request.user).delete()
        if token:e.confirmations.filter(guest_token=token).delete()
    return respond(event_data(fresh_event(e),request,True))

def event_tasks(request,pk):
    if (bad:=require(request,'PUT')) or (bad:=signed_in(request)): return bad
    e=Event.objects.filter(pk=pk).first()
    if not e: return error('Nie znaleziono wydarzenia.',404)
    if e.creator_id!=request.user.id: return error('Tylko autor może edytować zadania.',403)
    data=payload(request)
    if not isinstance(data,dict) or not isinstance(data.get('tasks'),list) or len(data['tasks'])>50: return error('Nieprawidłowa lista zadań.')
    incoming=data['tasks'];seen=set();incoming_ids=set()
    for item in incoming:
        if not isinstance(item,dict) or not isinstance(item.get('title'),str) or not item['title'].strip() or len(item['title'].strip())>180:return error('Nazwa zadania musi mieć od 1 do 180 znaków.')
        item_id=item.get('id')
        if item_id is not None:
            if type(item_id) is not int or item_id<=0 or item_id in incoming_ids:return error('Nieprawidłowy identyfikator zadania.')
            incoming_ids.add(item_id)
            if not Task.objects.filter(pk=item_id,event=e).exists():return error('Nie można zmienić obcego zadania.',403)
    if not consume('task-edit-user',request.user.id,120,3600):return too_many()
    with transaction.atomic():
        for i,item in enumerate(incoming):
            if not isinstance(item,dict): return error('Nieprawidłowe zadanie.')
            title=item['title'].strip()
            if not title or len(title)>180: return error('Nazwa zadania musi mieć od 1 do 180 znaków.')
            task=Task.objects.filter(pk=item['id'],event=e).first() if item.get('id') else None
            if item.get('id') and not task: return error('Nie można zmienić obcego zadania.',403)
            if task:task.title=title;task.position=i;task.save();seen.add(task.id)
            else:seen.add(Task.objects.create(event=e,title=title,position=i).id)
        e.tasks.exclude(pk__in=seen).delete()
    return respond(event_data(fresh_event(e),request,True))

def claim(request,pk):
    if (bad:=signed_in(request)): return bad
    task=Task.objects.select_related('event').filter(pk=pk).first()
    if not task: return error('Nie znaleziono zadania.',404)
    if request.method in ('POST','DELETE') and not consume('claim-user',request.user.id,120,3600):return too_many()
    if request.method=='POST' and archived(task.event):return error('Spotkanie już się odbyło.',400)
    if request.method=='POST': TaskClaim.objects.get_or_create(task=task,user=request.user)
    elif request.method=='DELETE': TaskClaim.objects.filter(task=task,user=request.user).delete()
    else:return error('Niedozwolona metoda.',405)
    return respond(event_data(fresh_event(task.event),request,True))

def announcements(request):
    if request.method=='GET':
        offset=feed_offset(request)
        if offset is None:return error('Nieprawidłowa strona listy.')
        return respond([announcement_data(a,request) for a in Announcement.objects.select_related('creator','creator__profile').all()[offset:offset+60]])
    if (bad:=require(request,'POST')) or (bad:=signed_in(request)): return bad
    data=payload(request)
    if not isinstance(data,dict): return error('Nieprawidłowe dane.')
    if not isinstance(data.get('body'),str) or type(data.get('anonymousAuthor',False)) is not bool:return error('Nieprawidłowe dane.')
    body=data['body'].strip()
    if not body or len(body)>10000:return error('Ogłoszenie musi mieć od 1 do 10000 znaków.')
    if not consume('announcement-create-user',request.user.id,30,86400):return too_many()
    a=Announcement.objects.create(creator=request.user,body=body,anonymous_author=data.get('anonymousAuthor',False))
    return respond(announcement_data(a,request),201)

def announcement(request,pk):
    a=Announcement.objects.filter(pk=pk).select_related('creator','creator__profile').first()
    if not a:return error('Nie znaleziono ogłoszenia.',404)
    if (bad:=signed_in(request)):return bad
    mine=a.creator_id==request.user.id
    if request.method=='DELETE':
        if not mine and not request.user.is_staff:return error('Brak uprawnień.',403)
        if not mine: Notice.objects.create(user=a.creator,text='Twoje ogłoszenie zostało usunięte przez moderatora.')
        a.delete();return respond({'deleted':True})
    if request.method!='PATCH':return error('Niedozwolona metoda.',405)
    if not mine:return error('Tylko autor może edytować ogłoszenie.',403)
    data=payload(request)
    if not isinstance(data,dict):return error('Nieprawidłowe dane.')
    if not isinstance(data.get('body'),str) or type(data.get('anonymousAuthor',False)) is not bool:return error('Nieprawidłowe dane.')
    body=data['body'].strip()
    if not body or len(body)>10000:return error('Ogłoszenie musi mieć od 1 do 10000 znaków.')
    a.body=body;a.anonymous_author=data.get('anonymousAuthor',False);a.save()
    return respond(announcement_data(a,request))

def goals(request):
    if (bad:=require(request,'GET')):return bad
    return respond({'goals':[{'id':g.id,'title':g.title,'description':g.description} for g in Goal.objects.filter(active=True)],'payment':payment_data()})

def notices(request):
    if (bad:=signed_in(request)):return bad
    if request.method=='GET':return respond([{'id':n.id,'text':n.text,'createdAt':n.created_at.isoformat(),'read':n.read} for n in request.user.notices.all()[:100]])
    if request.method=='POST':request.user.notices.filter(read=False).update(read=True);return respond({'ok':True})
    return error('Niedozwolona metoda.',405)

def contact(request):
    if (bad:=require(request,'POST')):return bad
    recipient=contact_recipient()
    if not recipient:return error('Kontakt nie jest jeszcze skonfigurowany.',503)
    data=payload(request)
    if not isinstance(data,dict):return error('Nieprawidłowe dane.')
    if any(not isinstance(data.get(key),str) for key in ('reply','subject','message')):return error('Nieprawidłowe dane.')
    reply=data['reply'].strip();subject=data['subject'].strip();body=data['message'].strip()
    try:validate_email(reply)
    except ValidationError:return error('Podaj poprawny adres e-mail.')
    if not subject or len(subject)>120 or any(c in subject for c in '\r\n') or not body or len(body)>5000:return error('Podaj temat i wiadomość do 5000 znaków.')
    if not consume('contact-ip',client_ip(request),5,600):return too_many()
    if not consume('contact-email',reply.lower(),3,600):return too_many()
    try:EmailMessage('Berea: '+subject,body,settings.DEFAULT_FROM_EMAIL,[recipient],reply_to=[reply]).send(fail_silently=False)
    except Exception:return error('Nie udało się wysłać wiadomości.',502)
    return respond({'sent':True})

def event_image(request,pk):
    if (bad:=require(request,'POST')) or (bad:=signed_in(request)):return bad
    e=Event.objects.filter(pk=pk).first()
    if not e:return error('Nie znaleziono wydarzenia.',404)
    if e.creator_id!=request.user.id:return error('Tylko autor może zmienić zdjęcie.',403)
    file=request.FILES.get('image')
    if not file:return error('Wybierz zdjęcie JPG, PNG lub WebP.',400)
    if file and (file.size>2_000_000 or file.content_type not in ('image/jpeg','image/png','image/webp')):return error('Zdjęcie JPG, PNG lub WebP do 2 MB.',400)
    if file:
        if not consume('image-upload-user',request.user.id,30,3600):return too_many()
        from PIL import Image, ImageOps, UnidentifiedImageError
        import warnings
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(file) as source:
                    if source.format not in ('JPEG','PNG','WEBP') or source.width*source.height>12_000_000:
                        return error('Nieprawidłowy format lub rozmiar zdjęcia.',400)
                    source.load()
                    image=ImageOps.exif_transpose(source)
                    image.thumbnail((2400,2400))
                    if image.mode in ('RGBA','LA') or 'transparency' in image.info:
                        background=Image.new('RGB',image.size,'white')
                        background.paste(image,mask=image.convert('RGBA').getchannel('A'))
                        image=background
                    else:image=image.convert('RGB')
                    output=BytesIO()
                    image.save(output,format='JPEG',quality=82,optimize=True)
                    if output.tell()>3_000_000:return error('Zdjęcie jest za duże po obróbce.',400)
        except (OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning,UnidentifiedImageError):
            return error('Plik nie jest poprawnym zdjęciem.',400)
        old_name=e.image.name
        e.image.save(f'{secrets.token_hex(16)}.jpg',ContentFile(output.getvalue()))
        if old_name:e.image.storage.delete(old_name)
    return respond(event_data(fresh_event(e),request,True))

def app_shell(request):
    index=settings.BASE_DIR/'frontend'/'browser'/'index.html'
    if not index.exists():return error('Najpierw zbuduj frontend: npm run build.',503)
    return FileResponse(index.open('rb'),content_type='text/html')

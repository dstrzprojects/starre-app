import { ChangeDetectorRef, Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Api, AdminSettings, Announcement, Bootstrap, ContactDetails, EventItem, Goal, Notice, Payment, Person, Task } from './api';

type Page='home'|'announcements'|'events'|'finance'|'tasks'|'account'|'contact'|'support'|'detail'|'eventForm'|'announcementForm'|'archive'|'transfer'|'notices'|'adminSettings';
@Component({selector:'app-root',standalone:true,imports:[CommonModule,FormsModule],templateUrl:'./app.html',styleUrl:'./app.css'})
export class App {
  private api=inject(Api);private cd=inject(ChangeDetectorRef);
  page:Page='home';previous:Page='home';loading=true;busy=false;error='';success='';
  user:Person|null=null;events:EventItem[]=[];announcements:Announcement[]=[];goals:Goal[]=[];payment:Payment={name:'',address:'',phone:'',account:''};support={name:'',address:'',phone:'',account:''};contactDetails:ContactDetails={name:'',email:'',phone:'',address:''};adminSettings:AdminSettings={contact:{visible:true,name:'',email:'',phone:'',address:''},payment:{name:'',address:'',phone:'',account:''},support:{visible:true,name:'',address:'',phone:'',account:''},navigation:{home:true,announcements:true,events:true,finance:true,tasks:true,contact:true,support:true}};navigation:Bootstrap['navigation']={home:true,announcements:true,events:true,finance:true,tasks:true,contact:true,support:true};contactAvailable=false;
  moreUpcoming=false;morePast=false;moreAnnouncements=false;
  selected:EventItem|null=null;selectedGoal:Goal|null=null;method:'blik'|'bank'='blik';notices:Notice[]=[];
  installPrompt:any=null;installed=false;showInstallHelp=false;
  loginMode:'login'|'register'='login';credentials={name:'',email:'',password:''};
  profile={name:'',phone:'',showName:true};
  eventDraft={id:0,title:'',description:'',topicSummary:'',startsAt:'',place:'',anonymousAuthor:false,tasks:[] as {id?:number,title:string}[]};
  image:File|null=null;
  announcementDraft={id:0,body:'',anonymousAuthor:false};
  contact={reply:'',subject:'Uwagi do aplikacji',message:''};
  readonly verse='Jak bowiem w jednym ciele mamy wiele członków, a nie wszystkie członki spełniają tę samą czynność – podobnie wszyscy razem tworzymy jedno ciało w Chrystusie, a każdy z osobna jesteśmy nawzajem dla siebie członkami.';
  constructor(){window.addEventListener('beforeinstallprompt',(e:Event)=>{e.preventDefault();this.installPrompt=e;this.changed()});window.addEventListener('appinstalled',()=>{this.installed=true;this.installPrompt=null;this.changed()});void this.initialize()}
  private changed(){this.cd.markForCheck()}
  async initialize(){try{const data=await this.api.call<Bootstrap>('bootstrap');this.user=data.user;this.goals=data.goals;this.payment=data.payment;this.support=data.support;this.contactDetails=data.contactDetails;this.navigation=data.navigation;this.contactAvailable=data.contactAvailable;await Promise.all([this.refreshEvents(),this.refreshAnnouncements()]);this.contact.reply=this.user?.email||'';if(this.user)this.profile={name:this.user.name,phone:this.user.phone,showName:this.user.showName}}catch(e){this.fail(e)}finally{this.loading=false;this.changed()}}
  async refreshEvents(){const [upcoming,past]=await Promise.all([this.api.call<EventItem[]>('events?scope=upcoming'),this.api.call<EventItem[]>('events?scope=past')]);this.events=[...upcoming,...past];this.moreUpcoming=upcoming.length===60;this.morePast=past.length===60;this.changed()}
  async refreshAnnouncements(){this.announcements=await this.api.call<Announcement[]>('announcements');this.moreAnnouncements=this.announcements.length===60;this.changed()}
  async loadMoreEvents(scope:'upcoming'|'past'){await this.action(async()=>{const offset=this.events.filter(e=>e.archived===(scope==='past')).length;const more=await this.api.call<EventItem[]>(`events?scope=${scope}&offset=${offset}`);const ids=new Set(this.events.map(e=>e.id));this.events.push(...more.filter(e=>!ids.has(e.id)));if(scope==='past')this.morePast=more.length===60;else this.moreUpcoming=more.length===60})}
  async loadMoreAnnouncements(){await this.action(async()=>{const more=await this.api.call<Announcement[]>(`announcements?offset=${this.announcements.length}`);const ids=new Set(this.announcements.map(a=>a.id));this.announcements.push(...more.filter(a=>!ids.has(a.id)));this.moreAnnouncements=more.length===60})}
  navigate(page:Page){this.page=page;this.error='';this.success='';this.changed();window.scrollTo(0,0)}
  back(){this.navigate(this.previous||'events')}
  async action(fn:()=>Promise<void>){this.busy=true;this.error='';this.success='';this.changed();try{await fn()}catch(e){this.fail(e)}finally{this.busy=false;this.changed()}}
  fail(e:unknown){this.error=e instanceof Error?e.message:'Wystąpił błąd.';this.changed()}
  toast(s:string){this.success=s;this.changed()}
  now(){return new Date()}
  date(v:string){return new Intl.DateTimeFormat('pl-PL',{day:'numeric',month:'long',timeZone:'Europe/Warsaw'}).format(new Date(v))}
  day(v:string){return new Intl.DateTimeFormat('pl-PL',{weekday:'long',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Warsaw'}).format(new Date(v))}
  localInput(v:string){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Warsaw',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(v)).replace(' ','T')}
  hasPassed(e:EventItem){const eventDay=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Warsaw',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(e.startsAt));const today=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Warsaw',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());return eventDay<today}
  get upcoming(){return this.events.filter(e=>!this.hasPassed(e)).sort((a,b)=>a.startsAt.localeCompare(b.startsAt))}
  get past(){return this.events.filter(e=>this.hasPassed(e)).sort((a,b)=>b.startsAt.localeCompare(a.startsAt))}
  get next(){return this.upcoming[0]||null}
  get myTasks(){return this.events.flatMap(e=>(e.tasks||[]).filter(t=>t.mine).map(t=>({e,t})))}
  async openEvent(id:number){await this.action(async()=>{this.previous=this.page;this.selected=await this.api.call<EventItem>('events/'+id);this.navigate('detail')})}
  async auth(){await this.action(async()=>{const path=this.loginMode==='register'?'auth/register':'auth/login';const data=await this.api.call<{user:Person}>(path,'POST',this.credentials);this.user=data.user;this.profile={name:data.user.name,phone:data.user.phone,showName:data.user.showName};this.contact.reply=data.user.email;this.credentials.password='';this.navigate('home');this.toast('Zalogowano.')})}
  async logout(){await this.action(async()=>{await this.api.call('auth/logout','POST',{});this.user=null;this.navigate('home');this.toast('Wylogowano.')})}
  async saveProfile(){await this.action(async()=>{const data=await this.api.call<{user:Person}>('profile','PATCH',this.profile);this.user=data.user;this.toast('Zapisano profil.')})}
  async signup(anonymous=false){if(!this.selected)return;await this.action(async()=>{this.selected=await this.api.call<EventItem>(`events/${this.selected!.id}/signup`,'POST',{anonymous});await this.refreshEvents();this.toast('Zapisano na spotkanie.')})}
  async togglePresence(){if(!this.selected)return;await this.action(async()=>{const was=this.selected!.presenceConfirmed;if(was&&!confirm('Czy na pewno chcesz zrezygnować z potwierdzenia przybycia?'))return;this.selected=await this.api.call<EventItem>(`events/${this.selected!.id}/presence`,was?'DELETE':'POST');this.toast(was?'Cofnięto potwierdzenie.':'Obecność potwierdzona.')})}
  async cancelSignup(){if(!this.selected)return;await this.action(async()=>{this.selected=await this.api.call<EventItem>(`events/${this.selected!.id}/signup`,'DELETE');await this.refreshEvents();this.toast('Anulowano zapis.')})}
  async claim(task:Task){if(!this.user){this.navigate('account');return}await this.action(async()=>{const e=await this.api.call<EventItem>(`tasks/${task.id}/claim`,task.mine?'DELETE':'POST');this.selected=e;this.events=this.events.map(x=>x.id===e.id?e:x);this.toast(task.mine?'Zrezygnowano z zadania.':'Wybrano zadanie.')})}
  newEvent(){if(!this.user){this.navigate('account');return}this.previous=this.page;this.eventDraft={id:0,title:'',description:'',topicSummary:'',startsAt:'',place:'',anonymousAuthor:false,tasks:[{title:''}]};this.image=null;this.navigate('eventForm')}
  editEvent(e:EventItem){this.previous=this.page;this.eventDraft={id:e.id,title:e.title,description:e.description,topicSummary:e.topicSummary||'',startsAt:this.localInput(e.startsAt),place:e.place,anonymousAuthor:e.anonymousAuthor,tasks:(e.tasks||[]).map(t=>({id:t.id,title:t.title}))};this.image=null;this.navigate('eventForm')}
  addTask(){this.eventDraft.tasks.push({title:''})}
  removeTask(i:number){this.eventDraft.tasks.splice(i,1)}
  async saveEvent(){await this.action(async()=>{const d=this.eventDraft;const event=await this.api.call<EventItem>(d.id?'events/'+d.id:'events',d.id?'PATCH':'POST',{title:d.title,description:d.description,topicSummary:d.topicSummary,place:d.place,startsAt:new Date(d.startsAt).toISOString(),anonymousAuthor:d.anonymousAuthor});let current=event;if(this.image){const form=new FormData();form.append('image',this.image);current=await this.api.call<EventItem>(`events/${event.id}/image`,'POST',form)}current=await this.api.call<EventItem>(`events/${event.id}/tasks`,'PUT',{tasks:d.tasks.filter(t=>t.title.trim())});this.selected=current;await this.refreshEvents();this.navigate('detail');this.toast('Zapisano wydarzenie.')})}
  async deleteEvent(e:EventItem){if(!confirm('Usunąć wydarzenie?'))return;await this.action(async()=>{await this.api.call(`events/${e.id}`,'DELETE');this.selected=null;await this.refreshEvents();this.navigate('events')})}
  onImage(event:Event){this.image=(event.target as HTMLInputElement).files?.[0]||null}
  newAnnouncement(){if(!this.user){this.navigate('account');return}this.previous='announcements';this.announcementDraft={id:0,body:'',anonymousAuthor:false};this.navigate('announcementForm')}
  editAnnouncement(a:Announcement){this.previous='announcements';this.announcementDraft={id:a.id,body:a.body,anonymousAuthor:a.anonymousAuthor};this.navigate('announcementForm')}
  async saveAnnouncement(){await this.action(async()=>{const d=this.announcementDraft;await this.api.call(d.id?'announcements/'+d.id:'announcements',d.id?'PATCH':'POST',d);await this.refreshAnnouncements();this.navigate('announcements');this.toast('Zapisano ogłoszenie.')})}
  async deleteAnnouncement(a:Announcement){if(!confirm('Usunąć ogłoszenie?'))return;await this.action(async()=>{await this.api.call('announcements/'+a.id,'DELETE');await this.refreshAnnouncements();this.toast('Usunięto ogłoszenie.')})}
  openTransfer(g:Goal,method:'blik'|'bank'){this.selectedGoal=g;this.method=method;this.previous='finance';this.navigate('transfer')}
  async copy(value:string){try{await navigator.clipboard.writeText(value);this.toast('Skopiowano.')}catch{this.fail(new Error('Nie udało się skopiować.'))}}
  async loadNotices(){if(!this.user){this.navigate('account');return}await this.action(async()=>{this.notices=await this.api.call<Notice[]>('notices');this.previous='account';this.navigate('notices')})}
  async readNotices(){await this.action(async()=>{await this.api.call('notices','POST',{});this.notices=this.notices.map(n=>({...n,read:true}))})}
  async openAdminSettings(){if(!this.user?.admin)return;await this.action(async()=>{this.adminSettings=await this.api.call<AdminSettings>('admin/settings');this.previous='account';this.navigate('adminSettings')})}
  async saveAdminSettings(){if(!this.user?.admin)return;await this.action(async()=>{await this.api.call('admin/settings','PATCH',this.adminSettings);this.navigation={...this.adminSettings.navigation};this.payment={...this.adminSettings.payment};this.support={name:this.adminSettings.support.name,address:this.adminSettings.support.address,phone:this.adminSettings.support.phone,account:this.adminSettings.support.account};this.contactDetails={name:this.adminSettings.contact.name,email:this.adminSettings.contact.email,phone:this.adminSettings.contact.phone,address:this.adminSettings.contact.address};const bootstrap=await this.api.call<Bootstrap>('bootstrap');this.contactAvailable=bootstrap.contactAvailable;this.toast('Zapisano ustawienia aplikacji.')})}
  async install(){if(this.installPrompt){await this.installPrompt.prompt();this.installPrompt=null;this.changed()}else{this.showInstallHelp=!this.showInstallHelp;this.changed()}}
  async sendContact(){await this.action(async()=>{await this.api.call('contact','POST',this.contact);this.contact.message='';this.toast('Wysłano wiadomość.')})}
}

import { Injectable } from '@angular/core';

export interface Person { id:number; email:string; name:string; phone:string; showName:boolean; moderator:boolean; admin:boolean }
export interface Goal { id:number; title:string; description:string }
export interface Payment { name:string; address:string; phone:string; account:string }
export interface Task { id:number; title:string; people:string[]; mine:boolean }
export interface EventItem { id:number; title:string; description:string; topicSummary:string; startsAt:string; place:string; image:string; author:string; mine:boolean; anonymousAuthor:boolean; signupCount:number; archived:boolean; signedUp?:boolean; signupMode?:string; presenceAvailable?:boolean; presenceConfirmed?:boolean; participants?:string[]; tasks?:Task[] }
export interface Announcement { id:number; body:string; createdAt:string; author:string; mine:boolean; canDelete:boolean; anonymousAuthor:boolean }
export interface Notice { id:number; text:string; createdAt:string; read:boolean }
export interface ContactDetails { name:string; email:string; phone:string; address:string }
export interface Navigation { home:boolean; announcements:boolean; events:boolean; finance:boolean; tasks:boolean; contact:boolean; support:boolean }
export interface AdminSettings { contact:ContactDetails&{visible:boolean}; payment:Payment; support:Payment&{visible:boolean}; navigation:Navigation }
export interface Bootstrap { user:Person|null; goals:Goal[]; payment:Payment; support:{name:string;address:string;phone:string;account:string}; navigation:Navigation; contactDetails:ContactDetails; contactAvailable:boolean }

@Injectable({providedIn:'root'})
export class Api {
  async call<T>(path:string, method='GET', data?:unknown):Promise<T> {
    const headers:Record<string,string>={};
    if(method!=='GET')headers['X-CSRFToken']=decodeURIComponent(document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)?.[1]||'');
    const body=data instanceof FormData?data:data===undefined?undefined:JSON.stringify(data);
    if(body && !(data instanceof FormData))headers['Content-Type']='application/json';
    const res=await fetch('/api/'+path,{method,headers,body,credentials:'same-origin'});
    let result:any;
    try{result=await res.json()}catch{throw Error('Serwer nie odpowiedział poprawnie.')}
    if(!res.ok)throw Error(result.error||'Nie udało się wykonać działania.');
    return result as T;
  }
}

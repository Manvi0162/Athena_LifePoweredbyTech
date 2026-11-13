import { Household, ReceiptItem, UtilityKind } from './types';
export const DEMO_MODE = process.env.EXPO_PUBLIC_USE_MOCKS !== 'false';
const URL = (process.env.EXPO_PUBLIC_API_URL || '').replace(/\/$/,'');
export async function request<T>(path:string,method:'GET'|'POST'|'PATCH'='GET',body?:unknown):Promise<T>{
  if(!URL)throw Error('Backend URL missing. Set EXPO_PUBLIC_API_URL in .env.local.');
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),12000);
  try{
    const response=await fetch(`${URL}${path}`,{method,headers:{'Accept':'application/json','Content-Type':'application/json'},
      body:body===undefined?undefined:JSON.stringify(body),signal:controller.signal});
    let result:unknown=null;
    try{result=await response.json();}catch{}
    if(!response.ok){
      const err=result as {message?:string;detail?:string};
      throw Error(err?.message||err?.detail||`HTTP ${response.status}: ${path}`);
    }
    return result as T;
  }finally{clearTimeout(timer);}
}
export async function uploadImage<T>(path:string,imageUri:string,householdId:string):Promise<T>{
  if(!URL)throw Error('Backend URL missing.');
  const data=new FormData();
  data.append('household_id',householdId);
  data.append('file',{uri:imageUri,name:'receipt.jpg',type:'image/jpeg'} as any);
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),15000);
  try{
    const response=await fetch(`${URL}${path}`,{method:'POST',body:data,signal:controller.signal,
      headers:{Accept:'application/json'}}); // Let fetch generate multipart boundary.
    const result=await response.json();
    if(!response.ok)throw Error(result.message||`Upload error ${response.status}`);
    return result as T;
  }finally{clearTimeout(timer);}
}
// PROPOSED integration contracts, pending confirmation by Members 2–5.
export const routes={
  onboarding:'/households/onboarding',bills:'/bills',forecasts:'/utilities/forecast',
  parse:'/receipts/parse',confirm:'/receipts/confirm',pantry:'/pantry',
  recommend:'/recipes/recommend',insights:'/household/insights',scenario:'/household/scenarios',
};
export type ParsedReceipt = {items:ReceiptItem[]; receipt_id?:string; status?:string};
export function categoryParams(householdId:string,kind:UtilityKind){return `?household_id=${encodeURIComponent(householdId)}&category=${kind}`;}
// Never put service-role keys, AI credentials or private API tokens in EXPO_PUBLIC_ variables.

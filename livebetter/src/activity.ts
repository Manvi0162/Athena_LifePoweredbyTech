import {Activity as ActivityEntry} from './types';

// One section of the Activity tab (AI recommendations, water, electricity, groceries, security).
export type Category='ai'|'water'|'electricity'|'groceries'|'security'|'household';
export const CATEGORY_INFO:Record<Category,{title:string;icon:string;about:string}>={
  ai:{title:'AI recommendations',icon:'✦',about:'What the AI recommends now, and every question you asked the coach.'},
  water:{title:'Water',icon:'◉',about:'Water bills, habits, forecasts and goals.'},
  electricity:{title:'Electricity',icon:'ϟ',about:'Electricity bills, appliances, forecasts and goals.'},
  groceries:{title:'Groceries and pantry',icon:'▤',about:'Receipts confirmed, recipes saved and meals cooked.'},
  security:{title:'Security',icon:'⬡',about:'Pattern checks, blocked attempts, authenticator, resets.'},
  household:{title:'Household',icon:'⌂',about:'Household details and account changes.'},
};
export function categoryOf(e:ActivityEntry):Category{
  if(e.category)return e.category;
  const k=e.kind.toLowerCase();
  if(k==='water'||k==='electricity'||k==='security')return k;
  if(['receipt','cook','pantry','recipe'].includes(k))return 'groceries';
  return 'household';
}

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Activity, Bill, Forecast, Household, Insight, PantryItem, ReceiptItem, Recipe, Scenario, Snapshot, UtilityKind } from './types';

const KEY = '@livebetter-v1-demo';
const initial: Snapshot = {
  household:null, bills:[], receipts:[], activity:[], completed_actions:[],
  pantry:[
    {id:'p-rice',name:'rice',quantity:1,unit:'kg',available:true},
    {id:'p-carrot',name:'carrot',quantity:3,unit:'piece',available:true},
    {id:'p-peas',name:'peas',quantity:0.5,unit:'kg',available:true},
    {id:'p-onion',name:'onion',quantity:4,unit:'piece',available:true},
    {id:'p-egg',name:'egg',quantity:4,unit:'piece',available:true},
  ],
};
export const sampleReceipt: ReceiptItem[] = [
  {name:'rice',quantity:1,unit:'kg',price:95}, {name:'carrot',quantity:2,unit:'piece',price:28},
  {name:'peas',quantity:0.5,unit:'kg',price:70}, {name:'onion',quantity:3,unit:'piece',price:45},
];
const demoRecipes: Omit<Recipe,'missing'|'coverage'>[] = [
  {id:'vegetable-rice',name:'Vegetable Fried Rice',source:'Illustrative demo recipe — not licensed dataset',
    ingredients:[{name:'rice',quantity:0.2,unit:'kg'},{name:'carrot',quantity:1,unit:'piece'},{name:'peas',quantity:0.1,unit:'kg'},{name:'onion',quantity:1,unit:'piece'}],
    instructions:'Cook rice, sauté chopped vegetables, then combine and season.'},
  {id:'vegetable-omelette',name:'Vegetable Omelette',source:'Illustrative demo recipe — not licensed dataset',
    ingredients:[{name:'egg',quantity:2,unit:'piece'},{name:'onion',quantity:1,unit:'piece'},{name:'carrot',quantity:1,unit:'piece'}],
    instructions:'Whisk eggs, add finely chopped vegetables and cook through.'},
  {id:'rice-and-peas',name:'Rice & Peas',source:'Illustrative demo recipe — not licensed dataset',
    ingredients:[{name:'rice',quantity:0.2,unit:'kg'},{name:'peas',quantity:0.15,unit:'kg'}],
    instructions:'Cook the rice and peas and season to taste.'},
];
const today = () => new Date().toISOString();
const id = () => Math.random().toString(36).slice(2,10)+Date.now().toString(36);
const normalized = (s:string) => s.trim().toLowerCase();
const audit = (s: Snapshot,message:string,kind:string) => s.activity.unshift({id:id(),at:today(),message,kind});
export async function loadDemo():Promise<Snapshot> {
  const saved = await AsyncStorage.getItem(KEY);
  if(!saved) return JSON.parse(JSON.stringify(initial));
  try {return JSON.parse(saved) as Snapshot;} catch{return JSON.parse(JSON.stringify(initial));}
}
export const saveDemo = (s:Snapshot) => AsyncStorage.setItem(KEY,JSON.stringify(s));
export async function resetDemo(){await AsyncStorage.removeItem(KEY);return loadDemo();}
export function putHousehold(s:Snapshot, data:Omit<Household,'id'>, assignedId?:string):Snapshot {
  const next={...s, household:{...data,id:assignedId||s.household?.id||'demo-household-001'}};
  audit(next,'Household assessment saved','household');return next;
}
export function putBill(s:Snapshot,bill:Omit<Bill,'id'|'household_id'|'currency'>):Snapshot {
  const next={...s,bills:[...s.bills,{...bill,id:id(),household_id:s.household?.id||'demo-household-001',currency:'MUR' as const}]};
  audit(next,`${bill.kind} historical bill saved (${bill.units} ${bill.kind==='water'?'m³':'kWh'})`,'bill');return next;
}
export function putReceipt(s:Snapshot,items:ReceiptItem[]):Snapshot {
  if(!items.length || items.some(x=>x.quantity<=0||x.price<0||!x.name.trim())) throw Error('Check item names, quantities and prices.');
  const next:Snapshot={...s, pantry:s.pantry.map(x=>({...x})), receipts:[...s.receipts], activity:[...s.activity],completed_actions:[...s.completed_actions]};
  for(const item of items){
    const existing=next.pantry.find(x=>normalized(x.name)===normalized(item.name)&&x.unit===item.unit);
    if(existing){existing.quantity+=item.quantity;existing.available=true;}
    else next.pantry.push({id:id(),name:normalized(item.name),quantity:item.quantity,unit:item.unit,available:true});
  }
  const total=items.reduce((a,x)=>a+x.price,0);
  next.receipts.push({id:id(),at:today(),total});
  audit(next,`Confirmed grocery purchase: ${items.length} items, Rs ${total.toFixed(2)}`,'receipt');return next;
}
export function putPantry(s:Snapshot,item:Omit<PantryItem,'id'> & {id?:string}):Snapshot {
  if(!item.name.trim()||item.quantity<0)throw Error('Name and valid non-negative quantity required.');
  const next:Snapshot={...s,pantry:[...s.pantry],activity:[...s.activity]};
  if(item.id){next.pantry=next.pantry.map(x=>x.id===item.id?{...x,...item,id:x.id}:x);}
  else next.pantry.push({...item,id:id()});
  audit(next,`${item.name} inventory updated`,'pantry');return next;
}
export function getRecipes(s:Snapshot):Recipe[] {
  return demoRecipes.map(recipe=>{
    const missing=recipe.ingredients.filter(ingredient=>{
      const p=s.pantry.find(x=>normalized(x.name)===ingredient.name&&x.unit===ingredient.unit);
      return !p||!p.available||p.quantity<ingredient.quantity;
    }).map(x=>`${x.name} (${x.quantity} ${x.unit})`);
    return {...recipe,missing,coverage:(recipe.ingredients.length-missing.length)/recipe.ingredients.length};
  }).sort((a,b)=>b.coverage-a.coverage);
}
export function putCooking(s:Snapshot,recipeId:string,actionId:string):Snapshot {
  if(s.completed_actions.includes(actionId))return s;
  const recipe=getRecipes(s).find(x=>x.id===recipeId);
  if(!recipe||recipe.missing.length)throw Error('Not enough available ingredients.');
  const next:Snapshot={...s,pantry:s.pantry.map(p=>({...p})),completed_actions:[...s.completed_actions,actionId],activity:[...s.activity]};
  for(const ingredient of recipe.ingredients){
    const p=next.pantry.find(x=>normalized(x.name)===ingredient.name&&x.unit===ingredient.unit)!;
    p.quantity=Number((p.quantity-ingredient.quantity).toFixed(4));
  }
  audit(next,`Cooked ${recipe.name}; pantry stock reduced (no new expense)`,'cook');return next;
}
const dayDiff=(start:string,end:string)=>{
  const a=Date.parse(start+'T00:00:00Z'), b=Date.parse(end+'T00:00:00Z');
  return Math.max(1,Math.round((b-a)/86400000)+1);
};
export function mockForecast(s:Snapshot,category:UtilityKind):Forecast {
  const bills=s.bills.filter(b=>b.kind===category);
  const now=new Date();const start=new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth()+1,1));
  const end=new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth()+2,0));
  const period_start=start.toISOString().slice(0,10),period_end=end.toISOString().slice(0,10);
  if(!bills.length) return {category,period_start,period_end,units:0,unit:category==='water'?'m³':'kWh',value:null,currency:'MUR',method:'No forecast — add a historical bill',confidence:'unavailable',assumptions:['No observed household bill yet.'],source_data:[]};
  const dailyUnits=bills.map(b=>b.units/dayDiff(b.period_start,b.period_end));
  const dailyAmount=bills.map(b=>b.amount/dayDiff(b.period_start,b.period_end));
  const cycleDays=dayDiff(period_start,period_end);
  return {category,period_start,period_end,
    units:Number((dailyUnits.reduce((a,b)=>a+b,0)/bills.length*cycleDays).toFixed(2)),
    unit:category==='water'?'m³':'kWh',
    value:Number((dailyAmount.reduce((a,b)=>a+b,0)/bills.length*cycleDays).toFixed(2)),
    currency:'MUR',method:'Normalized historical consumption and recorded bill cost; NOT a verified CWA/CEB tariff calculation',
    confidence:bills.length>=3?'historical_baseline':'limited_history',
    assumptions:['Next-cycle baseline, not live current-cycle consumption','Recorded bill amounts normalized by billed days','Tariff bands and fees require the verified backend calculator'],source_data:bills.map(b=>b.id)};
}
export function mockInsights(s:Snapshot):Insight {
  const water=mockForecast(s,'water'),elec=mockForecast(s,'electricity');
  const groceries=s.receipts.reduce((a,r)=>a+r.total,0);
  const combined=water.value!=null&&elec.value!=null?water.value+elec.value:null;
  return {period_start:water.period_start,period_end:water.period_end,currency:'MUR',water:water.value,electricity:elec.value,
    groceries_recorded:groceries,total:null,method:'Illustrative summary: two next-cycle utility baselines + recorded purchases (different periods)',
    assumptions:['No comparable combined household expense total can be calculated until category reporting periods align.',
      'Groceries are actual confirmed purchases, not a forecast. Cooking never adds a second expense.',
      'Utility monetary baselines are historical averages, NOT current official slab calculations.'],
    recommendations:[
      'Check pantry stock before shopping; use what you already have first.',
      'Provide multiple historical bills for stronger utility baselines.',
      'Test water/appliance usage scenarios with the official tariff engine when integrated.'
    ],source_data:[...water.source_data,...elec.source_data,...s.receipts.map(r=>r.id)]};
}
export function mockScenario(s:Snapshot,category:UtilityKind,percent:number):Scenario {
  const f=mockForecast(s,category);
  return {baseline:f.value,adjusted:null,delta:null,
    unit_change:f.value==null?null:Number((f.units*percent/100).toFixed(2)),
    message:'Illustrative consumption change only. Verified tariff-based cost savings require the backend utility engine.',
    assumptions:[`${percent}% hypothetical reduction in ${category} usage`,'No tariff-based money saving calculated.']};
}

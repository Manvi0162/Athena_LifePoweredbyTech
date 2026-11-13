import React,{createContext,useCallback,useContext,useEffect,useMemo,useState} from 'react';
import {DEMO_MODE,ParsedReceipt,request,routes,uploadImage,categoryParams} from './api';
import {getRecipes,loadDemo,mockForecast,mockInsights,mockScenario,putBill,putCooking,putHousehold,putPantry,putReceipt,resetDemo,saveDemo} from './mock';
import {Bill,Forecast,Household,Insight,PantryItem,ReceiptItem,Recipe,Scenario,Snapshot,UtilityKind} from './types';

type Context={
  ready:boolean;busy:boolean; demo:boolean; state:Snapshot; error:string|null;
  clearError:()=>void; clearDemo:()=>Promise<void>;
  onboard:(v:Omit<Household,'id'>)=>Promise<void>;
  addBill:(v:Omit<Bill,'id'|'household_id'|'currency'>)=>Promise<void>;
  addItem:(v:Omit<PantryItem,'id'> & {id?:string})=>Promise<void>;
  confirmReceipt:(items:ReceiptItem[],receiptId?:string)=>Promise<void>;
  parseReceipt:(uri:string)=>Promise<ParsedReceipt>;
  forecast:(kind:UtilityKind)=>Promise<Forecast>;
  insights:()=>Promise<Insight>;
  recipes:()=>Promise<Recipe[]>;
  cook:(recipeId:string,actionId:string)=>Promise<void>;
  scenario:(kind:UtilityKind,percent:number)=>Promise<Scenario>;
  refreshPantry:()=>Promise<void>;
};
const empty:Snapshot={household:null,bills:[],pantry:[],receipts:[],activity:[],completed_actions:[]};
const Ctx=createContext<Context|null>(null);
export function useApp(){const v=useContext(Ctx);if(!v)throw Error('Missing AppProvider');return v;}
export function AppProvider({children}:{children:React.ReactNode}){
  const [state,setState]=useState<Snapshot>(empty);const [ready,setReady]=useState(false);
  const [busy,setBusy]=useState(false);const [error,setError]=useState<string|null>(null);
  useEffect(()=>{loadDemo().then(s=>setState(DEMO_MODE?s:{...empty,household:s.household}))
    .catch(e=>setError(String(e))).finally(()=>setReady(true));},[]);
  const commit=useCallback(async (next:Snapshot)=>{setState(next);await saveDemo(next);},[]);
  const execute=useCallback(async(fn:()=>Promise<void>)=>{
    setBusy(true);setError(null);
    try{await fn();}catch(e){const msg=e instanceof Error?e.message:String(e);setError(msg);throw e;}
    finally{setBusy(false);}
  },[]);
  const householdId=state.household?.id||'demo-household-001';
  const onboard=async(v:Omit<Household,'id'>)=>execute(async()=>{
    if(!DEMO_MODE){
      const response=await request<{id?:string;household?:{id:string}}>(routes.onboarding,'POST',{...v});
      const assignedId=response?.household?.id||response?.id;
      if(!assignedId)throw Error('Onboarding API did not return a household ID. Agree on response contract with Member 2.');
      await commit(putHousehold(state,v,assignedId));return;
    }
    await commit(putHousehold(state,v));
  });
  const addBill=async(v:Omit<Bill,'id'|'household_id'|'currency'>)=>execute(async()=>{
    if(!DEMO_MODE)await request(routes.bills,'POST',{...v,household_id:householdId,currency:'MUR'});
    await commit(putBill(state,v));
  });
  const addItem=async(v:Omit<PantryItem,'id'> & {id?:string})=>execute(async()=>{
    if(!DEMO_MODE){
      // Requires Member 2/4 to agree PATCH/POST /pantry; not in original endpoint list.
      await request(routes.pantry,v.id?'PATCH':'POST',{...v,household_id:householdId});
      await refreshPantry();return;
    }
    await commit(putPantry(state,v));
  });
  const refreshPantry=async()=>{
    if(DEMO_MODE)return;
    const result=await request<PantryItem[]|{items:PantryItem[]}>(`${routes.pantry}?household_id=${encodeURIComponent(householdId)}`);
    const items=Array.isArray(result)?result:result.items;
    setState(old=>({...old,pantry:items}));
  };
  const confirmReceipt=async(items:ReceiptItem[],receiptId?:string)=>execute(async()=>{
    if(!DEMO_MODE){await request(routes.confirm,'POST',{household_id:householdId,receipt_id:receiptId,items});await refreshPantry();return;}
    await commit(putReceipt(state,items));
  });
  const parseReceipt=async(uri:string):Promise<ParsedReceipt>=>{
    if(DEMO_MODE)throw Error('Demo mode has no OCR. Enter items manually or load the labeled sample receipt.');
    return uploadImage<ParsedReceipt>(routes.parse,uri,householdId);
  };
  const forecast=async(kind:UtilityKind)=>{
    if(DEMO_MODE)return mockForecast(state,kind);
    return request<Forecast>(`${routes.forecasts}${categoryParams(householdId,kind)}`);
  };
  const insights=async()=>{
    if(DEMO_MODE)return mockInsights(state);
    return request<Insight>(`${routes.insights}?household_id=${encodeURIComponent(householdId)}`);
  };
  const recipes=async()=>{
    if(DEMO_MODE)return getRecipes(state);
    const result=await request<Recipe[]|{recipes:Recipe[]}>(routes.recommend,'POST',{household_id:householdId});
    return Array.isArray(result)?result:result.recipes;
  };
  const cook=async(recipeId:string,actionId:string)=>execute(async()=>{
    if(!DEMO_MODE){await request(`/recipes/${encodeURIComponent(recipeId)}/cook`,'POST',{household_id:householdId,idempotency_key:actionId});await refreshPantry();return;}
    await commit(putCooking(state,recipeId,actionId));
  });
  const scenario=async(kind:UtilityKind,percent:number)=>{
    if(DEMO_MODE)return mockScenario(state,kind,percent);
    return request<Scenario>(routes.scenario,'POST',{household_id:householdId,category:kind,reduction_percent:percent});
  };
  const clearDemo=async()=>{if(!DEMO_MODE)throw Error('Reset is enabled in demo mode only.');setState(await resetDemo());};
  const value=useMemo(()=>({ready,busy,demo:DEMO_MODE,state,error,clearError:()=>setError(null),clearDemo,onboard,addBill,
    addItem,confirmReceipt,parseReceipt,forecast,insights,recipes,cook,scenario,refreshPantry}),
    // Event handlers bind the latest state each render.
    [ready,busy,state,error]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

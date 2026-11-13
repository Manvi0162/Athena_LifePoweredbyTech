import React,{createContext,useCallback,useContext,useEffect,useMemo,useState} from 'react';
import {ApiError,DEMO_MODE,ParsedReceipt,categoryParams,clearSession,getSession,loadSession,newOperationId,request,routes,saveSession,uploadImage} from './api';
import {getRecipes,loadDemo,mockForecast,mockInsights,mockScenario,putBill,putCooking,putHousehold,putPantry,putReceipt,resetDemo,saveDemo} from './mock';
import {Activity,Bill,CoachReply,Forecast,Household,Insight,PantryItem,ReceiptItem,Recipe,Scenario,Snapshot,UtilityKind} from './types';

type Context={
  ready:boolean;busy:boolean; demo:boolean; state:Snapshot; error:string|null; signedIn:boolean;
  clearError:()=>void; clearDemo:()=>Promise<void>;
  login:(email:string,password:string)=>Promise<{household:boolean}>; signup:(email:string,password:string)=>Promise<string>;
  logout:()=>Promise<void>; loadSample:()=>Promise<void>; refreshAll:()=>Promise<void>;
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
  ask:(message:string)=>Promise<CoachReply>;
  refreshPantry:()=>Promise<void>;
};
const empty:Snapshot={household:null,bills:[],pantry:[],receipts:[],activity:[],completed_actions:[]};
const Ctx=createContext<Context|null>(null);
export function useApp(){const v=useContext(Ctx);if(!v)throw Error('Missing AppProvider');return v;}

// ---- backend -> app shapes ----
type ApiPantry={id:string;ingredient_name:string;quantity:number;unit:string;expiry_date?:string|null;available:boolean};
const toPantry=(p:ApiPantry):PantryItem=>({id:p.id,name:p.ingredient_name,quantity:Number(p.quantity),unit:p.unit,
  expiry:p.expiry_date||undefined,available:p.available});
type ApiRecipe={id:string;name:string;ingredients:{name:string;quantity:number|null;unit:string|null;optional?:boolean}[];
  missing:string[];uncertain?:string[];coverage:number;cook_now:boolean;instructions:string;source:string};
const toRecipe=(r:ApiRecipe):Recipe=>({id:r.id,name:r.name,
  ingredients:r.ingredients.filter(i=>!i.optional).map(i=>({name:i.name,quantity:Number(i.quantity||0),unit:i.unit||''})),
  missing:[...r.missing,...(r.uncertain||[]).map(x=>`${x} (check quantity)`)],coverage:r.coverage,
  instructions:r.instructions,source:r.source,cook_now:r.cook_now});

export function AppProvider({children}:{children:React.ReactNode}){
  const [state,setState]=useState<Snapshot>(empty);const [ready,setReady]=useState(false);
  const [busy,setBusy]=useState(false);const [error,setError]=useState<string|null>(null);
  const [signedIn,setSignedIn]=useState(false);

  // ---- live mode: load everything the screens show from the backend ----
  const loadLive=useCallback(async()=>{
    let household:Household|null=null;
    try{household=(await request<{household:Household}>(routes.me)).household;}
    catch(e){if(e instanceof ApiError&&e.status===401){await clearSession();setSignedIn(false);setState(empty);return;}
      if(!(e instanceof ApiError&&e.status===404))throw e;}
    if(!household){setState({...empty});return;}
    const [bills,pantry,activity]=await Promise.all([
      request<Bill[]>(routes.bills),
      request<{items:ApiPantry[]}>(routes.pantry),
      request<Activity[]>(routes.activity)]);
    setState({household,bills,pantry:pantry.items.map(toPantry),receipts:[],activity,completed_actions:[]});
  },[]);

  useEffect(()=>{
    (async()=>{
      try{
        if(DEMO_MODE){setState(await loadDemo());return;}
        const s=await loadSession();
        if(s.token){setSignedIn(true);await loadLive();}
      }catch(e){setError(String(e instanceof Error?e.message:e));}
      finally{setReady(true);}
    })();
  },[loadLive]);

  const commit=useCallback(async (next:Snapshot)=>{setState(next);await saveDemo(next);},[]);
  const execute=useCallback(async(fn:()=>Promise<void>)=>{
    setBusy(true);setError(null);
    try{await fn();}catch(e){const msg=e instanceof Error?e.message:String(e);setError(msg);throw e;}
    finally{setBusy(false);}
  },[]);
  const refreshAll=useCallback(async()=>{if(!DEMO_MODE)await loadLive();},[loadLive]);

  const login=async(email:string,password:string)=>{
    let household=false;
    await execute(async()=>{
      const r=await request<{token:string;refresh_token?:string;mode?:string;user?:{email:string}}>(routes.login,'POST',{email,password});
      await saveSession({token:r.token,refresh_token:r.refresh_token,email:r.user?.email,mode:r.mode});
      setSignedIn(true);await loadLive();
      household=!!(await request<{household:Household}>(routes.me).catch(()=>null));
    });
    return {household};
  };
  const signup=async(email:string,password:string)=>{
    let message='';
    await execute(async()=>{
      const r=await request<{token:string|null;message?:string;refresh_token?:string}>(routes.signup,'POST',{email,password});
      if(r.token){await saveSession({token:r.token,refresh_token:r.refresh_token,email});setSignedIn(true);message='Account created.';}
      else message=r.message||'Account created. Confirm your email, then sign in.';
    });
    return message;
  };
  const logout=async()=>{await clearSession();setSignedIn(false);setState(empty);};
  const loadSample=async()=>execute(async()=>{await request(routes.sample,'POST');await loadLive();});

  const onboard=async(v:Omit<Household,'id'>)=>execute(async()=>{
    if(!DEMO_MODE){
      const response=await request<{id?:string;household?:Household}>(routes.onboarding,'POST',{...v});
      if(!response?.household?.id)throw Error('Onboarding API did not return a household.');
      await loadLive();return;
    }
    await commit(putHousehold(state,v));
  });
  const addBill=async(v:Omit<Bill,'id'|'household_id'|'currency'>)=>execute(async()=>{
    if(!DEMO_MODE){await request(routes.bills,'POST',{...v,currency:'MUR'});await loadLive();return;}
    await commit(putBill(state,v));
  });
  const refreshPantry=useCallback(async()=>{
    if(DEMO_MODE)return;
    const result=await request<{items:ApiPantry[]}>(routes.pantry);
    setState(old=>({...old,pantry:result.items.map(toPantry)}));
  },[]);
  const addItem=async(v:Omit<PantryItem,'id'> & {id?:string})=>execute(async()=>{
    if(!DEMO_MODE){
      if(v.id)await request(routes.pantry,'PATCH',{id:v.id,name:v.name,quantity:v.quantity,unit:v.unit,
        expiry:v.expiry||undefined,available:v.available});
      else await request(routes.pantry,'POST',{name:v.name,quantity:v.quantity,unit:v.unit,expiry:v.expiry||undefined,
        available:v.available});
      await loadLive();return;
    }
    await commit(putPantry(state,v));
  });
  const confirmReceipt=async(items:ReceiptItem[],receiptId?:string)=>execute(async()=>{
    if(!DEMO_MODE){
      // receiptId = source_identifier from /receipts/parse; manual entries get a new one (confirmed once only).
      await request(routes.confirm,'POST',{source_identifier:receiptId||`manual-${newOperationId()}`,
        total:Number(items.reduce((t,i)=>t+i.price,0).toFixed(2)),
        items:items.map(i=>({original_name:i.original_name||i.name,normalized_name:i.name.trim().toLowerCase(),
          quantity:i.quantity,unit:i.unit.trim().toLowerCase(),line_total:i.price,category:i.category}))});
      await loadLive();return;
    }
    await commit(putReceipt(state,items));
  });
  const parseReceipt=async(uri:string):Promise<ParsedReceipt>=>{
    if(DEMO_MODE)throw Error('Demo mode has no OCR. Enter items manually or load the labeled sample receipt.');
    const r=await uploadImage<{source_identifier:string;items:{original_name?:string;normalized_name:string;quantity:number;
      unit:string;line_total:number|null;category?:string}[];retailer?:string;receipt_date?:string;total?:number;excluded_non_food?:string[]}>(routes.parse,uri);
    return {receipt_id:r.source_identifier,retailer:r.retailer,receipt_date:r.receipt_date,total:r.total,
      excluded_non_food:r.excluded_non_food,status:'needs_review',
      items:r.items.map(i=>({name:i.normalized_name,quantity:Number(i.quantity),unit:i.unit,price:Number(i.line_total||0),
        original_name:i.original_name,category:i.category}))};
  };
  const forecast=useCallback(async(kind:UtilityKind)=>{
    if(DEMO_MODE)return mockForecast(state,kind);
    return request<Forecast>(`${routes.forecasts}${categoryParams(kind)}`);
  },[state]);
  const insights=useCallback(async()=>{
    if(DEMO_MODE)return mockInsights(state);
    return request<Insight>(routes.insights);
  },[state]);
  const recipes=useCallback(async()=>{
    if(DEMO_MODE)return getRecipes(state);
    const result=await request<{recipes:ApiRecipe[]}>(routes.recipes);
    return result.recipes.map(toRecipe);
  },[state]);
  const cook=async(recipeId:string,actionId:string)=>execute(async()=>{
    if(!DEMO_MODE){
      // One operation id per tap: the backend deducts stock once even if the request is retried.
      const opId=/^[0-9a-f-]{36}$/i.test(actionId)?actionId:newOperationId();
      await request(`/recipes/${encodeURIComponent(recipeId)}/cook`,'POST',{operation_id:opId});
      await loadLive();return;
    }
    await commit(putCooking(state,recipeId,actionId));
  });
  const scenario=async(kind:UtilityKind,percent:number)=>{
    if(DEMO_MODE)return mockScenario(state,kind,percent);
    return request<Scenario>(routes.scenario,'POST',{category:kind,reduction_percent:percent});
  };
  const ask=async(message:string)=>{
    if(DEMO_MODE)throw Error('demo');
    const r=await request<CoachReply>(routes.coach,'POST',{message,language:'en'});
    loadLive().catch(()=>undefined);
    return r;
  };
  const clearDemo=async()=>{
    if(DEMO_MODE){setState(await resetDemo());return;}
    await execute(async()=>{await request(routes.reset,'POST');await loadLive();});
  };
  const value=useMemo(()=>({ready,busy,demo:DEMO_MODE,state,error,signedIn,clearError:()=>setError(null),clearDemo,
    login,signup,logout,loadSample,refreshAll,onboard,addBill,addItem,confirmReceipt,parseReceipt,forecast,insights,recipes,
    cook,scenario,ask,refreshPantry}),
    // Event handlers bind the latest state each render.
    [ready,busy,state,error,signedIn]);
  // Screens mount only after the saved login is loaded, so their first requests carry the token.
  return <Ctx.Provider value={value}>{ready?children:null}</Ctx.Provider>;
}

export const sessionEmail=()=>getSession().email;

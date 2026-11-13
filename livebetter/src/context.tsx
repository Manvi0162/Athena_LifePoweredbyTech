import React,{createContext,useCallback,useContext,useEffect,useMemo,useState} from 'react';
import {ApiError,DEMO_MODE,ParsedReceipt,categoryParams,clearSession,getSession,loadSession,newOperationId,request,routes,saveSession,uploadImage} from './api';
import {getRecipes,loadDemo,mockForecast,mockInsights,mockScenario,putBill,putCooking,putHousehold,putPantry,putReceipt,resetDemo,saveDemo} from './mock';
import {Plan} from './types';
import {Lang,getLang,loadLang,saveLang} from './i18n';
import {AIRecipe,Explanation,Habits,ParsedBill,RecipeMatch,RecognisedItem} from './types';
import {Activity,AuthenticatorSetup,Bill,CoachReply,Forecast,Household,Insight,LoginResult,PantryItem,ReceiptItem,Recipe,ResetStatus,Scenario,SecurityStatus,SensitiveAction,Snapshot,UtilityKind} from './types';

type Context={
  ready:boolean;busy:boolean; demo:boolean; lang:Lang; setLanguage:(l:Lang)=>Promise<void>; state:Snapshot; error:string|null; signedIn:boolean;
  clearError:()=>void; clearDemo:()=>Promise<void>;
  login:(email:string,password:string)=>Promise<LoginResult>;
  loginCode:(mfaToken:string,code:string,recovery?:boolean)=>Promise<LoginResult>;
  signup:(name:string,email:string,password:string)=>Promise<string>;
  logout:()=>Promise<void>; loadSample:()=>Promise<void>; refreshAll:()=>Promise<void>;
  onboard:(v:Omit<Household,'id'>,stepUp?:string)=>Promise<void>;
  deleteBill:(bill:Bill,stepUp:string)=>Promise<void>;
  // misuse safeguards (backend: core/security.py)
  securityStatus:()=>Promise<SecurityStatus>;
  setPattern:(pattern:number[],proof:{password?:string;code?:string;recovery_code?:string})=>Promise<SecurityStatus>;
  verifyPattern:(action:SensitiveAction,pattern:number[])=>Promise<string>;
  authenticatorSetup:()=>Promise<AuthenticatorSetup>;
  authenticatorConfirm:(code:string)=>Promise<string[]>;
  authenticatorDisable:(proof:{code?:string;recovery_code?:string},stepUp:string)=>Promise<SecurityStatus>;
  resetAccount:(stepUp:string)=>Promise<string>; restoreAccount:(stepUp:string)=>Promise<string>;
  resetStatus:()=>Promise<ResetStatus>;
  // redesign: bill photo, explainable AI, habits, scan-to-cook
  parseBill:(kind:UtilityKind,uri:string)=>Promise<ParsedBill>;
  explain:(kind:UtilityKind)=>Promise<Explanation>;
  habits:(kind:UtilityKind)=>Promise<Habits>;
  saveHabits:(kind:UtilityKind,answers:Record<string,any>)=>Promise<Habits>;
  recognizeFood:(uri:string)=>Promise<{items:RecognisedItem[];message:string}>;
  describeFood:(item:RecognisedItem)=>Promise<string>;
  searchRecipes:(ingredients:string[])=>Promise<RecipeMatch[]>;
  generateRecipe:(ingredients:string[])=>Promise<AIRecipe>;
  saveRecipe:(recipe:AIRecipe['recipe'])=>Promise<string>;
  applyPlan:(question:string)=>Promise<CoachReply>;
  plans:()=>Promise<Plan[]>;
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
  missing:string[];uncertain?:string[];coverage:number;cook_now:boolean;instructions:string;source:string;
  steps?:string[];verification_status?:string|null};
const toRecipe=(r:ApiRecipe):Recipe=>({id:r.id,name:r.name,
  ingredients:r.ingredients.filter(i=>!i.optional).map(i=>({name:i.name,quantity:Number(i.quantity||0),unit:i.unit||''})),
  missing:[...r.missing,...(r.uncertain||[]).map(x=>`${x} (check quantity)`)],coverage:r.coverage,
  instructions:r.instructions,source:r.source,cook_now:r.cook_now,steps:r.steps,
  verification_status:r.verification_status,ai_generated:r.verification_status==='pending'});

export function AppProvider({children}:{children:React.ReactNode}){
  const [state,setState]=useState<Snapshot>(empty);const [ready,setReady]=useState(false);
  const [busy,setBusy]=useState(false);const [error,setError]=useState<string|null>(null);
  const [signedIn,setSignedIn]=useState(false);
  const [lang,setLang]=useState<Lang>(getLang());
  const setLanguage=useCallback(async(l:Lang)=>{await saveLang(l);setLang(l);},[]);

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
        setLang(await loadLang());
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

  type Session={token:string;refresh_token?:string;mode?:string;user?:{email:string}};
  const startSession=async(r:Session,email:string)=>{
    await saveSession({token:r.token,refresh_token:r.refresh_token,email:r.user?.email||email,mode:r.mode});
    setSignedIn(true);await loadLive();
    return !!(await request<{household:Household|null}>(routes.me).then(x=>x.household).catch(()=>null));
  };
  const login=async(email:string,password:string):Promise<LoginResult>=>{
    if(DEMO_MODE){setSignedIn(true);return {household:!!state.household};}
    let out:LoginResult={household:false};
    await execute(async()=>{
      const r=await request<Session&{mfa_required?:boolean;mfa_token?:string;message?:string}>(routes.login,'POST',{email,password});
      if(r.mfa_required&&r.mfa_token){out={household:false,mfa:{token:r.mfa_token,message:r.message||'Enter the code from Microsoft Authenticator.'}};return;}
      out={household:await startSession(r,email)};
    });
    return out;
  };
  const loginCode=async(mfaToken:string,code:string,recovery=false):Promise<LoginResult>=>{
    let out:LoginResult={household:false};
    await execute(async()=>{
      const r=await request<Session>(routes.mfa,'POST',recovery?{mfa_token:mfaToken,recovery_code:code.trim()}:{mfa_token:mfaToken,code:code.trim()});
      out={household:await startSession(r,r.user?.email||'')};
    });
    return out;
  };
  const signup=async(name:string,email:string,password:string)=>{
    if(DEMO_MODE){setSignedIn(true);return 'Demo mode: nothing is sent to a server.';}
    let message='';
    await execute(async()=>{
      const r=await request<{token:string|null;message?:string;refresh_token?:string;mode?:string}>(routes.signup,'POST',{name,email,password});
      if(r.token){await saveSession({token:r.token,refresh_token:r.refresh_token,email,mode:r.mode});setSignedIn(true);message='Account created.';}
      else message=r.message||'Account created. Confirm your email, then log in.';
    });
    return message;
  };
  const logout=async()=>{await clearSession();setSignedIn(false);setState(empty);};
  const loadSample=async()=>execute(async()=>{await request(routes.sample,'POST');await loadLive();});

  const onboard=async(v:Omit<Household,'id'>,stepUp?:string)=>execute(async()=>{
    if(!DEMO_MODE){
      const response=await request<{id?:string;household?:Household}>(routes.onboarding,'POST',{...v},stepUp);
      if(!response?.household?.id)throw Error('Onboarding API did not return a household.');
      await loadLive();return;
    }
    await commit(putHousehold(state,v));
  });
  const addBill=async(v:Omit<Bill,'id'|'household_id'|'currency'>)=>execute(async()=>{
    if(!DEMO_MODE){await request(routes.bills,'POST',{...v,currency:'MUR'});await loadLive();return;}
    await commit(putBill(state,v));
  });
  const deleteBill=async(bill:Bill,stepUp:string)=>execute(async()=>{
    if(DEMO_MODE){await commit({...state,bills:state.bills.filter(b=>b.id!==bill.id)});return;}
    const [kind,id]=bill.id.includes(':')?bill.id.split(':'):[bill.kind,bill.id];
    await request(`/bills/${kind}/${encodeURIComponent(id)}`,'DELETE',undefined,stepUp);
    await loadLive();
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
    const r=await request<CoachReply>(routes.coach,'POST',{message,language:getLang()});
    loadLive().catch(()=>undefined);
    return r;
  };
  const clearDemo=async()=>{if(DEMO_MODE)setState(await resetDemo());};

  // ---- misuse safeguards: every sensitive request carries a one-time permission from the pattern ----
  const live=()=>{if(DEMO_MODE)throw Error('Security features need the LiveBetter backend (set EXPO_PUBLIC_USE_MOCKS=false).');};
  const securityStatus=useCallback(async()=>{live();return request<SecurityStatus>(routes.security);},[]);
  const setPattern=async(pattern:number[],proof:{password?:string;code?:string;recovery_code?:string})=>{
    live();return request<SecurityStatus>(routes.pattern,'PUT',{pattern,...proof});};
  const verifyPattern=async(action:SensitiveAction,pattern:number[])=>{
    live();return (await request<{step_up_token:string}>(routes.verifyPattern,'POST',{pattern,action})).step_up_token;};
  const authenticatorSetup=async()=>{live();return request<AuthenticatorSetup>(routes.authSetup,'POST');};
  const authenticatorConfirm=async(code:string)=>{
    live();return (await request<{recovery_codes:string[]}>(routes.authConfirm,'POST',{code:code.trim()})).recovery_codes;};
  const authenticatorDisable=async(proof:{code?:string;recovery_code?:string},stepUp:string)=>{
    live();return request<SecurityStatus>(routes.authDisable,'POST',proof,stepUp);};
  const resetAccount=async(stepUp:string)=>{
    live();let message='';
    await execute(async()=>{message=(await request<{message:string}>(routes.reset,'POST',undefined,stepUp)).message;await loadLive();});
    return message;};
  const restoreAccount=async(stepUp:string)=>{
    live();let message='';
    await execute(async()=>{message=(await request<{message:string}>(routes.restore,'POST',undefined,stepUp)).message;await loadLive();});
    return message;};
  const resetStatus=useCallback(async()=>{live();return request<ResetStatus>(routes.resetStatus);},[]);

  // ---- redesign: every screen below calls a backend route ----
  const parseBill=async(kind:UtilityKind,uri:string)=>{live();return uploadImage<ParsedBill>(routes.parseBill,uri,{kind});};
  const explain=useCallback(async(kind:UtilityKind)=>{live();return request<Explanation>(`${routes.explain}?category=${kind}&lang=${getLang()}`);},[]);
  const habits=useCallback(async(kind:UtilityKind)=>{live();return request<Habits>(`${routes.habits}/${kind}`);},[]);
  const saveHabits=async(kind:UtilityKind,answers:Record<string,any>)=>{live();let out:Habits|null=null;
    await execute(async()=>{out=await request<Habits>(`${routes.habits}/${kind}`,'PUT',answers);await loadLive();});
    return out as unknown as Habits;};
  const recognizeFood=async(uri:string)=>{live();return uploadImage<{items:RecognisedItem[];message:string}>(routes.recognize,uri);};
  const describeFood=async(item:RecognisedItem)=>{live();
    return (await request<{description:string}>(routes.describe,'POST',{name:item.name,category:item.category,label_text:item.label_text})).description;};
  const searchRecipes=async(ingredients:string[])=>{live();
    return (await request<{matches:RecipeMatch[]}>(routes.searchRecipes,'POST',{ingredients})).matches;};
  const generateRecipe=async(ingredients:string[])=>{live();return request<AIRecipe>(routes.generateRecipe,'POST',{ingredients});};
  const applyPlan=async(question:string)=>{live();
    const r=await request<CoachReply>('/household/coach/apply','POST',{question,language:getLang()});loadLive().catch(()=>undefined);return r;};
  const plans=useCallback(async()=>{live();return request<Plan[]>('/household/plans');},[]);
  const saveRecipe=async(recipe:AIRecipe['recipe'])=>{live();let id='';
    await execute(async()=>{id=(await request<{recipe_id:string}>(routes.drafts,'POST',{recipe})).recipe_id;});
    return id;};
  const value=useMemo(()=>({ready,busy,demo:DEMO_MODE,lang,setLanguage,state,error,signedIn,clearError:()=>setError(null),clearDemo,
    login,loginCode,signup,logout,loadSample,refreshAll,onboard,deleteBill,addBill,addItem,confirmReceipt,parseReceipt,forecast,
    insights,recipes,cook,scenario,ask,refreshPantry,securityStatus,setPattern,verifyPattern,authenticatorSetup,
    authenticatorConfirm,authenticatorDisable,resetAccount,restoreAccount,resetStatus,parseBill,explain,habits,saveHabits,
    recognizeFood,describeFood,searchRecipes,generateRecipe,saveRecipe,applyPlan,plans}),
    // Event handlers bind the latest state each render.
    [ready,busy,state,error,signedIn,lang]);
  // Screens mount only after the saved login is loaded, so their first requests carry the token.
  return <Ctx.Provider value={value}>{ready?children:null}</Ctx.Provider>;
}

export const sessionEmail=()=>getSession().email;

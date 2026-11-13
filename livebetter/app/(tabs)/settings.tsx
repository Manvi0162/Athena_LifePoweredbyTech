import React,{useCallback,useEffect,useState} from 'react';
import {Text,View} from 'react-native';
import {router,useFocusEffect} from 'expo-router';
import {useApp} from '../../src/context';
import {usePattern} from '../../src/pattern';
import {ResetStatus,SecurityStatus} from '../../src/types';
import {C,S} from '../../src/theme';
import {ActionRow,Btn,Card,Label,Note,Page,readError} from '../../src/ui';

export default function Settings(){
  const app=useApp();const {state,demo}=app;
  const guard=usePattern();
  const [sec,setSec]=useState<SecurityStatus|null>(null);
  const [reset,setReset]=useState<ResetStatus|null>(null);
  const [msg,setMsg]=useState<{text:string;bad?:boolean}|null>(null);

  const load=useCallback(async()=>{
    if(demo)return;
    try{const [s,r]=await Promise.all([app.securityStatus(),app.resetStatus()]);setSec(s);setReset(r);}
    catch(e){setMsg({text:readError(e),bad:true});}
  },[demo,app.securityStatus,app.resetStatus]);
  useFocusEffect(useCallback(()=>{void load();},[load]));
  useEffect(()=>{void load();},[state.bills.length,load]);

  const resetAccount=()=>guard.ask('reset_account',async t=>{
    try{setMsg({text:await app.resetAccount(t)});}catch(e){setMsg({text:readError(e),bad:true});}
    await load();
  });
  const restore=()=>guard.ask('restore_account',async t=>{
    try{setMsg({text:await app.restoreAccount(t)});}catch(e){setMsg({text:readError(e),bad:true});}
    await load();
  });

  return <Page back title="Settings" subtitle="Your household and app preferences.">
    {guard.prompt}
    {msg?<Text accessibilityLiveRegion="polite" style={msg.bad?S.error:[S.card,{color:C.green,fontWeight:'700'}]}>{msg.text}</Text>:null}
    <Card>
      <Label>Household details</Label>
      <Note>{state.household?.name||'Household'} · {state.household?.members||0} people · {state.household?.home_type||'Home not set'}</Note>
      <ActionRow icon="⌂" title="Household assessment" subtitle={demo?'Update your household details':'Update your household details (pattern needed)'}
        onPress={()=>router.push('/onboarding')}/>
    </Card>

    <Card>
      <Label>Security</Label>
      {sec?.alert?<Text style={[S.body,{color:C.red,fontWeight:'700'}]}>⚠ {sec.alert.message}</Text>:null}
      <ActionRow icon="⬡" title="Security pattern and Microsoft Authenticator"
        subtitle={demo?'Needs the backend (live mode)':`Pattern ${sec?.pattern_set?'set':'NOT set'} · Authenticator ${sec?.authenticator_on?'on':'off'}`}
        onPress={()=>router.push('/security')}/>
    </Card>

    {!demo?<Card>
      <Label>Account</Label>
      {reset?.restorable?<View style={{gap:8,backgroundColor:C.amber,borderRadius:14,padding:12}}>
        <Text style={S.title}>Your account was reset on {new Date(reset.reset_at!).toLocaleString()}.</Text>
        <Note>Your records can be restored until {new Date(reset.restore_until!).toLocaleString()}.</Note>
        <Btn title="Restore my records (pattern)" onPress={restore}/>
      </View>:null}
      <Note>Reset hides all bills, receipts, pantry and goals. It needs your pattern and can be undone for 24 hours.</Note>
      <Btn title="Reset account (pattern)" danger onPress={resetAccount}/>
      {!state.bills.length?<Btn title="Load sample household (fictional data)" outline
        onPress={()=>void app.loadSample().then(load).catch(e=>setMsg({text:readError(e),bad:true}))}/>:null}
      <Btn title="Sign out" outline onPress={()=>void app.logout().then(()=>router.replace('/welcome'))}/>
    </Card>:<Card>
      <Label>Demo data</Label>
      <Btn title="Reset demo data" outline onPress={()=>void app.clearDemo()}/>
    </Card>}

  </Page>;
}

import React,{useEffect,useState} from 'react';
import {Alert,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {Insight} from '../../src/types';
import {money,S,C} from '../../src/theme';
import {Btn,Card,Label,Loading,Note,Page} from '../../src/ui';
export default function Home(){const {state,insights,demo,clearDemo}=useApp();const [summary,setSummary]=useState<Insight|null>(null),[loading,setLoading]=useState(true);
  useEffect(()=>{let active=true;setLoading(true);insights().then(x=>{if(active)setSummary(x);}).catch(()=>{}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[state]);
  return <Page title="LiveBetter" subtitle={`Hello, ${state.household?.name||'household'} · household overview`}>
    <Card><Label>Utility baseline — next cycle</Label>
      {loading?<Loading/>:<><Note>Historical projections; excludes unverified tariff calculations</Note>
        <View style={S.between}><Text style={S.body}>💧 Water</Text><Text style={S.title}>{money(summary?.water)}</Text></View>
        <View style={S.between}><Text style={S.body}>⚡ Electricity</Text><Text style={S.title}>{money(summary?.electricity)}</Text></View>
        <View style={S.divider}/><Note>Grocery purchases confirmed in this demo state: {money(summary?.groceries_recorded)}</Note>
        <Note>Not added to the forecast: grocery purchases and utility estimates may cover different periods.</Note>
      </>}
      <Btn title="View utility forecasts" onPress={()=>router.push('/(tabs)/utilities')}/>
    </Card>
    <Card><Label>Quick actions</Label><Btn title="📷  Add grocery receipt" onPress={()=>router.push('/receipt')}/>
      <Btn title="🧾  Record historical bill" outline onPress={()=>router.push('/bill')}/>
      <Btn title="🥕  Use pantry ingredients" outline onPress={()=>router.push('/(tabs)/pantry')}/>
      <Btn title="🧠  See explainable advice" outline onPress={()=>router.push('/(tabs)/coach')}/></Card>
    <Card><Label>Your household</Label>
      <Note>{state.household?.members||0} members · {state.household?.home_type||'Not set'} · target {money(state.household?.monthly_target)}</Note>
      <Btn title="Edit assessment" outline onPress={()=>router.push('/onboarding')}/></Card>
    <Card><Label>Latest activity</Label>
      {state.activity.length?state.activity.slice(0,4).map(a=><View key={a.id}><Text style={S.body}>• {a.message}</Text><Note>{new Date(a.at).toLocaleString()}</Note></View>):<Note>No events yet. Save a bill or confirm a receipt.</Note>}
      <Btn title="View activity log" outline onPress={()=>router.push('/activity')}/></Card>
    {demo?<Card><Label>Demo controls</Label><Note>Reset will delete local demo bills, confirmed receipts and inventory edits.</Note>
      <Btn title="Reset local demo data" danger onPress={()=>Alert.alert('Reset demo?','Remove local entries and return to onboarding?',[
        {text:'Cancel',style:'cancel'},{text:'Reset',style:'destructive',onPress:()=>clearDemo().then(()=>router.replace('/onboarding'))}])}/></Card>:null}
    <Note>LiveBetter MVP · Values are examples or estimates until confirmed by a verified backend and real household data.</Note>
  </Page>;
}

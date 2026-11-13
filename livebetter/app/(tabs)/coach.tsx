import React,{useEffect,useState} from 'react';
import {Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {Insight} from '../../src/types';
import {money,S} from '../../src/theme';
import {Btn,Card,Label,Loading,Note,Page} from '../../src/ui';
export default function Coach(){const {state,insights,demo}=useApp();const [data,setData]=useState<Insight|null>(null),[loading,setLoading]=useState(true);
  useEffect(()=>{let active=true;setLoading(true);insights().then(v=>{if(active)setData(v);})
    .catch(()=>{}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[state]);
  return <Page title="Explainable AI Coach" subtitle="Structured evidence and transparent household decisions.">
    {loading?<Loading/>:<>
      <Card><Label>Household spending overview</Label>
        <Note>Utility projection period: {data?.period_start} to {data?.period_end}</Note>
        <View style={S.between}><Text style={S.body}>Water</Text><Text style={S.title}>{money(data?.water)}</Text></View>
        <View style={S.between}><Text style={S.body}>Electricity</Text><Text style={S.title}>{money(data?.electricity)}</Text></View>
        <View style={S.between}><Text style={S.body}>Confirmed grocery purchases</Text><Text style={S.title}>{money(data?.groceries_recorded)}</Text></View>
        <View style={S.divider}/>
        <Text style={S.title}>Comparable total: {money(data?.total)}</Text>
        <Note>Do not sum category amounts with incompatible periods. Grocery purchases are not automatically a future monthly grocery forecast.</Note>
      </Card>
      <Card><Label>Recommended next actions</Label>
        {(data?.recommendations||[]).map((r,i)=><View key={i} style={{gap:5}}><Text style={S.body}>{i+1}. {r}</Text></View>)}
        <Btn title="Try utility what-if planner" onPress={()=>router.push('/(tabs)/utilities')}/>
        <Btn title="Check pantry first" outline onPress={()=>router.push('/(tabs)/pantry')}/>
      </Card>
      <Card><Label>Why these recommendations?</Label>
        <Note>Method: {data?.method||'Not returned'}</Note>
        {(data?.assumptions||[]).map((a,i)=><Note key={i}>• {a}</Note>)}
        <Note>Source records: {data?.source_data?.length||0}</Note>
        <Note>Explainable AI requires traceable calculations. A generated paragraph is not proof of correctness.</Note>
      </Card>
      {demo?<Card><Label>Integration required for final judging</Label>
        <Note>These are deterministic demo suggestions. Member 5 must supply real evidence-based insights and Member 3 must supply tariff-verified scenario savings.</Note>
      </Card>:null}
    </>}
  </Page>;
}

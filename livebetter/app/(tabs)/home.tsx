import React,{useEffect,useState} from 'react';
import {ActivityIndicator,Alert,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {Insight} from '../../src/types';
import {money,S,C} from '../../src/theme';
import {ActionRow,Btn,Card,Label,Note,Page} from '../../src/ui';

export default function Home(){
  const {state,insights,demo,clearDemo}=useApp();
  const [summary,setSummary]=useState<Insight|null>(null);
  const [loading,setLoading]=useState(true);

  useEffect(()=>{
    let active=true;
    insights().then(value=>{if(active)setSummary(value);})
      .catch(()=>{})
      .finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[insights,state]);

  return <Page title={`Hello, ${state.household?.name||'household'}`}
    subtitle="Your household overview">
    <View style={S.heroCard}>
      <Text style={S.heroEyebrow}>NEXT CYCLE · UTILITY BASELINE</Text>
      {loading?<ActivityIndicator color={C.white}/>:<>
        <View style={S.row}>
          <View style={S.heroMetric}>
            <Text style={S.heroMetricLabel}>Water</Text>
            <Text style={S.heroMetricValue}>{money(summary?.water)}</Text>
          </View>
          <View style={S.heroMetric}>
            <Text style={S.heroMetricLabel}>Electricity</Text>
            <Text style={S.heroMetricValue}>{money(summary?.electricity)}</Text>
          </View>
        </View>
        <Text style={S.heroFootnote}>Historical estimates, not verified tariff outputs. Grocery purchases are shown separately.</Text>
      </>}
    </View>

    <View style={{gap:10}}>
      <Label>By category</Label>
      <View style={S.statRow}>
        <View style={[S.statCard,{backgroundColor:C.softBlue}]}>
          <Text style={S.statLabel}>WATER</Text>
          <Text style={S.statValue}>{money(summary?.water)}</Text>
        </View>
        <View style={[S.statCard,{backgroundColor:C.softAmber}]}>
          <Text style={S.statLabel}>ELECTRICITY</Text>
          <Text style={S.statValue}>{money(summary?.electricity)}</Text>
        </View>
        <View style={[S.statCard,{backgroundColor:C.softGreen}]}>
          <Text style={S.statLabel}>GROCERIES</Text>
          <Text style={S.statValue}>{money(summary?.groceries_recorded)}</Text>
        </View>
      </View>
      <Note>Water and electricity are next-cycle baselines. Groceries are confirmed purchases, not a forecast.</Note>
    </View>

    <Card>
      <Label>Recommended next steps</Label>
      <ActionRow icon="🥕" title="Check your pantry first" subtitle="Use what you already have"
        onPress={()=>router.push('/(tabs)/pantry')}/>
      <ActionRow icon="↗" title="Try a utility scenario" subtitle="Explore a hypothetical usage change"
        onPress={()=>router.push('/(tabs)/utilities')}/>
      <ActionRow icon="＋" title="Add groceries" subtitle="Review a receipt and update your pantry"
        onPress={()=>router.push('/receipt')}/>
    </Card>

    <Card>
      <Label>Your household</Label>
      <Note>{state.household?.members||0} members · {state.household?.home_type||'Not set'} · target {money(state.household?.monthly_target)}</Note>
      <Btn title="Edit assessment" outline onPress={()=>router.push('/onboarding')}/>
    </Card>

    <Card>
      <Label>Latest activity</Label>
      {state.activity.length?state.activity.slice(0,3).map(activity=><View key={activity.id} style={{gap:3}}>
        <Text style={S.body}>{activity.message}</Text>
        <Note>{new Date(activity.at).toLocaleString()}</Note>
      </View>):<Note>No events yet. Save a bill or confirm a receipt.</Note>}
      <Btn title="View activity log" outline onPress={()=>router.push('/activity')}/>
    </Card>

    {demo?<Card>
      <Label>Demo controls</Label>
      <Note>Reset removes local demo bills, confirmed receipts and inventory edits.</Note>
      <Btn title="Reset local demo data" danger onPress={()=>Alert.alert('Reset demo?','Remove local entries and return to onboarding?',[
        {text:'Cancel',style:'cancel'},
        {text:'Reset',style:'destructive',onPress:()=>clearDemo().then(()=>router.replace('/onboarding'))},
      ])}/>
    </Card>:null}
    <Note>LiveBetter MVP · Values are examples or estimates until confirmed by a verified backend and real household data.</Note>
  </Page>;
}

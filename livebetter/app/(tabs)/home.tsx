import React,{useEffect,useState} from 'react';
import {ActivityIndicator,Alert,Pressable,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {Insight} from '../../src/types';
import {money,S,C} from '../../src/theme';
import {ActionRow,Btn,Card,Label,Note,Page} from '../../src/ui';

export default function Home(){
  const {state,insights,demo,clearDemo}=useApp();
  const [summary,setSummary]=useState<Insight|null>(null);
  const [loading,setLoading]=useState(true);
  const [confirmReset,setConfirmReset]=useState(false);
  const [resetError,setResetError]=useState<string|null>(null);

  useEffect(()=>{
    let active=true;
    insights().then(value=>{if(active)setSummary(value);})
      .catch(error=>{if(active)Alert.alert('Summary unavailable',String(error));})
      .finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[insights,state]);

  return <Page title="Your household" subtitle={`${state.household?.name||'Welcome home'} · Monthly overview`} showSettings>
    <View style={S.heroCard}>
      <Text style={S.heroEyebrow}>NEXT BILLING CYCLE · UTILITIES</Text>
      {loading?<ActivityIndicator color={C.white}/>:<>
        <Text style={{fontSize:26,fontWeight:'800',color:C.white}}>Your baseline</Text>
        <View style={S.row}>
          <View style={S.heroMetric}>
            <Text style={S.heroMetricLabel}>Water</Text>
            <Text style={S.heroMetricValue}>{summary?.water==null?'No forecast yet':money(summary.water)}</Text>
          </View>
          <View style={S.heroMetric}>
            <Text style={S.heroMetricLabel}>Electricity</Text>
            <Text style={S.heroMetricValue}>{summary?.electricity==null?'No forecast yet':money(summary.electricity)}</Text>
          </View>
        </View>
        <Text style={S.heroFootnote}>Historical estimates, not verified tariff outputs.</Text>
        <Btn title="View utility details  →" outline onPress={()=>router.navigate('/(tabs)/utilities')}/>
      </>}
    </View>

    <View style={{gap:10}}>
      <View style={S.between}><Label>By category</Label><Text style={S.muted}>Next cycle / recorded</Text></View>
      <View style={S.statRow}>
        <Pressable accessibilityRole="button" onPress={()=>router.push('/water')} style={[S.statCard,{backgroundColor:C.softBlue}]}>
          <Text style={S.statLabel}>WATER</Text>
          <Text style={S.statValue}>{summary?.water==null?'No forecast':money(summary.water)}</Text>
        </Pressable>
        <Pressable accessibilityRole="button" onPress={()=>router.push('/electricity')} style={[S.statCard,{backgroundColor:C.softAmber}]}>
          <Text style={S.statLabel}>ELECTRICITY</Text>
          <Text style={S.statValue}>{summary?.electricity==null?'No forecast':money(summary.electricity)}</Text>
        </Pressable>
        <Pressable accessibilityRole="button" onPress={()=>router.navigate('/(tabs)/pantry')} style={[S.statCard,{backgroundColor:C.softGreen}]}>
          <Text style={S.statLabel}>GROCERIES</Text><Text style={S.statValue}>{money(summary?.groceries_recorded)}</Text>
        </Pressable>
      </View>
      <Note>Groceries are confirmed purchases, not a future spending forecast.</Note>
    </View>

    <Card>
      <View style={S.between}><Label>What needs attention?</Label><Text style={S.muted}>TODAY</Text></View>
      <ActionRow icon="▤" title="Use what you have" subtitle={`${state.pantry.filter(item=>item.available&&item.quantity>0).length} ingredients available in your pantry`}
        onPress={()=>router.navigate('/(tabs)/pantry')}/>
      <ActionRow icon="◉" title="Improve your utility baseline" subtitle={state.bills.length?'Add another verified bill':'Add a water or electricity bill'}
        onPress={()=>router.navigate('/(tabs)/utilities')}/>
    </Card>

    <Card>
      <Label>Quick actions</Label>
      <View style={S.statRow}>
        <View style={{flex:1}}><Btn title="Add a bill" outline onPress={()=>router.push('/bill')}/></View>
        <View style={{flex:1}}><Btn title="Scan receipt" outline onPress={()=>router.push('/receipt')}/></View>
      </View>
      <Btn title="Open AI Coach  ✦" onPress={()=>router.navigate('/(tabs)/coach')}/>
    </Card>

    <Card>
      <Label>Your household</Label>
      <Note>{state.household?.members||0} people · {state.household?.home_type||'Home not set'} · target {money(state.household?.monthly_target)}</Note>
      <Btn title="Edit household details" outline onPress={()=>router.push('/onboarding')}/>
    </Card>

    {state.activity.length?<Card>
      <View style={S.between}><Label>Recent activity</Label>
        <Pressable accessibilityRole="button" onPress={()=>router.push('/activity')}><Text style={[S.muted,{color:C.green,fontWeight:'700'}]}>View all</Text></Pressable>
      </View>
      {state.activity.slice(0,2).map(activity=><View key={activity.id} style={{gap:3}}>
        <Text style={S.body}>{activity.message}</Text><Note>{new Date(activity.at).toLocaleString()}</Note>
      </View>)}
    </Card>:null}

    {demo?<Card>
      <Label>Demo controls</Label>
      <Note>Reset removes local demo bills, confirmed receipts and inventory edits.</Note>
      {confirmReset?<View style={{gap:8,backgroundColor:C.dangerBg,borderRadius:14,padding:12}}>
        <Text style={{color:C.red,fontWeight:'700'}}>Remove all local demo records?</Text>
        {resetError?<Text style={{color:C.red}}>{resetError}</Text>:null}
        <Btn title="Confirm reset" danger onPress={async()=>{
          try{await clearDemo();router.replace('/welcome');}
          catch(error){setResetError(String(error));}
        }}/>
        <Btn title="Cancel" outline onPress={()=>{setConfirmReset(false);setResetError(null);}}/>
      </View>:<Btn title="Reset local demo data" danger onPress={()=>setConfirmReset(true)}/>}
    </Card>:null}
  </Page>;
}

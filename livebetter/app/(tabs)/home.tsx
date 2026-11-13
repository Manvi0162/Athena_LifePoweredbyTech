import React,{useEffect,useState} from 'react';
import {ActivityIndicator,Alert,Pressable,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {Insight,SecurityStatus} from '../../src/types';
import {money,S,C} from '../../src/theme';
import {ActionRow,Btn,Card,Label,Note,Page} from '../../src/ui';

export default function Home(){
  const {state,insights,demo,securityStatus}=useApp();
  const [summary,setSummary]=useState<Insight|null>(null);
  const [sec,setSec]=useState<SecurityStatus|null>(null);
  useEffect(()=>{if(!demo)securityStatus().then(setSec).catch(()=>undefined);},[demo,securityStatus,state]);
  const [loading,setLoading]=useState(true);

  useEffect(()=>{
    let active=true;
    insights().then(value=>{if(active)setSummary(value);})
      .catch(error=>{if(active)Alert.alert('Summary unavailable',String(error));})
      .finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[insights,state]);

  const priorities=(summary?.actions||[]).filter(a=>a.kind!=='unlock').slice(0,3);
  return <Page back={false} title="Your household" subtitle={`${state.household?.name||'Welcome home'} · Monthly overview`} showSettings>
    {sec?.alert?<Pressable accessibilityRole="button" onPress={()=>router.push('/security')} style={[S.card,{backgroundColor:C.dangerBg}]}>
      <Text style={[S.title,{color:C.red}]}>⚠ Security alert</Text>
      <Text style={[S.body,{color:C.red}]}>{sec.alert.message}</Text>
      <Text style={[S.muted,{fontWeight:'700'}]}>Tap to review →</Text>
    </Pressable>:null}
    {sec&&!sec.pattern_set?<Pressable accessibilityRole="button" onPress={()=>router.push('/security')} style={[S.card,{backgroundColor:C.amber}]}>
      <Text style={S.title}>Set a security pattern</Text>
      <Note>Without it, anyone using this phone could reset your account or delete bills. Tap to set it.</Note>
    </Pressable>:null}
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
        <Pressable accessibilityRole="button" onPress={()=>router.push('/electricity')} style={[S.statCard,{backgroundColor:C.softElectric}]}>
          <Text style={S.statLabel}>ELECTRICITY</Text>
          <Text style={S.statValue}>{summary?.electricity==null?'No forecast':money(summary.electricity)}</Text>
        </Pressable>
        <Pressable accessibilityRole="button" onPress={()=>router.navigate('/(tabs)/pantry')} style={[S.statCard,{backgroundColor:C.softGreen}]}>
          <Text style={S.statLabel}>GROCERIES</Text><Text style={S.statValue}>{money(summary?.groceries_recorded)}</Text>
        </Pressable>
      </View>
      <Note>Groceries are confirmed purchases, not a future spending forecast.</Note>
    </View>

    {summary?.big_brain_summary||priorities.length?<Card>
      <View style={S.between}><Label>Big Brain priorities</Label><Text style={S.muted}>ALL MODULES</Text></View>
      {summary?.big_brain_summary?<Text style={S.body}>{summary.big_brain_summary}</Text>:null}
      {priorities.map((a,i)=><View key={`${a.module}:${a.action_id}`} style={{gap:3,paddingVertical:8,borderTopWidth:1,borderTopColor:C.line}}>
        <View style={S.between}><Text style={[S.title,{flex:1}]}>{i+1}. {a.title}</Text>
          {a.estimated_savings_mur?<Text style={{color:C.green,fontWeight:'800'}}>{money(a.estimated_savings_mur)}</Text>:null}</View>
        <Note>{a.module.toUpperCase()} · {a.explanation}</Note>
      </View>)}
      <Btn title="Ask the AI Coach about these" outline onPress={()=>router.navigate('/(tabs)/coach')}/>
    </Card>:null}

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

  </Page>;
}

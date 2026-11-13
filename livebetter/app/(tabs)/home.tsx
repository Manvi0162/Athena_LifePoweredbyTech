import React,{useEffect,useState} from 'react';
import {t} from '../../src/i18n';
import {ActivityIndicator,Pressable,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {Insight,SecurityStatus} from '../../src/types';
import {money,S,C} from '../../src/theme';
import {Btn,Note,Page} from '../../src/ui';

type Attention={key:string;icon:string;title:string;detail:string;go:()=>void};
const PASTEL_RED='#FDECEC', RED_LINE='#F5C9C9';

export default function Home(){
  const {state,insights,demo,securityStatus}=useApp();
  const [summary,setSummary]=useState<Insight|null>(null);
  const [sec,setSec]=useState<SecurityStatus|null>(null);
  const [loading,setLoading]=useState(true);

  useEffect(()=>{
    let active=true;
    insights().then(value=>{if(active)setSummary(value);}).catch(()=>undefined)
      .finally(()=>{if(active)setLoading(false);});
    if(!demo)securityStatus().then(v=>{if(active)setSec(v);}).catch(()=>undefined);
    return()=>{active=false;};
  },[insights,securityStatus,demo,state]);

  // What needs attention: security first, then the AI recommendations that matter now (alerts, real savings).
  const items:Attention[]=[];
  if(sec?.alert)items.push({key:'sec',icon:'⚠',title:t('Security alert'),detail:sec.alert.message,go:()=>router.push('/security')});
  if(sec&&!sec.pattern_set)items.push({key:'pattern',icon:'⬡',title:t('Set your security pattern'),
    detail:t('Without it, anyone using this phone could reset your account or delete bills.'),go:()=>router.push('/security')});
  if(!state.bills.some(b=>b.kind==='water'))items.push({key:'wb',icon:'◉',title:t('Add a water bill'),
    detail:t('Needed for your water estimate.'),go:()=>router.push({pathname:'/bill',params:{kind:'water'}})});
  if(!state.bills.some(b=>b.kind==='electricity'))items.push({key:'eb',icon:'ϟ',title:t('Add an electricity bill'),
    detail:t('Needed for your electricity estimate.'),go:()=>router.push({pathname:'/bill',params:{kind:'electricity'}})});
  const ai=(summary?.actions||[]).filter(a=>a.source==='domain_module'&&a.status!=='completed'&&
    (a.kind==='alert'||(a.estimated_savings_mur||0)>0));
  for(const a of ai.slice(0,3)){
    const target=a.module==='food'?'/pantry':a.module==='water'?'/water':'/electricity';
    items.push({key:`${a.module}:${a.action_id}`,icon:a.kind==='alert'?'!':'✦',
      title:a.kind==='alert'?a.title:`${a.title}${a.estimated_savings_mur?` · ${t('save about')} ${money(a.estimated_savings_mur)}`:''}`,
      detail:`${t('AI recommendation')} · ${t(a.module==='water'?'Water':a.module==='electricity'?'Electricity':'Groceries')} · ${a.explanation||''}`.trim(),go:()=>router.push(target as any)});
  }
  if(!state.pantry.some(p=>p.available&&p.quantity>0))items.push({key:'pantry',icon:'▤',title:t('Your pantry is empty'),
    detail:t('Scan a grocery receipt to track what you have.'),go:()=>router.push('/receipt')});

  return <Page back={false} title={t('Your household')} subtitle={`${state.household?.name||t('Welcome home')} · ${t('Monthly overview')}`} showSettings>
    <View style={S.statRow}>
      <View style={{flex:1}}><Btn title={t('＋ Add a bill')} onPress={()=>router.push('/bill')}/></View>
      <View style={{flex:1}}><Btn title={t('Scan a receipt')} outline onPress={()=>router.push('/receipt')}/></View>
    </View>

    <View style={S.heroCard}>
      <Text style={S.heroEyebrow}>{t('NEXT BILLING CYCLE · UTILITIES')}</Text>
      {loading?<ActivityIndicator color={C.white}/>:<>
        <Text style={{fontSize:26,fontWeight:'800',color:C.white}}>{t('Your baseline')}</Text>
        <View style={S.row}>
          <View style={S.heroMetric}>
            <Text style={S.heroMetricLabel}>{t('Water')}</Text>
            <Text style={S.heroMetricValue}>{summary?.water==null?t('No forecast yet'):money(summary.water)}</Text>
          </View>
          <View style={S.heroMetric}>
            <Text style={S.heroMetricLabel}>{t('Electricity')}</Text>
            <Text style={S.heroMetricValue}>{summary?.electricity==null?t('No forecast yet'):money(summary.electricity)}</Text>
          </View>
        </View>
        <Text style={S.heroFootnote}>{t('Estimates from your confirmed bills, calculated with the official CWA and CEB tariffs.')}</Text>
        <Btn title={t('View utility details  →')} outline onPress={()=>router.navigate('/(tabs)/utilities')}/>
      </>}
    </View>

    <View style={{gap:10}}>
      <Text style={S.h2}>{t('By category')}</Text>
      <Pressable accessibilityRole="button" accessibilityLabel="Groceries" onPress={()=>router.navigate('/(tabs)/pantry')}
        style={{backgroundColor:C.softGreen,borderRadius:16,paddingVertical:16,paddingHorizontal:18,gap:4}}>
        <View style={S.between}><Text style={S.statLabel}>{t('GROCERIES · THIS MONTH')}</Text>
          <Text style={{color:C.green,fontWeight:'800'}}>›</Text></View>
        <Text style={[S.statValue,{fontSize:22}]}>{money(summary?.groceries_recorded)}</Text>
        <Note>{state.pantry.filter(p=>p.available&&p.quantity>0).length} ingredients in your pantry · confirmed purchases only</Note>
      </Pressable>

      <View accessibilityLabel="Needs attention" style={{backgroundColor:PASTEL_RED,borderColor:RED_LINE,borderWidth:1,borderRadius:18,padding:15,gap:4}}>
        <View style={S.between}><Text style={[S.title,{color:C.red}]}>{t('Needs attention')}</Text>
          <Text style={[S.muted,{color:C.red,fontWeight:'700'}]}>{items.length?`${items.length} ${t('TODAY')}`:t('ALL GOOD')}</Text></View>
        {items.length?items.map((it,i)=><Pressable key={it.key} accessibilityRole="button" onPress={it.go}
          style={{flexDirection:'row',gap:10,paddingVertical:9,borderTopWidth:i?1:0,borderTopColor:RED_LINE,alignItems:'flex-start'}}>
          <Text style={{width:22,textAlign:'center',color:C.red,fontWeight:'900',fontSize:15}}>{it.icon}</Text>
          <View style={{flex:1,gap:2}}>
            <Text style={[S.title,{fontSize:14}]}>{it.title}</Text>
            <Text style={[S.muted,{color:'#7A4B4B'}]} numberOfLines={3}>{it.detail}</Text>
          </View>
          <Text style={{color:C.red,fontSize:18}}>›</Text>
        </Pressable>):<Note>{t('Nothing needs your attention right now.')}</Note>}
      </View>
    </View>
  </Page>;
}

import React,{useEffect,useMemo,useState} from 'react';
import {ActivityIndicator,Alert,Pressable,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../context';
import {usePattern} from '../pattern';
import {Explanation,Forecast,Habits,UtilityKind} from '../types';
import {money,S,C} from '../theme';
import {Btn,Card,Label,Note,Page,readError} from '../ui';

// Same layout for water and electricity:
// next billing cycle -> explainable AI (why this estimate) -> past billing cycles -> habits.
export function UtilityDetail({kind}:{kind:UtilityKind}){
  const {state,forecast,explain,habits,deleteBill,demo}=useApp();
  const guard=usePattern();   // deleting a bill removes evidence: the pattern is required
  const [data,setData]=useState<Forecast|null>(null);
  const [why,setWhy]=useState<Explanation|null>(null);
  const [hab,setHab]=useState<Habits|null>(null);
  const [loading,setLoading]=useState(true);
  const isWater=kind==='water';
  const unit=isWater?'m³':'kWh';
  const bills=useMemo(()=>state.bills.filter(bill=>bill.kind===kind)
    .sort((a,b)=>a.period_start.localeCompare(b.period_start)),[state.bills,kind]);

  useEffect(()=>{
    let active=true;
    setLoading(true);
    forecast(kind).then(v=>{if(active)setData(v);}).catch(()=>undefined).finally(()=>{if(active)setLoading(false);});
    if(!demo){
      explain(kind).then(v=>{if(active)setWhy(v);}).catch(()=>undefined);
      habits(kind).then(v=>{if(active)setHab(v);}).catch(()=>undefined);
    }
    return()=>{active=false;};
  },[forecast,explain,habits,kind,state,demo]);

  const remove=(id:string)=>{
    const bill=bills.find(b=>b.id===id);if(!bill)return;
    guard.ask('delete_bill',async t=>{try{await deleteBill(bill,t);}catch(e){Alert.alert('Not deleted',readError(e));}});
  };
  const maxUnits=Math.max(1,...bills.map(bill=>bill.units));
  const answered=hab?hab.questions.filter(q=>{const v=hab.answers[q.id];return Array.isArray(v)?v.length>0:v!=null&&v!=='';}):[];

  return <Page back title={isWater?'Water':'Electricity'}
    subtitle={isWater?'Your next water bill, why we expect it, and your history.':'Your next electricity bill, why we expect it, and your history.'}>
    {guard.prompt}
    <View style={[S.heroCard,{backgroundColor:isWater?'#176E78':'#245C91'}]}>
      <View style={S.between}>
        <Text style={S.heroEyebrow}>NEXT BILLING CYCLE</Text>
        <Text style={{fontSize:10,fontWeight:'800',color:'#E8F4F4'}}>ESTIMATE</Text>
      </View>
      {loading?<ActivityIndicator color={C.white}/>:<>
        <Text style={{fontSize:30,fontWeight:'800',color:C.white}}>{data?.value==null?'No forecast yet':money(data.value)}</Text>
        <Text style={S.heroFootnote}>{data?.value!=null?`${data.units} ${unit} · ${data.period_start} to ${data.period_end}`:
          (data?.status_message||`Add a ${kind} bill to start your baseline.`)}</Text>
        {data?.cost_range?<Text style={S.heroFootnote}>Likely between {money(data.cost_range.low)} and {money(data.cost_range.high)}</Text>:null}
      </>}
    </View>

    <Card>
      <View style={S.between}><Label>Why this estimate</Label>
        <View style={S.tag}><Text style={S.tagText}>EXPLAINABLE AI</Text></View></View>
      {demo?<Note>Explanations come from the backend (live mode).</Note>:!why?<ActivityIndicator color={C.green}/>:<>
        <Text style={S.body}>{why.summary}</Text>
        {why.factors.length?<View style={{borderWidth:1,borderColor:C.line,borderRadius:14,overflow:'hidden'}}>
          {why.factors.map((f,i)=><View key={f.label} style={{flexDirection:'row',padding:10,gap:10,
            backgroundColor:i%2?C.white:C.bg}}>
            <Text style={[S.muted,{width:105,fontWeight:'700'}]}>{f.label}</Text>
            <View style={{flex:1}}><Text style={S.title}>{f.value}</Text><Text style={S.muted}>{f.detail}</Text></View>
          </View>)}
        </View>:null}
        {why.breakdown.length?<View style={{gap:4}}>
          <Text style={S.title}>How the bill is calculated</Text>
          {why.breakdown.map(b=><View key={b.label} style={S.between}>
            <Text style={[S.muted,{flex:1}]}>{b.label}{b.how&&b.how!=='fixed'?` · ${b.how}`:''}</Text>
            <Text style={S.title}>{money(b.rs)}</Text></View>)}
        </View>:null}
        {why.to_improve.length?<View style={{gap:3,backgroundColor:C.softAmber,borderRadius:12,padding:11}}>
          <Text style={S.title}>To make it more accurate</Text>
          {why.to_improve.map((t,i)=><Note key={i}>• {t}</Note>)}
        </View>:null}
        <Note>{why.summary_source==='gemini'?'Written by AI from the calculated figures (numbers checked).':
          'Calculated by LiveBetter from your bills and the official tariff.'}</Note>
      </>}
    </Card>

    <Card>
      <View style={S.between}><Label>Past billing cycles</Label><Text style={S.muted}>{bills.length} bills</Text></View>
      {bills.length?<View style={{height:120,flexDirection:'row',alignItems:'flex-end',justifyContent:'space-around',gap:10,paddingTop:8}}>
        {bills.slice(-6).map(bill=><View key={bill.id} style={{flex:1,alignItems:'center',justifyContent:'flex-end',gap:7,height:'100%'}}>
          <View style={{width:'70%',maxWidth:34,height:Math.max(14,bill.units/maxUnits*80),borderRadius:7,
            backgroundColor:isWater?(bill===bills[bills.length-1]?C.green:'#8ACFD0'):(bill===bills[bills.length-1]?'#3274B8':'#A8C8E8')}}/>
          <Text style={[S.muted,{fontSize:10}]}>{bill.period_start.slice(5,7)}/{bill.period_start.slice(2,4)}</Text>
        </View>)}
      </View>:<Note>No bills yet. Add one to start your baseline.</Note>}
      {[...bills].reverse().map(bill=><View key={bill.id} style={{flexDirection:'row',alignItems:'center',gap:10,paddingVertical:9,borderTopWidth:1,borderTopColor:C.line}}>
        <View style={{flex:1}}>
          <Text style={S.body}>{bill.period_start} – {bill.period_end}</Text>
          <Note>{bill.units} {unit}{bill.amount_source==='tariff_calculation'?' · amount calculated with the tariff':''}</Note>
        </View>
        <Text style={S.title}>{money(bill.amount)}</Text>
        <Pressable accessibilityRole="button" accessibilityLabel={`Delete bill ${bill.period_start}`} onPress={()=>remove(bill.id)}
          hitSlop={8} style={{width:24,height:24,borderRadius:12,backgroundColor:C.dangerBg,alignItems:'center',justifyContent:'center'}}>
          <Text style={{color:C.red,fontWeight:'900',fontSize:12}}>✕</Text></Pressable>
      </View>)}
      <Btn title={isWater?'＋ Add a water bill':'＋ Add an electricity bill'} onPress={()=>router.push({pathname:'/bill',params:{kind}})}/>
    </Card>

    <Card>
      <View style={S.between}><Label>{isWater?'Your water habits':'Your appliances and habits'}</Label>
        {hab?<Text style={S.muted}>{answered.length}/{hab.questions.length} answered</Text>:null}</View>
      {hab&&answered.length?answered.map(q=>{
        const v=hab.answers[q.id];
        const label=(x:string)=>q.options.find(o=>o.value===x)?.label||x;
        return <View key={q.id} style={{gap:1}}>
          <Text style={S.muted}>{q.question}</Text>
          <Text style={S.title}>{Array.isArray(v)?v.map(label).join(', '):label(String(v))}</Text>
        </View>;
      }):<Note>{isWater?'Tell us about showers, laundry and outdoor use: it personalises your estimate and unlocks calculated savings.':
        'Tell us which appliances you use: it personalises your estimate and unlocks calculated savings.'}</Note>}
      <Btn title={isWater?'Edit water habits':'Edit appliances and habits'} outline
        onPress={()=>router.push({pathname:'/habits',params:{kind}})}/>
    </Card>
  </Page>;
}

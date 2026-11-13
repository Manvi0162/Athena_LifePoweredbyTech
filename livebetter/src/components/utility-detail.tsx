import React,{useEffect,useMemo,useState} from 'react';
import {ActivityIndicator,Alert,Pressable,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../context';
import {Forecast,Scenario,UtilityKind} from '../types';
import {money,S,C} from '../theme';
import {usePattern} from '../pattern';
import {Btn,Card,Field,Label,Note,Page,readError} from '../ui';

export function UtilityDetail({kind}:{kind:UtilityKind}){
  const {state,forecast,scenario,deleteBill}=useApp();
  const guard=usePattern();   // deleting a bill removes evidence: the pattern is required
  const [data,setData]=useState<Forecast|null>(null);
  const [result,setResult]=useState<Scenario|null>(null);
  const [reduction,setReduction]=useState('10');
  const [loading,setLoading]=useState(true);
  const bills=useMemo(()=>state.bills.filter(bill=>bill.kind===kind)
    .sort((a,b)=>a.period_start.localeCompare(b.period_start)),[state.bills,kind]);
  const isWater=kind==='water';

  useEffect(()=>{
    let active=true;
    forecast(kind).then(value=>{if(active)setData(value);})
      .catch(error=>{if(active)Alert.alert('Forecast unavailable',String(error));})
      .finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[forecast,kind,state]);

  async function runScenario(){
    const percent=Number(reduction);
    if(!Number.isFinite(percent)||percent<=0||percent>=100)return;
    try{setResult(await scenario('water',percent));}
    catch(error){console.warn('Could not calculate water scenario',error);}
  }

  const maxUnits=Math.max(1,...bills.map(bill=>bill.units));
  return <Page back title={isWater?'Water intelligence':'Electricity insights'}
    subtitle={isWater?'Understand your water use and upcoming bill.':'See your electricity trend and recorded bills.'}>
    {guard.prompt}
    {loading?<ActivityIndicator color={C.green}/>:null}
    <View style={[S.heroCard,{backgroundColor:isWater?'#176E78':'#245C91'}]}>
      <View style={S.between}>
        <Text style={S.heroEyebrow}>{isWater?'NEXT BILLING CYCLE · HISTORICAL BASELINE':'NEXT BILLING CYCLE · RECORDED BASELINE'}</Text>
        <Text style={{fontSize:10,fontWeight:'800',color:'#E8F4F4'}}>ESTIMATE</Text>
      </View>
      <Text style={{fontSize:30,fontWeight:'800',color:C.white}}>{data?.value==null?'No forecast yet':money(data.value)}</Text>
      <Text style={S.heroFootnote}>{data?`${data.units} ${data.unit} projected from prior cycles`:'Add a bill to start your household baseline.'}</Text>
      <Text style={S.heroFootnote}>{data?.confidence==='unavailable'?'No verified bill history yet':`Confidence: ${data?.confidence||'loading'}`}</Text>
    </View>

    <Card>
      <View style={S.between}><Label>{isWater?'Past billing cycles':'Electricity usage history'}</Label><Text style={S.muted}>{bills.length} records</Text></View>
      {bills.length?<View style={{height:132,flexDirection:'row',alignItems:'flex-end',justifyContent:'space-around',gap:10,paddingTop:12}}>
        {bills.slice(-6).map(bill=><View key={bill.id} style={{flex:1,alignItems:'center',justifyContent:'flex-end',gap:7,height:'100%'}}>
          <View style={{width:'70%',maxWidth:34,height:Math.max(14,bill.units/maxUnits*86),borderRadius:7,backgroundColor:isWater?(bill===bills[bills.length-1]?C.green:'#8ACFD0'):(bill===bills[bills.length-1]?'#3274B8':'#A8C8E8')}}/>
          <Text style={[S.muted,{fontSize:10}]}>{bill.period_start.slice(5,7)}/{bill.period_start.slice(2,4)}</Text>
        </View>)}
      </View>:<View style={{borderRadius:14,backgroundColor:C.bg,padding:14}}>
        <Note>No bill history yet. Add a verified bill to start your household baseline.</Note>
      </View>}
      {bills.slice(-3).reverse().map(bill=><View key={bill.id} style={{paddingVertical:9,borderTopWidth:1,borderTopColor:C.line}}>
        <View style={S.between}><Text style={S.body}>{bill.period_start} – {bill.period_end}</Text><Text style={S.title}>{money(bill.amount)}</Text></View>
        <View style={S.between}><Note>{bill.units} {isWater?'m³':'kWh'} · {bill.tariff}</Note>
          <Pressable accessibilityRole="button" accessibilityLabel={`Delete bill ${bill.period_start}`}
            onPress={()=>guard.ask('delete_bill',async t=>{try{await deleteBill(bill,t);}catch(e){Alert.alert('Not deleted',readError(e));}})}>
            <Text style={{color:C.red,fontWeight:'700',fontSize:12}}>🔒 Delete</Text></Pressable></View>
      </View>)}
      <Btn title={isWater?'Add a water bill':'Add an electricity bill'} onPress={()=>router.push({pathname:'/bill',params:{kind}})}/>
    </Card>

    {isWater?<Card>
      <Label>How was this estimated?</Label>
      <Pressable accessibilityRole="button" onPress={()=>router.push({pathname:'/bill',params:{kind:'water'}})} style={S.actionRow}>
        <View style={S.actionIcon}><Text style={S.actionIconText}>▣</Text></View>
        <View style={{flex:1,gap:2}}><Text style={S.title}>Recorded bill history</Text><Text style={S.muted}>{data?.source_data.length||0} source bills used</Text></View>
        <Text style={S.actionArrow}>›</Text>
      </Pressable>
      <View style={{gap:5}}><Text style={S.title}>Estimation method</Text><Note>{data?.method||'Add a bill to see the estimate method'}</Note></View>
      {data?.assumptions.map((assumption,index)=><Note key={index}>• {assumption}</Note>)}
      <Note>A past bill does not measure current meter usage.</Note>
    </Card>:<Card>
      <Label>About this baseline</Label>
      <Note>{data?.method||'The estimate will appear after you record a bill.'}</Note>
      {data?.assumptions.map((assumption,index)=><Note key={index}>• {assumption}</Note>)}
      <Note>This screen shows recorded history; appliance savings and live meter readings are not available.</Note>
    </Card>}

    {isWater?<Card>
      <Label>Try one change</Label>
      <Note>Explore a hypothetical water-use reduction. Savings are illustrative, not a verified tariff quote.</Note>
      <Field label="Usage reduction (%)" value={reduction} onChangeText={setReduction} keyboardType="decimal-pad"/>
      <Btn title="Open water-saving scenario" onPress={runScenario}/>
      {result?<View style={{gap:7,backgroundColor:C.softGreen,borderRadius:14,padding:13}}>
        <Text style={S.title}>{result.message}</Text>
        <Note>Baseline: {money(result.baseline)} · Scenario: {money(result.adjusted)}</Note>
        <Note>Estimated difference: {money(result.delta)}</Note>
        {result.assumptions.map((assumption,index)=><Note key={index}>• {assumption}</Note>)}
      </View>:null}
    </Card>:null}

    {isWater?<Card>
      <Label>Your water habits</Label>
      <Note>{state.household?.water_habit||'Add optional notes about household water use.'}</Note>
      <Btn title="Edit household assessment" outline onPress={()=>router.push('/onboarding')}/>
    </Card>:null}
  </Page>;
}

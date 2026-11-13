import React,{useEffect,useState} from 'react';
import {Alert,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {Forecast,Scenario,UtilityKind} from '../../src/types';
import {money,S,C} from '../../src/theme';
import {Btn,Card,Field,Label,Loading,Note,Page} from '../../src/ui';
export default function Utilities(){const {state,forecast,scenario}=useApp();
  const [data,setData]=useState<{water?:Forecast;electricity?:Forecast}>({});const [loading,setLoading]=useState(true);
  const [kind,setKind]=useState<UtilityKind>('electricity'),[reduction,setReduction]=useState('10');
  const [result,setResult]=useState<Scenario|null>(null);
  useEffect(()=>{let active=true;setLoading(true);Promise.all([forecast('water'),forecast('electricity')])
    .then(([water,electricity])=>{if(active)setData({water,electricity});}).catch(e=>{if(active)Alert.alert('Forecast unavailable',String(e));})
    .finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[state]);
  async function run(){const p=Number(reduction);if(!Number.isFinite(p)||p<=0||p>100)
    return Alert.alert('Invalid reduction','Enter a percentage between 0 and 100.');
    try{setResult(await scenario(kind,p));}catch(e){Alert.alert('Scenario unavailable',String(e));}
  }
  return <Page title="Utility intelligence" subtitle="Water and electricity, based on actual recorded billing periods.">
    <Btn title="+ Add water / electricity bill" onPress={()=>router.push('/bill')}/>
    {loading?<Loading/>:([['water','💧 Water'],['electricity','⚡ Electricity']] as const).map(([category,label])=>{
      const f=data[category];return <Card key={category}>
        <Label>{label}</Label><Text style={S.amount}>{money(f?.value)}</Text>
        <Note>{f?`${f.units} ${f.unit} · ${f.period_start} to ${f.period_end}`:'No forecast yet'}</Note>
        <View style={[S.tag,{backgroundColor:C.amber}]}><Text style={S.muted}>Confidence: {f?.confidence||'unknown'}</Text></View>
        <Note>Method: {f?.method||'Unavailable'}</Note>
        {f?.assumptions?.map((a,i)=><Note key={i}>• {a}</Note>)}
        <Note>Bill records: {f?.source_data.length||0}</Note>
      </Card>;
    })}
    <Card><Label>What-if usage planner</Label>
      <Note>Choose a category and a hypothetical consumption reduction. Offline mode does not invent cost savings.</Note>
      <Btn title={kind==='water'?'✓ Water':'Water'} outline={kind!=='water'} onPress={()=>{setKind('water');setResult(null);}}/>
      <Btn title={kind==='electricity'?'✓ Electricity':'Electricity'} outline={kind!=='electricity'} onPress={()=>{setKind('electricity');setResult(null);}}/>
      <Field label="Reduction in usage (%)" value={reduction} onChangeText={setReduction} keyboardType="decimal-pad"/>
      <Btn title="Calculate scenario" onPress={run}/>
      {result?<View style={{gap:7}}><View style={S.divider}/><Label>Scenario result</Label>
          <Note>Baseline cost: {money(result.baseline)}</Note><Note>Adjusted cost: {money(result.adjusted)}</Note>
          <Note>Estimated money difference: {money(result.delta)}</Note>
          <Note>Illustrative unit change: {result.unit_change??'Unavailable'}</Note>
          <Text style={S.body}>{result.message}</Text>
          {result.assumptions.map((a,i)=><Note key={i}>• {a}</Note>)}
        </View>:null}
    </Card>
  </Page>;
}

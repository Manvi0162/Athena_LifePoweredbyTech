import React,{useEffect,useState} from 'react';
import {ActivityIndicator,Pressable,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {Forecast,UtilityKind} from '../../src/types';
import {money,S,C} from '../../src/theme';
import {ActionRow,Card,Label,Note,Page} from '../../src/ui';

export default function Utilities(){
  const {state,forecast}=useApp();
  const [data,setData]=useState<Partial<Record<UtilityKind,Forecast>>>({});
  const [loading,setLoading]=useState(true);

  useEffect(()=>{
    let active=true;
    Promise.all([forecast('water'),forecast('electricity')])
      .then(([water,electricity])=>{if(active)setData({water,electricity});})
      .catch(error=>{if(active)setData({});console.warn('Could not load utility forecasts',error);})
      .finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[forecast,state]);

  return <Page title="Your utilities" subtitle="Separate baselines for water and electricity." showSettings>
    <Card>
      <Label>Next billing cycle</Label>
      <Note>Forecasts use recorded bills where available. They are not live meter readings.</Note>
      {loading?<ActivityIndicator color={C.green}/>:null}
      {(['water','electricity'] as const).map(kind=>{
        const forecastData=data[kind];
        const isWater=kind==='water';
        return <Pressable key={kind} accessibilityRole="button"
          onPress={()=>router.push(isWater?'/water':'/electricity')}
          style={{padding:14,borderRadius:17,backgroundColor:isWater?C.softBlue:C.softAmber,gap:8}}>
          <View style={S.between}>
            <Text style={S.title}>{isWater?'◉  Water':'ϟ  Electricity'}</Text>
            <Text style={[S.muted,{color:C.green,fontWeight:'700'}]}>VIEW DETAILS  ›</Text>
          </View>
          <Text style={[S.amount,{color:C.ink,fontSize:23}]}>{forecastData?.value==null?'No forecast yet':money(forecastData.value)}</Text>
          <Note>{forecastData?`${forecastData.units} ${forecastData.unit} · ${forecastData.period_start} to ${forecastData.period_end}`:'Add a bill to start your baseline'}</Note>
        </Pressable>;
      })}
    </Card>

    <Card>
      <Label>Improve your baseline</Label>
      <ActionRow icon="＋" title="Add a water bill" subtitle="Record a verified billing period"
        onPress={()=>router.push({pathname:'/bill',params:{kind:'water'}})}/>
      <ActionRow icon="＋" title="Add an electricity bill" subtitle="Record a verified billing period"
        onPress={()=>router.push({pathname:'/bill',params:{kind:'electricity'}})}/>
      <Note>Bill photos are previewed locally. Enter and confirm the values printed on your bill.</Note>
    </Card>
    <Note>Tariff classes and future bill amounts are not verified by this demo. Avoid treating estimates as live meter data.</Note>
  </Page>;
}

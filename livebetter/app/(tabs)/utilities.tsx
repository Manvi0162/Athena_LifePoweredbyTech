import React,{useEffect,useState} from 'react';
import {t} from '../../src/i18n';
import {ActivityIndicator,Pressable,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {Forecast,UtilityKind} from '../../src/types';
import {money,S,C} from '../../src/theme';
import {ActionRow,Card,Label,Note,Page} from '../../src/ui';

export default function Utilities(){
  const {state,forecast,demo}=useApp();
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

  return <Page title={t('Your utilities')} subtitle={t('Separate baselines for water and electricity.')} showSettings>
    <Card>
      <Label>{t('Next billing cycle')}</Label>
      <Note>{t('Forecasts use recorded bills where available. They are not live meter readings.')}</Note>
      {loading?<ActivityIndicator color={C.green}/>:null}
      {(['water','electricity'] as const).map(kind=>{
        const forecastData=data[kind];
        const isWater=kind==='water';
        return <Pressable key={kind} accessibilityRole="button"
          onPress={()=>router.push(isWater?'/water':'/electricity')}
          style={{padding:14,borderRadius:17,backgroundColor:isWater?C.softBlue:C.softAmber,gap:8}}>
          <View style={S.between}>
            <Text style={S.title}>{isWater?'◉  Water':'ϟ  Electricity'}</Text>
            <Text style={[S.muted,{color:C.green,fontWeight:'700'}]}>{t('VIEW DETAILS  ›')}</Text>
          </View>
          <Text style={[S.amount,{color:C.ink,fontSize:23}]}>{forecastData?.value==null?t('No forecast yet'):money(forecastData.value)}</Text>
          <Note>{forecastData&&forecastData.value!=null?`${forecastData.units} ${forecastData.unit} · ${forecastData.period_start} to ${forecastData.period_end}`:
            (forecastData?.status_message||'Add a bill to start your baseline')}</Note>
        </Pressable>;
      })}
    </Card>

    <Card>
      <Label>{t('Improve your baseline')}</Label>
      <ActionRow icon="＋" title={t('Add a water bill')} subtitle={t('Photo or typed values from your CWA bill')}
        onPress={()=>router.push({pathname:'/bill',params:{kind:'water'}})}/>
      <ActionRow icon="＋" title={t('Add an electricity bill')} subtitle={t('Photo or typed values from your CEB bill')}
        onPress={()=>router.push({pathname:'/bill',params:{kind:'electricity'}})}/>
      <Note>{t('Upload a photo of the bill and the form is filled in for you to check.')}</Note>
    </Card>
    <Note>{demo?t('Tariff classes and future bill amounts are not verified by this demo. Avoid treating estimates as live meter data.'):
      'Costs are calculated with the official CWA and CEB tariffs. Estimates are not live meter data.'}</Note>
  </Page>;
}

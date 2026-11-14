import React from 'react';
import {t} from '../../src/i18n';
import {Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {Btn,Card,Label,Note,Page} from '../../src/ui';
import {S,C} from '../../src/theme';

export default function PantryUpdated(){
  const {state}=useApp();
  const lastCook=state.activity.find(item=>item.kind==='cook'||item.kind==='recipe');
  return <Page title={t('Pantry updated')} subtitle={t('Your meal is recorded and your remaining stock is up to date.')}>
    <View style={[S.card,{backgroundColor:C.softGreen,borderColor:C.softGreen,alignItems:'center',paddingVertical:24}]}>
      <Text style={{fontSize:32,color:C.green}}>✓</Text>
      <Text style={[S.title,{color:C.green}]}>{t('Inventory saved')}</Text>
      <Note>{lastCook?.message||'Your pantry inventory has been updated.'}</Note>
    </View>
    <Card>
      <Label>{t('Available now')}</Label>
      {state.pantry.filter(item=>item.available).slice(0,5).map(item=><View key={item.id} style={S.between}>
        <Text style={S.body}>{item.name}</Text><Text style={S.title}>{item.quantity} {item.unit}</Text>
      </View>)}
      <Note>{t('Cooking changes stock, not recorded purchase expenses.')}</Note>
    </Card>
    <Btn title={t('Find another recipe')} onPress={()=>router.replace('/(tabs)/pantry')}/>
    <Btn title={t('See activity log')} outline onPress={()=>router.push('/activity')}/>
  </Page>;
}

import React,{useEffect} from 'react';
import {t} from '../../src/i18n';
import {Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {money,S,C} from '../../src/theme';
import {Btn,Card,Label,Note,Page} from '../../src/ui';

export default function Stock(){
  const {state,demo,refreshPantry}=useApp();
  useEffect(()=>{if(!demo)refreshPantry().catch(()=>undefined);},[demo,refreshPantry]);
  const available=state.pantry.filter(p=>p.available&&p.quantity>0);
  const receipts=state.activity.filter(a=>a.event_type==='receipt_confirmed').slice(0,3);
  return <Page back title={t('Groceries and stock')} subtitle={t('Scan a receipt: what you bought is added to your pantry once.')}>
    <View style={[S.heroCard,{backgroundColor:'#1E6B5C'}]}>
      <Text style={S.heroEyebrow}>{t('YOUR PANTRY')}</Text>
      <Text style={{fontSize:28,fontWeight:'800',color:C.white}}>{available.length} items available</Text>
      <Text style={S.heroFootnote}>Cooking a recipe lowers the stock; it never adds a grocery expense.</Text>
    </View>
    <Card>
      <Label>{t('Add groceries')}</Label>
      <Note>Take or upload a photo of your receipt. AI reads the food items; you check them before saving.</Note>
      <Btn title={t('📷 Scan a receipt')} onPress={()=>router.push('/receipt')}/>
    </Card>
    <Card>
      <Label>{t('Your ingredients')}</Label>
      <Note>{t('See every ingredient and how much is left.')}</Note>
      <Btn title={t('View list of ingredients')} outline onPress={()=>router.push('/ingredients')}/>
    </Card>
    {receipts.length?<Card>
      <Label>{t('Latest receipts')}</Label>
      {receipts.map(r=><View key={r.id} style={[S.between,{paddingVertical:6,borderTopWidth:1,borderTopColor:C.line}]}>
        <Text style={[S.body,{flex:1}]}>{r.message}</Text><Note>{new Date(r.at).toLocaleDateString()}</Note></View>)}
    </Card>:null}
  </Page>;
}

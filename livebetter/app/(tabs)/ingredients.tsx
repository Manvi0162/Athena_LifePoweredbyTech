import React,{useEffect} from 'react';
import {t} from '../../src/i18n';
import {Text,View} from 'react-native';
import {useApp} from '../../src/context';
import {S,C} from '../../src/theme';
import {Card,Note,Page} from '../../src/ui';

const cap=(v:string)=>v.charAt(0).toUpperCase()+v.slice(1);
export default function Ingredients(){
  const {state,demo,refreshPantry}=useApp();
  useEffect(()=>{if(!demo)refreshPantry().catch(()=>undefined);},[demo,refreshPantry]);
  const rows=[...state.pantry].sort((a,b)=>Number(b.available&&b.quantity>0)-Number(a.available&&a.quantity>0)||a.name.localeCompare(b.name));
  const cell={paddingVertical:10,paddingHorizontal:10};
  return <Page back title={t('List of ingredients')} subtitle={`${rows.filter(r=>r.available&&r.quantity>0).length} available · ${rows.length} in total`}>
    <Card>
      <View style={{borderWidth:1,borderColor:C.line,borderRadius:14,overflow:'hidden'}}>
        <View style={{flexDirection:'row',backgroundColor:C.softBlue}}>
          <Text style={[S.muted,cell,{flex:2,fontWeight:'800'}]}>{t('INGREDIENT')}</Text>
          <Text style={[S.muted,cell,{flex:1.2,fontWeight:'800',textAlign:'right'}]}>{t('QUANTITY')}</Text>
          <Text style={[S.muted,cell,{flex:1.2,fontWeight:'800',textAlign:'right'}]}>{t('STATUS')}</Text>
        </View>
        {rows.map((r,i)=>{const ok=r.available&&r.quantity>0;
          return <View key={r.id} style={{flexDirection:'row',backgroundColor:i%2?C.bg:C.white,borderTopWidth:1,borderTopColor:C.line}}>
            <Text style={[S.body,cell,{flex:2}]}>{cap(r.name)}</Text>
            <Text style={[S.title,cell,{flex:1.2,textAlign:'right'}]}>{Number(r.quantity.toFixed(3))} {r.unit}</Text>
            <Text style={[S.muted,cell,{flex:1.2,textAlign:'right',fontWeight:'700',color:ok?C.green:C.muted}]}>{ok?t('Available'):t('Used up')}</Text>
          </View>;})}
        {!rows.length?<Text style={[S.muted,cell]}>{t('No ingredients yet. Scan a receipt to add them.')}</Text>:null}
      </View>
      <Note>Quantities change when you confirm a receipt (added) or cook a recipe (used).</Note>
    </Card>
  </Page>;
}

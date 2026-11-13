import React,{useCallback} from 'react';
import {Text} from 'react-native';
import {useFocusEffect} from 'expo-router';
import {useApp} from '../../src/context';
import {Card,Label,Note,Page} from '../../src/ui';
import {C,S} from '../../src/theme';
export default function Activity(){
  const {state,refreshAll}=useApp();
  useFocusEffect(useCallback(()=>{void refreshAll().catch(()=>undefined);},[]));   // security events appear at once
  return <Page back title="Household activity" subtitle="Bills, receipts, pantry and security events.">
  {state.activity.length?state.activity.map(item=>{
    const warn=/BLOCKED|Wrong|locked/i.test(item.message)&&item.kind==='security';
    return <Card key={item.id}><Label>{item.kind.toUpperCase()}</Label>
      <Text style={[S.body,warn&&{color:C.red,fontWeight:'700'}]}>{item.message}</Text><Note>{new Date(item.at).toLocaleString()}</Note></Card>;}):
    <Card><Note>No activity yet.</Note></Card>}
</Page>;}

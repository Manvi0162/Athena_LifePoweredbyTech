import React,{useEffect,useState} from 'react';
import {t} from '../../src/i18n';
import {Alert,Pressable,Text,View} from 'react-native';
import {router,useLocalSearchParams} from 'expo-router';
import {useApp} from '../../src/context';
import {Habits} from '../../src/types';
import {C,S} from '../../src/theme';
import {Btn,Card,Field,Label,Loading,Note,Page,readError} from '../../src/ui';

// Edit ONLY the water habits (W1-W5) or the electricity appliances and habits (E1-E5).
export default function HabitsEdit(){
  const {kind:raw}=useLocalSearchParams<{kind?:string}>();
  const kind=raw==='electricity'?'electricity':'water';
  const {habits,saveHabits,demo}=useApp();
  const [data,setData]=useState<Habits|null>(null);
  const [answers,setAnswers]=useState<Record<string,any>>({});
  useEffect(()=>{if(!demo)habits(kind).then(h=>{setData(h);setAnswers(h.answers||{});}).catch(e=>Alert.alert(t('Unavailable'),readError(e)));},[kind,habits,demo]);

  const set=(id:string,v:any)=>setAnswers(a=>({...a,[id]:v}));
  const toggle=(id:string,v:string)=>setAnswers(a=>{const cur:string[]=Array.isArray(a[id])?a[id]:[];
    return {...a,[id]:cur.includes(v)?cur.filter(x=>x!==v):[...cur,v]};});
  async function save(){
    try{await saveHabits(kind,answers);router.back();}
    catch(e){Alert.alert(t('Could not save'),readError(e));}
  }

  return <Page back title={kind==='water'?t('Water habits'):t('Appliances and habits')}
    subtitle={t('Optional. Answer what you know; skip the rest. Each answer makes your estimate more personal.')}>
    {demo?<Card><Note>Habit questions are saved by the backend (live mode).</Note></Card>:!data?<Loading/>:<>
      {data.questions.map((q,i)=><Card key={q.id}>
        <Text style={S.muted}>QUESTION {i+1}{q.multi?' · choose all that apply':''}</Text>
        <Label>{q.question}</Label>
        <View style={S.choiceRow}>{q.options.map(o=>{
          const on=q.multi?(Array.isArray(answers[q.id])&&answers[q.id].includes(o.value)):answers[q.id]===o.value;
          return <Pressable key={o.value} accessibilityRole="button" accessibilityState={{selected:on}}
            onPress={()=>q.multi?toggle(q.id,o.value):set(q.id,on?null:o.value)} style={[S.choice,on&&S.choiceSelected]}>
            <Text style={[S.choiceText,on&&S.choiceTextSelected]}>{o.label}</Text></Pressable>;})}
        </View>
        {q.extra&&['increase','decrease'].includes(String(answers[q.id]))?
          <Field label={q.extra.label} value={answers[q.extra.id]!=null?String(answers[q.extra.id]):''}
            onChangeText={v=>set(q.extra!.id,v.trim()===''?null:Number(v))} keyboardType="decimal-pad"/>:null}
      </Card>)}
      <Btn title={t('Save answers')} onPress={()=>void save()}/>
      <Note>{data.note}</Note>
    </>}
  </Page>;
}

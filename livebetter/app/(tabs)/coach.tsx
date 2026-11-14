// AI Coach: a conversation about changes at home and what they do to the bills (POST /household/coach).
// "Hello" gets a hello back; "I want to shower more" gets "How many minutes more?" (quick-reply chips); then the water
// and electricity engines calculate both bills with the official tariffs; "apply it" (or the button) adds the change to
// the plan, and the predicted bills on Home include it. The server returns `context` (its follow-up question, the last
// change) and the app sends it back with the next message: that is the conversation memory.
// Layout: header, conversation (scrolls), quick replies, composer. The composer rises with the keyboard.
import React,{useEffect,useRef,useState} from 'react';
import {t} from '../../src/i18n';
import {ActivityIndicator,Keyboard,KeyboardAvoidingView,Platform,Pressable,ScrollView,Text,TextInput,View} from 'react-native';
import {router} from 'expo-router';
import {SafeAreaView} from 'react-native-safe-area-context';
import {useApp} from '../../src/context';
import {CoachReply,Plan,QuickReply,WhatIfChange} from '../../src/types';
import {C,money,S} from '../../src/theme';
import {BottomNavigation} from '../../src/ui';

type Msg={role:'user'|'coach';text:string;reply?:CoachReply;question?:string;error?:boolean};
const WIDTH={width:'100%' as const,maxWidth:440,alignSelf:'center' as const};

export default function Coach(){
  const {ask,demo,applyPlan,plans,removePlan}=useApp();
  const [msgs,setMsgs]=useState<Msg[]>([{role:'coach',text:t("Hi! 👋 I'm your LiveBetter coach. Tell me about a change at home, like showering longer, using the AC less or having guests, and I'll show you what it does to your water and electricity bills.")}]);
  const [ctx,setCtx]=useState<Record<string,any>>({});      // conversation memory sent back to the server
  const [myPlan,setMyPlan]=useState<Plan[]>([]);
  const [showPlan,setShowPlan]=useState(false);
  const loadPlans=()=>{if(!demo)plans().then(setMyPlan).catch(()=>undefined);};
  useEffect(loadPlans,[demo]);
  const [draft,setDraft]=useState('');
  const [sending,setSending]=useState(false);
  const [kb,setKb]=useState(false);
  const scroll=useRef<any>(null);
  useEffect(()=>{
    const a=Keyboard.addListener(Platform.OS==='ios'?'keyboardWillShow':'keyboardDidShow',()=>setKb(true));
    const b=Keyboard.addListener(Platform.OS==='ios'?'keyboardWillHide':'keyboardDidHide',()=>setKb(false));
    return()=>{a.remove();b.remove();};
  },[]);
  useEffect(()=>{setTimeout(()=>scroll.current?.scrollToEnd({animated:true}),80);},[msgs,sending]);

  const oops=(e:unknown)=>`${t('Sorry, I could not answer that just now.')} ${e instanceof Error?e.message:String(e)}`;

  async function apply(i:number){
    const m=msgs[i];if(!m?.reply||sending)return;
    setSending(true);
    try{const r=await applyPlan(m.question||'',m.reply.plan);
      setMsgs(all=>all.map((x,j)=>j===i?{...x,reply:{...x.reply!,applied:r.applied,applied_message:r.applied_message}}:x));
      setCtx({});loadPlans();}
    catch(e){setMsgs(all=>[...all,{role:'coach',text:oops(e),error:true}]);}
    finally{setSending(false);}
  }

  // shown = what appears in the user's bubble (a quick-reply label); text = what is sent to the coach.
  async function send(q=draft,shown?:string){
    const text=q.trim();if(!text||sending)return;
    setDraft('');setSending(true);setMsgs(m=>[...m,{role:'user',text:shown||text}]);
    try{
      if(demo)throw Error(t('The coach needs the LiveBetter server. Run the app in live mode.'));
      const reply=await ask(text,ctx);
      setCtx(reply.context||{});
      setMsgs(m=>[...m,{role:'coach',text:reply.answer,reply,question:reply.context?.last_question||text}]);
      if(reply.applied)loadPlans();
    }catch(e){setMsgs(m=>[...m,{role:'coach',text:oops(e),error:true}]);}
    finally{setSending(false);}
  }
  async function remove(p:Plan){
    try{setMyPlan(await removePlan(p.id));}
    catch(e){setMsgs(m=>[...m,{role:'coach',text:oops(e),error:true}]);}
  }
  const last=msgs[msgs.length-1];
  const quick:QuickReply[]=!sending&&last?.role==='coach'?(last.reply?.quick_replies||[]):[];

  return <SafeAreaView style={{flex:1,backgroundColor:C.bg}} edges={['top','bottom']}>
    <KeyboardAvoidingView style={{flex:1}} behavior="padding" keyboardVerticalOffset={0}>
      <View style={[WIDTH,{paddingHorizontal:18,paddingTop:10,paddingBottom:8,gap:2}]}>
        <View style={S.between}>
          <View style={S.row}>
            <View style={{width:34,height:34,borderRadius:12,backgroundColor:C.green,alignItems:'center',justifyContent:'center'}}>
              <Text style={{color:C.white,fontSize:17,fontWeight:'900'}}>✦</Text></View>
            <View><Text style={[S.h2,{fontSize:20}]}>{t('What if…?')}</Text>
              <Text style={S.muted}>{t('See how a change affects your bills and budget')}</Text></View>
          </View>
          <Pressable accessibilityRole="button" accessibilityLabel="Open settings" onPress={()=>router.push('/settings')} style={S.topAction}>
            <Text style={S.topActionText}>⚙</Text></Pressable>
        </View>
      </View>

      <ScrollView ref={scroll} style={{flex:1}} contentContainerStyle={[WIDTH,{paddingHorizontal:18,paddingBottom:16,gap:12}]}
        keyboardShouldPersistTaps="handled" keyboardDismissMode="interactive">
        {myPlan.length?<Pressable accessibilityRole="button" onPress={()=>setShowPlan(v=>!v)}
          style={{backgroundColor:C.softGreen,borderRadius:16,padding:13,gap:6}}>
          <View style={S.between}><Text style={S.title}>Your plan · {myPlan.length} change{myPlan.length>1?'s':''}</Text>
            <Text style={{color:C.green,fontWeight:'800'}}>{(()=>{const v=myPlan.reduce((a,p)=>a+(p.total_delta_rs||0),0);return `${v<0?'−':'+'}${money(Math.abs(v))}`;})()} {showPlan?'▴':'▾'}</Text></View>
          {showPlan?myPlan.map(p=><View key={p.id} style={{borderTopWidth:1,borderTopColor:'#CDEBE2',paddingTop:6,flexDirection:'row',gap:8,alignItems:'center'}}>
            <View style={{flex:1,gap:2}}>
              <Text style={S.body}>{p.changes.map(c=>c.title).join(' + ')}</Text>
              <Text style={S.muted}>{p.changes.map(c=>`${t(c.module==='water'?'Water':'Electricity')} ${c.delta_rs<0?'−':'+'}${money(Math.abs(c.delta_rs))}`).join(' · ')}</Text>
            </View>
            <Pressable accessibilityRole="button" accessibilityLabel={t('Remove from my plan')} onPress={()=>void remove(p)}
              style={{width:32,height:32,borderRadius:16,backgroundColor:'#FDECEC',alignItems:'center',justifyContent:'center'}}>
              <Text style={{color:C.red,fontWeight:'900'}}>✕</Text></Pressable>
          </View>):<Text style={S.muted}>{t('Included in your predicted bills on Home. Tap to see or remove.')}</Text>}
        </Pressable>:null}
        {msgs.map((m,i)=>m.role==='user'?
          <View key={i} style={{alignSelf:'flex-end',maxWidth:'85%',backgroundColor:C.green,borderRadius:18,borderBottomRightRadius:5,
            paddingHorizontal:14,paddingVertical:10}}><Text style={{color:C.white,fontSize:14,lineHeight:20}}>{m.text}</Text></View>:
          <CoachAnswer key={i} msg={m} onApply={()=>void apply(i)} busy={sending}/>)}
        {sending?<View style={[S.row,{alignSelf:'flex-start',backgroundColor:C.white,borderRadius:16,padding:12}]}>
          <ActivityIndicator color={C.green}/><Text style={S.muted}>{t('Thinking…')}</Text></View>:null}
        {quick.length?<View style={{flexDirection:'row',flexWrap:'wrap',gap:8}}>
          {quick.map(q=><Pressable key={q.value} accessibilityRole="button" onPress={()=>void send(q.value,t(q.label))}
            style={{borderWidth:1.5,borderColor:C.green,borderRadius:18,paddingHorizontal:14,paddingVertical:8,backgroundColor:C.white}}>
            <Text style={{color:C.green,fontWeight:'800'}}>{t(q.label)}</Text></Pressable>)}
        </View>:null}
      </ScrollView>

      <View style={{backgroundColor:C.white,borderTopWidth:1,borderTopColor:C.line}}>
        <View style={[WIDTH,{flexDirection:'row',alignItems:'flex-end',gap:8,paddingHorizontal:14,paddingVertical:10}]}>
          <TextInput value={draft} onChangeText={setDraft} placeholder={t('Type a message…')} placeholderTextColor={C.muted}
            multiline style={[S.chatInput,{maxHeight:110}]} onSubmitEditing={()=>void send()} blurOnSubmit returnKeyType="send"
            accessibilityLabel="Message the coach"/>
          <Pressable accessibilityRole="button" accessibilityLabel="Send" disabled={sending||!draft.trim()} onPress={()=>void send()}
            style={{width:44,height:44,borderRadius:14,backgroundColor:C.green,alignItems:'center',justifyContent:'center',
              opacity:sending||!draft.trim()?0.45:1}}><Text style={{color:C.white,fontWeight:'900',fontSize:18}}>↑</Text></Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
    {kb?null:<BottomNavigation/>}
  </SafeAreaView>;
}

function CoachAnswer({msg,onApply,busy}:{msg:Msg;onApply:()=>void;busy:boolean}){
  const r=msg.reply;
  const ok=(r?.changes||[]).filter(c=>c.status==='ok');
  if(!r||r.intent!=='what_if'||!r.changes?.length)return <View style={{alignSelf:'flex-start',maxWidth:'88%',
    backgroundColor:msg.error?'#FDECEC':C.white,borderRadius:18,borderBottomLeftRadius:5,paddingHorizontal:14,paddingVertical:11,
    borderWidth:1,borderColor:msg.error?'#F5C9C9':C.line}}>
    <Text style={[S.body,{lineHeight:21},msg.error&&{color:C.red}]}>{r?.applied&&r.applied_message?`✓ ${r.applied_message}`:msg.text}</Text></View>;
  return <View style={{alignSelf:'stretch',backgroundColor:C.white,borderRadius:18,borderBottomLeftRadius:5,padding:14,gap:10,
    borderWidth:1,borderColor:C.line}}>
    {r.changes.map((c,i)=><ChangeCard key={i} c={c}/>)}
    {ok.length>1?<View style={[S.between,{backgroundColor:C.bg,borderRadius:12,padding:11}]}>
      <Text style={S.title}>{t('Together')}</Text><Delta v={r.budget?.total_delta_rs||0}/></View>:null}
    {(r.budget?.lines||[]).map(b=>{
      const pct=Math.min(1.2,b.after_rs/Math.max(1,b.budget_rs));
      return <View key={b.module} style={{gap:5}}>
        <View style={S.between}><Text style={S.title}>{t(b.module==='water'?'Water budget':'Electricity budget')}</Text>
          <Text style={[S.muted,{fontWeight:'700',color:b.within_after?C.green:C.red}]}>
            {b.within_after?t('Within budget'):`${money(b.after_rs-b.budget_rs)} ${t('over')}`}</Text></View>
        <View style={{height:8,borderRadius:8,backgroundColor:C.line,overflow:'hidden'}}>
          <View style={{width:`${Math.min(100,pct*100)}%`,height:'100%',backgroundColor:b.within_after?C.green:C.red}}/></View>
        <Text style={S.muted}>{money(b.after_rs)} of {money(b.budget_rs)}{b.within_before!==b.within_after?
          (b.within_after?' · this change brings you back within budget':' · this change takes you over budget'):''}</Text>
      </View>;
    })}
    {r.suggestion?<View style={{backgroundColor:C.softAmber,borderRadius:12,padding:11,gap:3}}>
      <Text style={[S.title,{fontSize:13}]}>{t('✦ Suggestion')}</Text><Text style={S.body}>{((x:string)=>x.charAt(0).toUpperCase()+x.slice(1))(r.suggestion.replace(/^My suggestion: /,''))}</Text></View>:null}
    {r.applied?<View style={{backgroundColor:C.softGreen,borderRadius:12,padding:11}}>
      <Text style={[S.body,{color:C.green,fontWeight:'700'}]}>✓ {r.applied_message}</Text></View>:
      r.can_apply?<Pressable accessibilityRole="button" disabled={busy} onPress={onApply}
        style={{backgroundColor:C.green,borderRadius:12,paddingVertical:11,alignItems:'center',opacity:busy?0.5:1}}>
        <Text style={{color:C.white,fontWeight:'800'}}>{t('Apply to my plan')}</Text></Pressable>:null}
    {!r.budget?.lines?.length&&ok.length?<Text style={S.muted}>{t('Set a water or electricity budget in your household details to see the effect on it.')}</Text>:null}
    <Text style={[S.muted,{fontSize:11}]}>{r.source==='gemini'?t('Worded by AI · numbers '):t('Numbers ')}calculated with the official CWA and CEB tariffs from your bills. Estimates, not measured savings.</Text>
  </View>;
}

const niceDate=(d?:string)=>{if(!d)return '';const x=new Date(`${d}T00:00:00`);
  return isNaN(x.getTime())?d:x.toLocaleDateString(undefined,{day:'numeric',month:'short'});};

function ChangeCard({c}:{c:WhatIfChange}){
  const [how,setHow]=useState(false);
  if(c.status!=='ok')return <View style={{gap:3}}><Text style={S.title}>{c.title}</Text><Text style={S.muted}>{c.message}</Text></View>;
  return <View style={{gap:6}}>
    <View style={S.between}>
      <View style={[S.row,{flex:1,gap:8}]}>
        <View style={{width:28,height:28,borderRadius:9,backgroundColor:c.module==='water'?C.softBlue:C.softElectric,
          alignItems:'center',justifyContent:'center'}}><Text>{c.module==='water'?'◉':'ϟ'}</Text></View>
        <View style={{flex:1}}><Text style={S.title}>{c.title}</Text><Text style={S.muted}>{c.when}</Text></View>
      </View>
      <Delta v={c.delta_rs||0}/>
    </View>
    <View style={{flexDirection:'row',alignItems:'center',gap:8,backgroundColor:C.bg,borderRadius:12,padding:10}}>
      <View style={{flex:1}}><Text style={S.muted}>{t('Next bill now')}</Text><Text style={S.title}>{money(c.before_rs)}</Text></View>
      <Text style={{color:C.muted,fontSize:18}}>→</Text>
      <View style={{flex:1}}><Text style={S.muted}>{t('With the change')}</Text><Text style={S.title}>{money(c.after_rs)}</Text></View>
    </View>
    <Text style={S.muted}>{Math.abs(c.unit_change||0).toLocaleString()} {c.unit} {(c.unit_change||0)<0?t('less'):t('more')} · {t('bill of')} {niceDate(c.period_start)} → {niceDate(c.period_end)}</Text>
    {c.how?<Pressable accessibilityRole="button" onPress={()=>setHow(v=>!v)}>
      <Text style={[S.muted,{color:C.green,fontWeight:'700'}]}>{how?`▴ ${c.how}`:t('▾ How is this calculated?')}</Text></Pressable>:null}
    {c.note?<Text style={[S.muted,{color:'#8A5A00'}]}>{c.note}</Text>:null}
  </View>;
}

function Delta({v}:{v:number}){
  const save=v<0;
  return <View style={{backgroundColor:v===0?C.bg:save?C.softGreen:'#FDECEC',borderRadius:10,paddingHorizontal:9,paddingVertical:5}}>
    <Text style={{fontWeight:'800',color:v===0?C.muted:save?C.green:C.red}}>{v===0?t('Rs 0'):`${save?'−':'+'}${money(Math.abs(v))}`}</Text></View>;
}

import React,{useEffect,useState} from 'react';
import {ActivityIndicator,Pressable,ScrollView,Text,TextInput,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {Insight} from '../../src/types';
import {money,S,C} from '../../src/theme';
import {Card,Label,Note,Page} from '../../src/ui';

type Message={role:'assistant'|'user';text:string};
const suggestions=['How can I spend less?','What can I cook?','Why this forecast?','Try a water scenario'];

export default function Coach(){
  const {state,insights,scenario}=useApp();
  const [data,setData]=useState<Insight|null>(null);
  const [loading,setLoading]=useState(true);
  const [sending,setSending]=useState(false);
  const [draft,setDraft]=useState('');
  const [messages,setMessages]=useState<Message[]>([{
    role:'assistant',
    text:'Hi! I can help you understand your household baseline, find something to cook from your pantry, or explore a water-use scenario.',
  }]);

  useEffect(()=>{
    let active=true;
    insights().then(value=>{if(active)setData(value);})
      .catch(error=>{console.warn('Could not load household insights',error);})
      .finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[insights,state]);

  async function answer(question:string){
    const text=question.toLowerCase();
    if(text.includes('cook')||text.includes('pantry')||text.includes('meal')){
      const available=state.pantry.filter(item=>item.available&&item.quantity>0);
      const ingredients=available.slice(0,4).map(item=>item.name).join(', ');
      return ingredients
        ?`You currently have ${ingredients}${available.length>4?' and more':''}. Open your pantry to see recipe matches.`
        :'Your pantry has no available stock yet. Add ingredients or confirm a grocery receipt to get started.';
    }
    if(text.includes('scenario')||text.includes('water')){
      const result=await scenario('water',10);
      return `A 10% water-use reduction scenario: ${result.message} Baseline ${money(result.baseline)}; adjusted estimate ${money(result.adjusted)}. This is illustrative, not a verified tariff quote.`;
    }
    if(text.includes('why')||text.includes('forecast')||text.includes('evidence')){
      return data
        ?`The utility estimates use ${data.method}. They cover ${data.period_start} to ${data.period_end}. ${data.assumptions.slice(0,2).join(' ')}`
        :'There is not enough household bill history to explain a forecast yet. Add a verified utility bill to start a baseline.';
    }
    if(text.includes('spend')||text.includes('budget')||text.includes('save')){
      const recommendations=data?.recommendations.slice(0,2).join(' ')||'Add utility bills and confirm grocery receipts to build a useful baseline.';
      return `Your next-cycle utility estimates are Water: ${money(data?.water)} and Electricity: ${money(data?.electricity)}. Confirmed groceries (${money(data?.groceries_recorded)}) are recorded purchases, not a future monthly forecast. ${recommendations}`;
    }
    return 'I can help with household spending, pantry ingredients, utility forecasts and water-use scenarios. Try one of the suggested questions below.';
  }

  async function send(question=draft){
    const prompt=question.trim();
    if(!prompt||sending)return;
    setDraft('');
    setSending(true);
    setMessages(current=>[...current,{role:'user',text:prompt}]);
    try{
      const reply=await answer(prompt);
      setMessages(current=>[...current,{role:'assistant',text:reply}]);
    }catch(error){
      console.warn('Could not prepare coach response',error);
      setMessages(current=>[...current,{role:'assistant',text:'I could not load that household information. Please try again or open the related page directly.'}]);
    }finally{setSending(false);}
  }

  return <Page title="LiveBetter AI Coach" subtitle="Practical help for your household." showSettings
    stickyFooter={<View style={S.chatComposer}>
      <TextInput value={draft} onChangeText={setDraft} style={S.chatInput}
        placeholder="Ask a follow-up…" placeholderTextColor={C.muted} returnKeyType="send"
        onSubmitEditing={()=>void send()} accessibilityLabel="Ask a follow-up"/>
      <Pressable accessibilityRole="button" accessibilityLabel="Send message" disabled={sending||!draft.trim()}
        onPress={()=>void send()} style={[S.actionIcon,{backgroundColor:C.green,opacity:sending||!draft.trim()?0.5:1}]}>
        <Text style={{color:C.white,fontWeight:'800'}}>→</Text>
      </Pressable>
    </View>}>
    <View style={[S.card,{backgroundColor:C.softGreen,borderColor:C.softGreen}]}>
      <View style={S.between}><Label>Evidence-led guidance</Label><Text style={[S.statLabel,{color:C.green}]}>PREVIEW</Text></View>
      <Note>Replies use available household records and deterministic guidance. A generative chat service is not connected in this build.</Note>
    </View>

    <Card>
      <View style={S.between}><Label>Conversation</Label>{loading?<ActivityIndicator color={C.green}/>:null}</View>
      {messages.map((message,index)=><View key={`${index}-${message.role}`} style={{
        alignItems:message.role==='user'?'flex-end':'flex-start',
      }}>
        <View style={[S.chatBubble,{backgroundColor:message.role==='user'?C.mint:C.bg,
          borderBottomRightRadius:message.role==='user'?5:17,borderBottomLeftRadius:message.role==='assistant'?5:17}]}>
          <Text style={S.chatBubbleText}>{message.text}</Text>
        </View>
      </View>)}
      {sending?<Text style={S.muted}>Checking household information…</Text>:null}
    </Card>

    <View style={{gap:8}}>
      <Label>Try asking</Label>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{gap:8,paddingRight:12}}>
        {suggestions.map(question=><Pressable key={question} accessibilityRole="button"
          disabled={sending} onPress={()=>void send(question)} style={S.choice}>
          <Text style={S.choiceText}>{question}</Text>
        </Pressable>)}
      </ScrollView>
    </View>

    <Card>
      <Label>Open a detailed view</Label>
      <Pressable accessibilityRole="button" onPress={()=>router.navigate('/(tabs)/utilities')} style={S.actionRow}>
        <Text style={S.body}>Utility forecasts</Text><Text style={S.actionArrow}>›</Text>
      </Pressable>
      <Pressable accessibilityRole="button" onPress={()=>router.navigate('/(tabs)/pantry')} style={S.actionRow}>
        <Text style={S.body}>Pantry and recipes</Text><Text style={S.actionArrow}>›</Text>
      </Pressable>
      <Pressable accessibilityRole="button" onPress={()=>router.push('/activity')} style={S.actionRow}>
        <Text style={S.body}>Evidence and activity</Text><Text style={S.actionArrow}>›</Text>
      </Pressable>
    </Card>
  </Page>;
}

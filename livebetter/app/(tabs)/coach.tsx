import React,{useEffect,useState} from 'react';
import {ActivityIndicator,Pressable,ScrollView,Text,TextInput,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {Insight} from '../../src/types';
import {money,S,C} from '../../src/theme';
import {Btn,Card,Label,Page} from '../../src/ui';

type CoachAction={label:string;href:'/pantry'|'/utilities'|'/activity'};
type CoachReply={text:string;action?:CoachAction};
type Message={role:'assistant'|'user';text:string;action?:CoachAction};
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

  async function answer(question:string):Promise<CoachReply>{
    const text=question.toLowerCase();
    if(text.includes('cook')||text.includes('pantry')||text.includes('meal')){
      const available=state.pantry.filter(item=>item.available&&item.quantity>0);
      const ingredients=available.slice(0,4).map(item=>item.name).join(', ');
      return ingredients
        ?{text:`You currently have ${ingredients}${available.length>4?' and more':''}. Open your pantry to see recipe matches.`,action:{label:'Check pantry & recipes',href:'/pantry'}}
        :{text:'Your pantry has no available stock yet. Add ingredients or confirm a grocery receipt to get started.',action:{label:'Open pantry',href:'/pantry'}};
    }
    if(text.includes('scenario')||text.includes('water')){
      const result=await scenario('water',10);
      return {text:`A 10% water-use reduction scenario: ${result.message} Baseline ${money(result.baseline)}; adjusted estimate ${money(result.adjusted)}. This is illustrative, not a verified tariff quote.`,action:{label:'View utility insights',href:'/utilities'}};
    }
    if(text.includes('why')||text.includes('forecast')||text.includes('evidence')){
      return data
        ?{text:`The utility estimates use ${data.method}. They cover ${data.period_start} to ${data.period_end}. ${data.assumptions.slice(0,2).join(' ')}`,action:{label:'View utility insights',href:'/utilities'}}
        :{text:'There is not enough household bill history to explain a forecast yet. Add a verified utility bill to start a baseline.',action:{label:'Open utilities',href:'/utilities'}};
    }
    if(text.includes('spend')||text.includes('budget')||text.includes('save')){
      const recommendations=data?.recommendations.slice(0,2).join(' ')||'Add utility bills and confirm grocery receipts to build a useful baseline.';
      return {text:`Your next-cycle utility estimates are Water: ${money(data?.water)} and Electricity: ${money(data?.electricity)}. Confirmed groceries (${money(data?.groceries_recorded)}) are recorded purchases, not a future monthly forecast. ${recommendations}`,action:{label:'View utility insights',href:'/utilities'}};
    }
    return {text:'I can help with household spending, pantry ingredients, utility forecasts and water-use scenarios. Try one of the suggested questions below.'};
  }

  async function send(question=draft){
    const prompt=question.trim();
    if(!prompt||sending)return;
    setDraft('');
    setSending(true);
    setMessages(current=>[...current,{role:'user',text:prompt}]);
    try{
      const reply=await answer(prompt);
      setMessages(current=>[...current,{role:'assistant',...reply}]);
    }catch(error){
      console.warn('Could not prepare coach response',error);
      setMessages(current=>[...current,{role:'assistant',text:'I could not load that household information. Please try again or open the related page directly.',action:{label:'Open utilities',href:'/utilities'}}]);
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
    <Card>
      <View style={S.between}><Label>Conversation</Label>{loading?<ActivityIndicator color={C.green}/>:null}</View>
      {messages.map((message,index)=>{
        const action=message.action;
        return <View key={`${index}-${message.role}`} style={{
          alignItems:message.role==='user'?'flex-end':'flex-start',
        }}>
          <View style={[S.chatBubble,{backgroundColor:message.role==='user'?C.mint:C.bg,
            borderBottomRightRadius:message.role==='user'?5:17,borderBottomLeftRadius:message.role==='assistant'?5:17}]}>
            <Text style={S.chatBubbleText}>{message.text}</Text>
          </View>
          {action?<View style={{width:'88%',marginTop:7}}>
            <Btn title={action.label} outline onPress={()=>router.navigate(action.href)}/>
          </View>:null}
        </View>;
      })}
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

  </Page>;
}

// Security settings (surprise card "Misuse").
// Opened after registration (?setup=1) and from Settings. Pattern: required for protected actions.
// Microsoft Authenticator: optional, the user decides here and can switch it on or off later.
import React,{useCallback,useEffect,useState} from 'react';
import {Image,Text,View} from 'react-native';
import {router,useLocalSearchParams} from 'expo-router';
import {useApp} from '../src/context';
import {PatternGrid,usePattern} from '../src/pattern';
import {AuthenticatorSetup,SecurityStatus} from '../src/types';
import {C,S} from '../src/theme';
import {Btn,Card,Field,Label,Note,Page,readError} from '../src/ui';

export default function Security(){
  const {setup}=useLocalSearchParams<{setup?:string}>();
  const firstRun=setup==='1';
  const app=useApp();
  const guard=usePattern();
  const [st,setSt]=useState<SecurityStatus|null>(null);
  const [msg,setMsg]=useState<{text:string;bad?:boolean}|null>(null);
  // pattern
  const [stage,setStage]=useState<'idle'|'draw'|'confirm'|'proof'>('idle');
  const [first,setFirst]=useState<number[]>([]);const [dots,setDots]=useState<number[]>([]);
  const [password,setPassword]=useState('');
  // authenticator
  const [offer,setOffer]=useState<'ask'|'setup'|'codes'|'declined'>('ask');
  const [qr,setQr]=useState<AuthenticatorSetup|null>(null);const [code,setCode]=useState('');
  const [codes,setCodes]=useState<string[]>([]);
  const [offCode,setOffCode]=useState('');

  const load=useCallback(async()=>{
    try{const s=await app.securityStatus();setSt(s);if(firstRun&&!s.pattern_set)setStage(x=>x==='idle'?'draw':x);}
    catch(e){setMsg({text:readError(e),bad:true});}
  },[app.securityStatus,firstRun]);
  useEffect(()=>{void load();},[load]);

  function nextDraw(){
    if(dots.length<4)return setMsg({text:'Connect at least 4 dots.',bad:true});
    if(stage==='draw'){setFirst(dots);setDots([]);setStage('confirm');setMsg({text:'Draw the same pattern again to confirm.'});return;}
    if(dots.join()!==first.join()){setDots([]);setFirst([]);setStage('draw');return setMsg({text:'The two patterns were different. Start again.',bad:true});}
    setStage('proof');setMsg(null);
  }
  async function savePattern(){
    try{
      const proof=st?.authenticator_on?(code.includes('-')?{recovery_code:code}:{code}):{password};
      setSt(await app.setPattern(first,proof));
      setStage('idle');setFirst([]);setDots([]);setPassword('');setCode('');
      setMsg({text:'Security pattern saved. Protected actions now need it.'});
    }catch(e){setMsg({text:readError(e),bad:true});}
  }
  async function startAuthenticator(){
    try{setQr(await app.authenticatorSetup());setOffer('setup');setMsg(null);}catch(e){setMsg({text:readError(e),bad:true});}
  }
  async function confirmAuthenticator(){
    try{setCodes(await app.authenticatorConfirm(code));setCode('');setQr(null);setOffer('codes');await load();
      setMsg({text:'Microsoft Authenticator is on. Logging in now needs a code.'});}
    catch(e){setMsg({text:readError(e),bad:true});}
  }
  function turnOff(){
    if(!offCode.trim())return setMsg({text:'Enter a code from Microsoft Authenticator (or a recovery code).',bad:true});
    guard.ask('security_off',async stepUp=>{
      try{const proof=offCode.includes('-')?{recovery_code:offCode.trim()}:{code:offCode.trim()};
        setSt(await app.authenticatorDisable(proof,stepUp));setOffCode('');setMsg({text:'Microsoft Authenticator is off.'});}
      catch(e){setMsg({text:readError(e),bad:true});}
    });
  }

  if(app.demo)return <Page back title="Security" showTabs={false}>
    <Card><Note>Security (pattern, Microsoft Authenticator, protected reset) is checked by the LiveBetter backend.
      Run the app with EXPO_PUBLIC_USE_MOCKS=false to use it.</Note></Card></Page>;

  return <Page back={!firstRun} showTabs={false} title={firstRun?'Protect your household':'Security'}
    subtitle="Someone else using this phone (a child, a housemate) should not be able to wipe your records or switch security off.">
    {guard.prompt}
    {st?.alert?<View style={[S.card,{backgroundColor:C.dangerBg}]}>
      <Text style={[S.title,{color:C.red}]}>⚠ {st.alert.message}</Text>
    </View>:null}
    {msg?<Text accessibilityLiveRegion="polite" style={msg.bad?S.error:[S.card,{color:C.green,fontWeight:'700'}]}>{msg.text}</Text>:null}

    <Card>
      <View style={S.between}><Label>1 · Security pattern</Label>
        <Text style={{color:st?.pattern_set?C.green:C.red,fontWeight:'800'}}>{st?.pattern_set?'SET':'NOT SET'}</Text></View>
      <Note>Needed to: reset the account, restore after a reset, delete a bill, change household details and switch security off.
        After 5 wrong tries it locks for 5 minutes, and you see every attempt here and in Activity.</Note>
      {stage==='idle'?<Btn title={st?.pattern_set?'Change pattern':'Set pattern'} outline={!!st?.pattern_set}
        onPress={()=>{setStage('draw');setDots([]);setMsg(null);}}/>:null}
      {stage==='draw'||stage==='confirm'?<>
        <Text style={S.title}>{stage==='draw'?'Draw a new pattern (at least 4 dots)':'Draw it again to confirm'}</Text>
        <PatternGrid value={dots} onChange={setDots}/>
        <View style={S.row}>
          <View style={{flex:1}}><Btn title="Clear" outline onPress={()=>setDots([])}/></View>
          <View style={{flex:1}}><Btn title={stage==='draw'?'Next':'Confirm pattern'} onPress={nextDraw}/></View>
        </View>
      </>:null}
      {stage==='proof'?<>
        {st?.authenticator_on
          ?<Field label="Code from Microsoft Authenticator (or a recovery code)" value={code} onChangeText={setCode} keyboardType="default"/>
          :<Field label="Your account password (proves it is you)" value={password} onChangeText={setPassword} secureTextEntry/>}
        <Btn title="Save pattern" onPress={()=>void savePattern()}/>
      </>:null}
    </Card>

    <Card>
      <View style={S.between}><Label>2 · Microsoft Authenticator (optional)</Label>
        <Text style={{color:st?.authenticator_on?C.green:C.muted,fontWeight:'800'}}>{st?.authenticator_on?'ON':'OFF'}</Text></View>
      {!st?.authenticator_on&&offer==='ask'?<>
        <Note>Do you want to add Microsoft Authenticator? Then logging in needs your password AND a 6-digit code from your phone.
          It is optional: you can switch it on or off later in Settings → Security. Google Authenticator works too.</Note>
        <View style={S.row}>
          <View style={{flex:1}}><Btn title="Yes, set it up" onPress={()=>void startAuthenticator()}/></View>
          <View style={{flex:1}}><Btn title="Not now" outline onPress={()=>setOffer('declined')}/></View>
        </View>
      </>:null}
      {!st?.authenticator_on&&offer==='declined'?<>
        <Note>Not switched on. You can add it any time here.</Note>
        <Btn title="Set up Microsoft Authenticator" outline onPress={()=>void startAuthenticator()}/>
      </>:null}
      {offer==='setup'&&qr?<>
        <Note>1. In Microsoft Authenticator tap + → Other account → scan this code.</Note>
        <Image source={{uri:qr.qr_png}} style={{width:200,height:200,alignSelf:'center'}} accessibilityLabel="Authenticator QR code"/>
        <Note>Can't scan? Enter this key: </Note>
        <Text selectable style={[S.title,{letterSpacing:1}]}>{qr.manual_key.match(/.{1,4}/g)?.join(' ')}</Text>
        <Note>2. Type the 6-digit code it shows. This key is shown only now.</Note>
        <Field label="6-digit code" value={code} onChangeText={setCode} keyboardType="number-pad"/>
        <Btn title="Switch on" onPress={()=>void confirmAuthenticator()}/>
      </>:null}
      {offer==='codes'&&codes.length?<View style={{gap:6,backgroundColor:C.amber,borderRadius:14,padding:13}}>
        <Text style={S.title}>Your 8 recovery codes (shown once)</Text>
        <Note>If you lose your phone, each code logs you in once. Write them down and keep them away from the phone.</Note>
        <Text selectable style={[S.body,{fontFamily:'monospace'}]}>{codes.join('   ')}</Text>
        <Btn title="I saved them" onPress={()=>{setCodes([]);setOffer('ask');}}/>
      </View>:null}
      {st?.authenticator_on&&offer!=='codes'?<>
        <Note>Logging in needs a code. {st.recovery_codes_left} recovery codes left.</Note>
        <Note>Switching it off needs BOTH your pattern and a current code, so someone with only the phone cannot do it.</Note>
        <Field label="Code (or recovery code) to switch off" value={offCode} onChangeText={setOffCode}/>
        <Btn title="Switch off Microsoft Authenticator" outline onPress={turnOff}/>
      </>:null}
    </Card>

    {!firstRun&&st?.recent_events.length?<Card>
      <Label>Recent security events</Label>
      {st.recent_events.slice(0,8).map((e,i)=><View key={i} style={{paddingVertical:6,borderTopWidth:i?1:0,borderTopColor:C.line}}>
        <Text style={[S.body,{color:e.event==='blocked'||e.event.endsWith('_failed')||e.event.endsWith('_locked')?C.red:C.ink}]}>
          {e.event.replace(/_/g,' ')}{e.action?` · ${st.protected_actions[e.action as keyof typeof st.protected_actions]||e.action}`:''}</Text>
        <Note>{new Date(e.at).toLocaleString()}</Note>
      </View>)}
    </Card>:null}

    {firstRun?<Card>
      <Btn title="Continue to household setup  →" disabled={!st?.pattern_set} onPress={()=>router.replace('/onboarding')}/>
      {!st?.pattern_set?<Note>Set your pattern first. The authenticator is optional.</Note>:null}
    </Card>:null}
  </Page>;
}

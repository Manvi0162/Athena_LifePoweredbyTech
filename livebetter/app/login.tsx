import React,{useState} from 'react';
import {Alert,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../src/context';
import {Btn,Card,Field,Label,Note,Page,readError} from '../src/ui';
import {S} from '../src/theme';

export default function Login(){
  const {login,loginCode,demo}=useApp();
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  const [mfa,setMfa]=useState<{token:string;message:string}|null>(null);
  const [code,setCode]=useState('');
  const [recovery,setRecovery]=useState(false);
  const go=(household:boolean)=>router.replace(household?'/(tabs)/home':'/onboarding');

  async function submit(){
    if(!email.trim()||!password)return Alert.alert('Missing details','Enter your email and password.');
    try{
      const r=await login(email.trim(),password);
      if(r.mfa){setMfa(r.mfa);setPassword('');return;}
      go(r.household);
    }catch(error){Alert.alert('Could not log in',readError(error));}
  }
  async function submitCode(){
    if(!mfa||!code.trim())return;
    try{go((await loginCode(mfa.token,code,recovery)).household);}
    catch(error){setCode('');Alert.alert('Code not accepted',readError(error));}
  }

  return <Page showTabs={false} title="Log in" subtitle="Sign in to continue to your household.">
    {!mfa?<Card>
      <Label>Your account</Label>
      <Field label="Email address" value={email} onChangeText={setEmail}
        placeholder="you@example.com" keyboardType="email-address"/>
      <Field label="Password" value={password} onChangeText={setPassword}
        secureTextEntry placeholder="Enter your password"/>
      <Btn title="Log in" onPress={()=>void submit()}/>
      {demo?<Note>Demo mode: any details open the sample app.</Note>:null}
    </Card>:<Card>
      <Label>Microsoft Authenticator</Label>
      <Note>{recovery?'Enter one of your recovery codes (each works once).':mfa.message}</Note>
      <Field label={recovery?'Recovery code':'6-digit code'} value={code} onChangeText={setCode}
        keyboardType={recovery?'default':'number-pad'} placeholder={recovery?'xxxx-xxxx':'123456'}/>
      <Btn title="Verify" onPress={()=>void submitCode()}/>
      <Btn title={recovery?'Use the authenticator code':'Lost your phone? Use a recovery code'} outline
        onPress={()=>{setRecovery(!recovery);setCode('');}}/>
      <Btn title="Back" outline onPress={()=>{setMfa(null);setCode('');}}/>
    </Card>}
    <View style={[S.card,{alignItems:'center'}]}>
      <Text style={S.muted}>New to LiveBetter?</Text>
      <Btn title="Register" outline onPress={()=>router.push('/register')}/>
    </View>
  </Page>;
}

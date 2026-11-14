import React,{useState} from 'react';
import {t} from '../src/i18n';
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
  const {securityStatus}=useApp();
  // First login after confirming the email (Supabase): the security pattern is set before anything else.
  const go=async(household:boolean)=>{
    let needsPattern=false;
    if(!demo){try{needsPattern=!(await securityStatus()).pattern_set;}catch{}}
    if(needsPattern)router.replace({pathname:'/security',params:{setup:'1'}});
    else router.replace(household?'/(tabs)/home':'/onboarding');
  };

  async function submit(){
    if(!email.trim()||!password)return Alert.alert(t('Missing details'),t('Enter your email and password.'));
    try{
      const r=await login(email.trim(),password);
      if(r.mfa){setMfa(r.mfa);setPassword('');return;}
      await go(r.household);
    }catch(error){Alert.alert(t('Could not log in'),readError(error));}
  }
  async function submitCode(){
    if(!mfa||!code.trim())return;
    try{await go((await loginCode(mfa.token,code,recovery)).household);}
    catch(error){setCode('');Alert.alert(t('Code not accepted'),readError(error));}
  }

  return <Page showTabs={false} title={t('Log in')} subtitle={t('Sign in to continue to your household.')}>
    {!mfa?<Card>
      <Label>{t('Your account')}</Label>
      <Field label={t('Email address')} value={email} onChangeText={setEmail}
        placeholder={t('you@example.com')} keyboardType="email-address"/>
      <Field label={t('Password')} value={password} onChangeText={setPassword}
        secureTextEntry placeholder={t('Enter your password')}/>
      <Btn title={t('Log in')} onPress={()=>void submit()}/>
      {demo?<Note>{t('Demo mode: any details open the sample app.')}</Note>:null}
    </Card>:<Card>
      <Label>{t('Microsoft Authenticator')}</Label>
      <Note>{recovery?t('Enter one of your recovery codes (each works once).'):mfa.message}</Note>
      <Field label={recovery?t('Recovery code'):'6-digit code'} value={code} onChangeText={setCode}
        keyboardType={recovery?'default':'number-pad'} placeholder={recovery?'xxxx-xxxx':'123456'}/>
      <Btn title={t('Verify')} onPress={()=>void submitCode()}/>
      <Btn title={recovery?t('Use the authenticator code'):t('Lost your phone? Use a recovery code')} outline
        onPress={()=>{setRecovery(!recovery);setCode('');}}/>
      <Btn title={t('Back')} outline onPress={()=>{setMfa(null);setCode('');}}/>
    </Card>}
    <View style={[S.card,{alignItems:'center'}]}>
      <Text style={S.muted}>New to LiveBetter?</Text>
      <Btn title={t('Register')} outline onPress={()=>router.push('/register')}/>
    </View>
  </Page>;
}

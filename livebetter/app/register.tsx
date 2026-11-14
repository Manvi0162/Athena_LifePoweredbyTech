import React,{useState} from 'react';
import {t} from '../src/i18n';
import {Alert,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../src/context';
import {Btn,Card,Field,Label,LanguagePicker,Note,Page,readError} from '../src/ui';
import {S} from '../src/theme';

export default function Register(){
  const {signup,demo}=useApp();
  const [name,setName]=useState('');
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  const [confirmPassword,setConfirmPassword]=useState('');

  async function createAccount(){
    if(!name.trim())return Alert.alert(t('Name required'),t('Enter your name to continue.'));
    if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()))
      return Alert.alert(t('Check your email'),t('Enter a valid email address.'));
    if(password.length<8)
      return Alert.alert(t('Password too short'),t('Use at least 8 characters.'));
    if(password!==confirmPassword)
      return Alert.alert(t('Passwords do not match'),t('Re-enter your password confirmation.'));
    try{
      const message=await signup(name.trim(),email.trim(),password);
      if(demo){router.replace('/onboarding');return;}
      if(message==='SESSION')router.replace({pathname:'/security',params:{setup:'1'}});   // logged in: set the pattern now
      else{Alert.alert(t('Check your email'),t('Account created. Open the link in the email we sent you, then log in. You will set your security pattern right after.'));router.replace('/login');}
    }catch(error){Alert.alert(t('Could not create account'),readError(error));}
  }

  return <Page showTabs={false} title={t('Create your account')}
    subtitle={t('Enter your details to get started with LiveBetter.')}>
    <Card>
      <Label>{t('Account details')}</Label>
      <Field label={t('Full name')} value={name} onChangeText={setName}
        placeholder={t('Your name')}/>
      <Field label={t('Email address')} value={email} onChangeText={setEmail}
        placeholder={t('you@example.com')} keyboardType="email-address"/>
      <Field label={t('Password')} value={password} onChangeText={setPassword}
        placeholder={t('At least 8 characters')} secureTextEntry/>
      {password&&password.length<8?<Note>{`${password.length}/8 characters: the password needs at least 8.`}</Note>:null}
      <Field label={t('Confirm password')} value={confirmPassword} onChangeText={setConfirmPassword}
        placeholder={t('Re-enter your password')} secureTextEntry/>
      <LanguagePicker/>
      <Note>{t('Forms, screens and reports use this language. Calculated numbers stay the same.')}</Note>
      <Btn title={t('Create account')} onPress={()=>void createAccount()}/>
      <Note>{demo?t('Demo mode: nothing is sent to a server.'):t('Next: set a security pattern, and choose whether to add Microsoft Authenticator.')}</Note>
    </Card>
    <View style={[S.card,{alignItems:'center'}]}>
      <Text style={S.muted}>Already have an account?</Text>
      <Btn title={t('Log in')} outline onPress={()=>router.replace('/login')}/>
    </View>
  </Page>;
}

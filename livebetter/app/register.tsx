import React,{useState} from 'react';
import {Alert,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../src/context';
import {Btn,Card,Field,Label,Note,Page,readError} from '../src/ui';
import {S} from '../src/theme';

export default function Register(){
  const {signup,demo}=useApp();
  const [name,setName]=useState('');
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  const [confirmPassword,setConfirmPassword]=useState('');

  async function createAccount(){
    if(!name.trim())return Alert.alert('Name required','Enter your name to continue.');
    if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()))
      return Alert.alert('Check your email','Enter a valid email address.');
    if(password.length<8)
      return Alert.alert('Password too short','Use at least 8 characters.');
    if(password!==confirmPassword)
      return Alert.alert('Passwords do not match','Re-enter your password confirmation.');
    try{
      const message=await signup(name.trim(),email.trim(),password);
      if(demo){router.replace('/onboarding');return;}
      if(message.startsWith('Account created.'))router.replace({pathname:'/security',params:{setup:'1'}});
      else{Alert.alert('Check your email',message);router.replace('/login');}
    }catch(error){Alert.alert('Could not create account',readError(error));}
  }

  return <Page showTabs={false} title="Create your account"
    subtitle="Enter your details to get started with LiveBetter.">
    <Card>
      <Label>Account details</Label>
      <Field label="Full name" value={name} onChangeText={setName}
        placeholder="Your name"/>
      <Field label="Email address" value={email} onChangeText={setEmail}
        placeholder="you@example.com" keyboardType="email-address"/>
      <Field label="Password" value={password} onChangeText={setPassword}
        placeholder="At least 8 characters" secureTextEntry/>
      {password&&password.length<8?<Note>{`${password.length}/8 characters: the password needs at least 8.`}</Note>:null}
      <Field label="Confirm password" value={confirmPassword} onChangeText={setConfirmPassword}
        placeholder="Re-enter your password" secureTextEntry/>
      <Btn title="Create account" onPress={()=>void createAccount()}/>
      <Note>{demo?'Demo mode: nothing is sent to a server.':'Next: set a security pattern, and choose whether to add Microsoft Authenticator.'}</Note>
    </Card>
    <View style={[S.card,{alignItems:'center'}]}>
      <Text style={S.muted}>Already have an account?</Text>
      <Btn title="Log in" outline onPress={()=>router.replace('/login')}/>
    </View>
  </Page>;
}

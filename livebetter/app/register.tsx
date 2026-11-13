import React,{useState} from 'react';
import {Alert,Text,View} from 'react-native';
import {router} from 'expo-router';
import {Btn,Card,Field,Label,Note,Page} from '../src/ui';
import {S} from '../src/theme';

export default function Register(){
  const [name,setName]=useState('');
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  const [confirmPassword,setConfirmPassword]=useState('');

  function createAccount(){
    if(!name.trim())return Alert.alert('Name required','Enter your name to continue.');
    if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()))
      return Alert.alert('Check your email','Enter a valid email address.');
    if(password.length<8)
      return Alert.alert('Password too short','Use at least 8 characters.');
    if(password!==confirmPassword)
      return Alert.alert('Passwords do not match','Re-enter your password confirmation.');
    Alert.alert('Registration unavailable',
      'Account registration is not connected yet. Your details have not been saved.');
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
      <Field label="Confirm password" value={confirmPassword} onChangeText={setConfirmPassword}
        placeholder="Re-enter your password" secureTextEntry/>
      <Btn title="Create account" onPress={createAccount}/>
      <Note>Account registration is not connected yet. Your details will not be stored.</Note>
    </Card>
    <View style={[S.card,{alignItems:'center'}]}>
      <Text style={S.muted}>Already have an account?</Text>
      <Btn title="Log in" outline onPress={()=>router.replace('/login')}/>
    </View>
  </Page>;
}

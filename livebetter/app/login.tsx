import React,{useState} from 'react';
import {Alert,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../src/context';
import {Btn,Card,Field,Label,Note,Page} from '../src/ui';
import {C,S} from '../src/theme';

export default function Login(){
  const {demo}=useApp();
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  return <Page back title="Welcome back"
    subtitle="Your household, all in one place.">
    <ViewIntro/>
    <Card>
      <Label>Sign in</Label>
      <Field label="Email address" value={email} onChangeText={setEmail}
        placeholder="you@example.com" keyboardType="email-address"/>
      <Field label="Password" value={password} onChangeText={setPassword}
        secureTextEntry placeholder="Enter your password"/>
      <Btn title="Sign in" onPress={()=>Alert.alert('Sign-in unavailable',
        'Account authentication is not connected in this preview. Continue with the demo household instead.')}/>
      <Btn title="Continue with demo household" outline
        onPress={()=>router.push('/onboarding')}/>
      <Note>{demo?'Demo mode uses fictional local data.':'Sign-in and secure account storage are not connected in this build.'}</Note>
    </Card>
    <Text style={[S.muted,{textAlign:'center'}]}>New here? Set up your household to begin.</Text>
    <Btn title="Set up my household" outline onPress={()=>router.push('/onboarding')}/>
  </Page>;
}

function ViewIntro(){
  return <View style={[S.card,{backgroundColor:C.softGreen,borderColor:C.softGreen}]}>
    <Text style={[S.title,{color:C.green}]}>Start with what matters at home.</Text>
    <Note>Water, electricity and groceries, organized around your household.</Note>
  </View>;
}

import React,{useState} from 'react';
import {Alert,Text,View} from 'react-native';
import {router} from 'expo-router';
import {Btn,Card,Field,Label,Page} from '../src/ui';
import {S} from '../src/theme';

export default function Login(){
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  return <Page showTabs={false} title="Log in" subtitle="Sign in to continue to your household.">
    <Card>
      <Label>Your account</Label>
      <Field label="Email address" value={email} onChangeText={setEmail}
        placeholder="you@example.com" keyboardType="email-address"/>
      <Field label="Password" value={password} onChangeText={setPassword}
        secureTextEntry placeholder="Enter your password"/>
      <Btn title="Log in" onPress={()=>Alert.alert('Login unavailable',
        'Account authentication is not configured yet. Please contact the app administrator.')}/>
    </Card>
    <View style={[S.card,{alignItems:'center'}]}>
      <Text style={S.muted}>New to LiveBetter?</Text>
      <Btn title="Register" outline onPress={()=>router.push('/register')}/>
    </View>
  </Page>;
}

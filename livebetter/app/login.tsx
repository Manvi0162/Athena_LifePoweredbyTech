import React,{useState} from 'react';
import {Alert,Text} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../src/context';
import {Btn,Card,Field,Label,Note,Page} from '../src/ui';
export default function Login(){const {demo}=useApp();
  const [email,setEmail]=useState(''),[password,setPassword]=useState('');
  return <Page title="Welcome to LiveBetter" subtitle="Plan household expenses. Waste less. Make decisions with evidence.">
    <Card><Label>Try the application</Label>
      <Note>{demo?'A fictional local account is provided for judging the interface before backend integration.':'Developer testing only. Production identity verification is not wired.'}</Note>
      <Btn title={demo?'Continue as demo household':'Continue to assessment (developer preview)'} onPress={()=>router.push('/onboarding')}/>
    </Card>
    <Card><Label>Sign in — integration pending</Label>
      <Field label="Email" value={email} onChangeText={setEmail} keyboardType="email-address"/>
      <Field label="Password" value={password} onChangeText={setPassword} secureTextEntry/>
      <Btn title="Sign in" outline onPress={()=>Alert.alert('Auth not connected',
        'This is the sign-in UI only. Member 2 must integrate Supabase Auth and backend household authorization before production sign-in works.')}/>
      <Note>Do not enter a real password here. This build does not authenticate or securely store login credentials.</Note>
    </Card>
  </Page>;
}

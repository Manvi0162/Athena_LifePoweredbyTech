import React,{useState} from 'react';
import {Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {C,S} from '../../src/theme';
import {ActionRow,Btn,Card,Label,Note,Page} from '../../src/ui';

export default function Settings(){
  const {state,demo,clearDemo}=useApp();
  const [confirmReset,setConfirmReset]=useState(false);
  const [resetError,setResetError]=useState<string|null>(null);
  return <Page back title="Settings" subtitle="Your household and app preferences.">
    <Card>
      <Label>Household details</Label>
      <Note>{state.household?.name||'Household'} · {state.household?.members||0} people · {state.household?.home_type||'Home not set'}</Note>
      <ActionRow icon="⌂" title="Household assessment" subtitle="Update your household details"
        onPress={()=>router.push('/onboarding')}/>
    </Card>
    <Card>
      <Label>Language</Label>
      <View style={[S.between,{paddingVertical:11,borderBottomWidth:1,borderBottomColor:C.line}]}>
        <Text style={S.body}>English</Text><Text style={{color:C.green,fontWeight:'800'}}>ACTIVE</Text>
      </View>
      <Text style={S.body}>Français · Kreol Morisien</Text>
      <Note>Additional language translations are not enabled in this app build.</Note>
    </Card>
    <Card>
      <Label>History and activity</Label>
      <ActionRow icon="◷" title="Household activity" subtitle="Bills, receipts and pantry updates"
        onPress={()=>router.push('/activity')}/>
    </Card>
    <Card>
      <Label>Your data</Label>
      <Note>{demo?'Demo records are stored on this device.':'Household records are sent to the configured API.'} Do not enter sensitive personal details in this preview.</Note>
      {demo?<View style={{gap:9}}>
        {confirmReset?<View style={{gap:8,backgroundColor:C.dangerBg,borderRadius:14,padding:12}}>
          <Text style={{color:C.red,fontWeight:'700'}}>This removes local bills, receipts and pantry changes.</Text>
          {resetError?<Text style={{color:C.red}}>{resetError}</Text>:null}
          <Btn title="Confirm reset" danger onPress={async()=>{
            try{await clearDemo();router.replace('/welcome');}
            catch(error){setResetError(String(error));}
          }}/>
          <Btn title="Cancel" outline onPress={()=>{setConfirmReset(false);setResetError(null);}}/>
        </View>:<Btn title="Reset local demo data" danger onPress={()=>setConfirmReset(true)}/>}
      </View>:null}
    </Card>
  </Page>;
}

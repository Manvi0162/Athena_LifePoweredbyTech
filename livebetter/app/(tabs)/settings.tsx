import React from 'react';
import {Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {C,S} from '../../src/theme';
import {ActionRow,Card,Label,Note,Page} from '../../src/ui';

export default function Settings(){
  const {state}=useApp();
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
  </Page>;
}

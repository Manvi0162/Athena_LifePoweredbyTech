import React from 'react';
import {Text,View} from 'react-native';
import {router} from 'expo-router';
import {C,S} from '../src/theme';
import {Btn,Card,Note,Page} from '../src/ui';

export default function Welcome(){
  return <Page title="Smarter home. Less waste. Better living."
    subtitle="See what is coming, use what you have, and make every rupee count.">
    <View style={S.heroCard}>
      <Text style={{fontSize:12,fontWeight:'800',letterSpacing:1,color:'#BCEFE2'}}>LIVEBETTER ✦</Text>
      <Text style={{fontSize:21,lineHeight:28,fontWeight:'800',color:C.white}}>
        A clearer picture of your household.
      </Text>
      <Text style={S.heroFootnote}>Track utilities, plan meals from your pantry, and get useful next steps.</Text>
      <View style={{flexDirection:'row',gap:12,justifyContent:'center',paddingVertical:12}}>
        {['◉','ϟ','▤'].map(icon=><View key={icon} style={{width:54,height:54,borderRadius:17,backgroundColor:'#254259',alignItems:'center',justifyContent:'center'}}>
          <Text style={{fontSize:23,color:C.white}}>{icon}</Text>
        </View>)}
      </View>
    </View>
    <Card>
      <Btn title="Get started  →" onPress={()=>router.push('/login')}/>
      <Btn title="Explore demo household" outline onPress={()=>router.push('/onboarding')}/>
      <Note>Demo values are examples. No account is created in this preview.</Note>
    </Card>
  </Page>;
}

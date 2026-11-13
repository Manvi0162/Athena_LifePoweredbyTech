import React from 'react';
import {t} from '../src/i18n';
import {Text,View} from 'react-native';
import {router} from 'expo-router';
import {C,S} from '../src/theme';
import {Btn,Card,LanguagePicker,Page} from '../src/ui';

export default function Welcome(){
  return <Page back={false} showTabs={false} title={t('Smarter home. Less waste. Better living.')}
    subtitle={t('See what is coming, use what you have, and make every rupee count.')}>
    <View style={S.heroCard}>
      <Text style={{fontSize:12,fontWeight:'800',letterSpacing:1,color:'#BCEFE2'}}>{t('LIVEBETTER ✦')}</Text>
      <Text style={{fontSize:21,lineHeight:28,fontWeight:'800',color:C.white}}>
        {t('A clearer picture of your household.')}
      </Text>
      <Text style={S.heroFootnote}>{t('Track utilities, plan meals from your pantry, and get useful next steps.')}</Text>
      <View style={{flexDirection:'row',gap:12,justifyContent:'center',paddingVertical:12}}>
        {['◉','ϟ','▤'].map(icon=><View key={icon} style={{width:54,height:54,borderRadius:17,backgroundColor:'#254259',alignItems:'center',justifyContent:'center'}}>
          <Text style={{fontSize:23,color:C.white}}>{icon}</Text>
        </View>)}
      </View>
    </View>
    <Card>
      <LanguagePicker/>
      <Btn title={t('Log in')} onPress={()=>router.push('/login')}/>
      <Btn title={t('Register')} outline onPress={()=>router.push('/register')}/>
    </Card>
  </Page>;
}

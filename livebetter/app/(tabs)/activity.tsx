import React,{useCallback} from 'react';
import {Pressable,Text,View} from 'react-native';
import {router,useFocusEffect} from 'expo-router';
import {useApp} from '../../src/context';
import {C,S} from '../../src/theme';
import {Note,Page} from '../../src/ui';
import {CATEGORY_INFO,Category,categoryOf} from '../../src/activity';

const ORDER:Category[]=['ai','water','electricity','groceries','security'];
const TINT:Record<Category,string>={ai:'#EEF0FF',water:C.softBlue,electricity:C.softElectric,groceries:C.softGreen,
  security:'#FDECEC',household:C.bg};

// Activity tab: one row per section; each opens the full timeline (with date filter and PDF export).
export default function Activity(){
  const {state,refreshAll}=useApp();
  useFocusEffect(useCallback(()=>{void refreshAll().catch(()=>undefined);},[]));
  const by=(c:Category)=>state.activity.filter(a=>categoryOf(a)===c);
  const extra=by('household').length?['household' as Category]:[];
  return <Page back={false} title="Activity" subtitle="Everything recorded for your household, by section." showSettings>
    {[...ORDER,...extra].map(c=>{
      const list=by(c);const info=CATEGORY_INFO[c];const last=list[0];
      const warn=c==='security'&&list.some(a=>/BLOCKED|Wrong|locked/i.test(a.message));
      return <Pressable key={c} accessibilityRole="button" accessibilityLabel={`${info.title} activity`}
        onPress={()=>router.push({pathname:'/activity-detail',params:{category:c}})}
        style={{flexDirection:'row',alignItems:'center',gap:12,padding:15,borderRadius:18,backgroundColor:TINT[c]}}>
        <View style={[S.actionIcon,{backgroundColor:C.white}]}><Text style={[S.actionIconText,warn&&{color:C.red}]}>{info.icon}</Text></View>
        <View style={{flex:1,gap:2}}>
          <View style={S.between}><Text style={S.title}>{info.title}</Text>
            <Text style={[S.muted,{fontWeight:'800'}]}>{list.length}</Text></View>
          <Text style={[S.muted,warn&&{color:C.red,fontWeight:'700'}]} numberOfLines={1}>
            {last?last.message:info.about}</Text>
        </View>
        <Text style={S.actionArrow}>›</Text>
      </Pressable>;
    })}
    <Note>Open a section to filter by dates and export a PDF report.</Note>
  </Page>;
}

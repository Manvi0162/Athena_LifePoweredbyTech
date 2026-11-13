import React,{useEffect,useState} from 'react';
import {ActivityIndicator,Keyboard,KeyboardAvoidingView,KeyboardTypeOptions,Platform,Pressable,ScrollView,Text,TextInput,View} from 'react-native';
import {router,usePathname} from 'expo-router';
import {SafeAreaView} from 'react-native-safe-area-context';
import {C,S} from './theme';
import {useApp} from './context';
export function Page({title,subtitle,children,back=true,showSettings,stickyFooter,showTabs=true,hideBrand=false,headerRight}:{title:string;subtitle?:string;children:React.ReactNode;back?:boolean;showSettings?:boolean;stickyFooter?:React.ReactNode;showTabs?:boolean;hideBrand?:boolean;headerRight?:React.ReactNode}){
  const {error,clearError}=useApp();
  const [keyboardVisible,setKeyboardVisible]=useState(false);
  useEffect(()=>{
    const show=Keyboard.addListener('keyboardDidShow',()=>setKeyboardVisible(true));
    const hide=Keyboard.addListener('keyboardDidHide',()=>setKeyboardVisible(false));
    return()=>{show.remove();hide.remove();};
  },[]);
  return <SafeAreaView style={S.screen} edges={['top','bottom']}>
    <KeyboardAvoidingView style={{flex:1}} behavior={Platform.OS==='ios'?'padding':'height'}>
    <ScrollView style={S.screen} contentContainerStyle={S.content} keyboardShouldPersistTaps="handled"
      keyboardDismissMode={Platform.OS==='ios'?'interactive':'on-drag'} automaticallyAdjustKeyboardInsets>
      <View style={S.screenHeader}>
        {hideBrand?<>
          {back?<Pressable accessibilityRole="button" accessibilityLabel="Go back" onPress={()=>router.canGoBack()?router.back():router.replace('/(tabs)/home')} style={S.topAction}><Text style={S.topActionText}>‹</Text></Pressable>:<View/>}
          {headerRight}
        </>:<>
          <View style={S.brandRow}>
            {back?<Pressable accessibilityRole="button" accessibilityLabel="Go back" onPress={()=>router.canGoBack()?router.back():router.replace('/(tabs)/home')} style={S.topAction}><Text style={S.topActionText}>‹</Text></Pressable>:null}
            <View accessibilityLabel="LiveBetter L plus logo" style={S.brandMark}>
              <Text style={S.brandInitial}>L</Text>
              <Text style={S.brandPlus}>+</Text>
            </View>
            <View><Text style={S.brandName}>LIVEBETTER</Text><Text style={S.brandCaption}>HOUSEHOLD PLANNER</Text></View>
          </View>
          {headerRight}
          {showSettings?<Pressable accessibilityRole="button" accessibilityLabel="Open settings" onPress={()=>router.push('/settings')} style={S.topAction}><Text style={S.topActionText}>⚙</Text></Pressable>:null}
        </>}
      </View>
      <Text style={S.h1}>{title}</Text>{subtitle?<Text style={S.muted}>{subtitle}</Text>:null}
      {error?<Pressable onPress={clearError}><Text style={S.error}>{error}  · Tap to dismiss</Text></Pressable>:null}
      {children}
    </ScrollView>
    {stickyFooter?<View style={{backgroundColor:C.white,borderTopWidth:1,borderTopColor:C.line,paddingHorizontal:18,paddingTop:10,paddingBottom:8}}>
      {stickyFooter}
    </View>:null}
    {showTabs&&!keyboardVisible?<BottomNavigation/>:null}
    </KeyboardAvoidingView>
  </SafeAreaView>;
}
function BottomNavigation(){
  const pathname=usePathname();
  const path=pathname.split('/').filter(Boolean).pop()||'home';
  const activeTab=path==='utilities'||path==='water'||path==='electricity'||path==='bill'?'utilities'
    :path==='pantry'||path==='receipt'||path==='pantry-updated'||pathname.startsWith('/recipe/')?'pantry'
    :path==='coach'?'coach':'home';
  const tabs=[
    {name:'home',label:'Home',icon:'⌂'},
    {name:'utilities',label:'Utilities',icon:'◉'},
    {name:'pantry',label:'Pantry',icon:'▤'},
    {name:'coach',label:'Coach',icon:'✦'},
  ] as const;
  return <View accessibilityRole="tablist" style={S.bottomNavigation}>
    {tabs.map(tab=>{
      const focused=activeTab===tab.name;
      return <Pressable key={tab.name} accessibilityRole="tab" accessibilityState={{selected:focused}}
        accessibilityLabel={`${tab.label} tab`} onPress={()=>router.replace(`/(tabs)/${tab.name}`)}
        style={S.bottomNavigationItem}>
        <View style={[S.tabIcon,focused&&{backgroundColor:C.mint}]}>
          <Text style={[S.tabIconText,{color:focused?C.green:C.muted}]}>{tab.icon}</Text>
        </View>
        <Text style={{fontSize:10,fontWeight:'700',color:focused?C.green:C.muted}}>{tab.label}</Text>
      </Pressable>;
    })}
  </View>;
}
export function Card({children}:{children:React.ReactNode}){return <View style={S.card}>{children}</View>;}
export function Label({children}:{children:React.ReactNode}){return <Text style={S.title}>{children}</Text>;}
export function Body({children}:{children:React.ReactNode}){return <Text style={S.body}>{children}</Text>;}
export function Note({children}:{children:React.ReactNode}){return <Text style={S.muted}>{children}</Text>;}
export function ActionRow({icon,title,subtitle,onPress}:{icon:string;title:string;subtitle:string;onPress:()=>void}){
  return <Pressable accessibilityRole="button" onPress={onPress} style={S.actionRow}>
    <View style={S.actionIcon}><Text style={S.actionIconText}>{icon}</Text></View>
    <View style={{flex:1,gap:2}}><Text style={S.title}>{title}</Text><Text style={S.muted}>{subtitle}</Text></View>
    <Text style={S.actionArrow}>›</Text>
  </Pressable>;
}
export function ChoiceChips({label,options,value,onChange}:{label:string;options:string[];value:string;onChange:(value:string)=>void}){
  return <View style={{gap:7}}>
    <Text style={[S.muted,{fontWeight:'700'}]}>{label}</Text>
    <View style={S.choiceRow}>{options.map(option=><Pressable key={option} accessibilityRole="button"
      accessibilityState={{selected:value===option}} onPress={()=>onChange(option)}
      style={[S.choice,value===option&&S.choiceSelected]}>
      <Text style={[S.choiceText,value===option&&S.choiceTextSelected]}>{option}</Text>
    </Pressable>)}</View>
  </View>;
}
export function Btn({title,onPress,disabled,outline,danger}:{title:string;onPress:()=>void;disabled?:boolean;outline?:boolean;danger?:boolean}){
  const {busy}=useApp();const lock=disabled||busy;
  return <Pressable accessibilityRole="button" disabled={lock} onPress={onPress}
    style={[S.btn,outline&&S.outline,danger&&{backgroundColor:C.red},lock&&{opacity:0.55}]}>
    <Text style={[S.btnText,outline&&S.outlineText]}>{title}</Text>
  </Pressable>;
}
export function Field({label,value,onChangeText,placeholder,keyboardType,multiline,secureTextEntry}:{label:string;value:string;onChangeText:(v:string)=>void;
  placeholder?:string;keyboardType?:KeyboardTypeOptions;multiline?:boolean;secureTextEntry?:boolean}){
  return <View style={{gap:3}}><Text style={[S.muted,{fontWeight:'700'}]}>{label}</Text><TextInput
    style={[S.field,multiline&&{minHeight:78,textAlignVertical:'top'}]} value={value} onChangeText={onChangeText}
    placeholder={placeholder} placeholderTextColor="#9AA9A4" keyboardType={keyboardType} multiline={multiline} secureTextEntry={secureTextEntry}
    autoCapitalize={secureTextEntry||keyboardType==='email-address'?'none':'sentences'}/>
  </View>;
}
export function Loading(){return <View style={{padding:24}}><ActivityIndicator color={C.green}/><Text style={[S.muted,{textAlign:'center',marginTop:8}]}>Loading…</Text></View>;}
export const readError=(e:unknown)=>e instanceof Error?e.message:String(e);

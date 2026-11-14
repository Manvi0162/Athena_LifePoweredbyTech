import React,{useEffect,useState} from 'react';
import {LANGS,t} from './i18n';
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
            <View><Text style={S.brandName}>{t('LIVEBETTER')}</Text><Text style={S.brandCaption}>{t('HOUSEHOLD PLANNER')}</Text></View>
          </View>
          {headerRight}
          {showSettings?<Pressable accessibilityRole="button" accessibilityLabel="Open settings" onPress={()=>router.push('/settings')} style={S.topAction}><Text style={S.topActionText}>⚙</Text></Pressable>:null}
        </>}
      </View>
      <Text style={S.h1}>{title}</Text>{subtitle?<Text style={S.muted}>{subtitle}</Text>:null}
      {error?<ErrorBox text={error} onClose={clearError}/>:null}
      {children}
    </ScrollView>
    {stickyFooter?<View style={{backgroundColor:C.white,borderTopWidth:1,borderTopColor:C.line,paddingHorizontal:18,paddingTop:10,paddingBottom:8}}>
      {stickyFooter}
    </View>:null}
    {showTabs&&!keyboardVisible?<BottomNavigation/>:null}
    </KeyboardAvoidingView>
  </SafeAreaView>;
}
export function BottomNavigation(){
  const pathname=usePathname();
  const path=pathname.split('/').filter(Boolean).pop()||'home';
  const activeTab=path==='utilities'||path==='water'||path==='electricity'||path==='bill'||path==='habits'?'utilities'
    :path==='pantry'||path==='receipt'||path==='pantry-updated'||path==='stock'||path==='ingredients'||path==='cook-now'||path==='my-recipes'||pathname.startsWith('/recipe/')?'pantry'
    :path==='coach'?'coach':path==='activity'||pathname.startsWith('/activity')?'activity':'home';
  const tabs=[
    {name:'home',label:'Home',icon:'⌂'},
    {name:'utilities',label:'Utilities',icon:'◉'},
    {name:'pantry',label:'Pantry',icon:'▤'},
    {name:'coach',label:'Coach',icon:'✦'},
    {name:'activity',label:'Activity',icon:'◷'},
  ] as const;
  return <View accessibilityRole="tablist" style={S.bottomNavigation}>
    {tabs.map(tab=>{
      const focused=activeTab===tab.name;
      return <Pressable key={tab.name} accessibilityRole="tab" accessibilityState={{selected:focused}}
        accessibilityLabel={`${t(tab.label)}`} onPress={()=>router.replace(`/(tabs)/${tab.name}`)}
        style={S.bottomNavigationItem}>
        <View style={[S.tabIcon,focused&&{backgroundColor:C.mint}]}>
          <Text style={[S.tabIconText,{color:focused?C.green:C.muted}]}>{tab.icon}</Text>
        </View>
        <Text style={{fontSize:10,fontWeight:'700',color:focused?C.green:C.muted}}>{t(tab.label)}</Text>
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
// A friendly error box: icon, the message, and a clear ✕ to close it.
export function ErrorBox({text,onClose,action}:{text:string;onClose?:()=>void;action?:{title:string;onPress:()=>void}}){
  return <View accessibilityRole="alert" style={{flexDirection:'row',gap:10,backgroundColor:'#FDECEC',borderColor:'#F5C9C9',
    borderWidth:1,borderRadius:16,padding:13,alignItems:'flex-start'}}>
    <Text style={{fontSize:16}}>⚠️</Text>
    <View style={{flex:1,gap:8}}>
      <Text style={{color:'#8A2C2C',fontSize:14,lineHeight:20,fontWeight:'600'}}>{text}</Text>
      {action?<Pressable accessibilityRole="button" onPress={action.onPress} style={{alignSelf:'flex-start',backgroundColor:C.white,
        borderRadius:10,borderWidth:1,borderColor:'#F5C9C9',paddingHorizontal:12,paddingVertical:7}}>
        <Text style={{color:C.red,fontWeight:'800'}}>{action.title}</Text></Pressable>:null}
    </View>
    {onClose?<Pressable accessibilityRole="button" accessibilityLabel={t('Close')} onPress={onClose} hitSlop={10}>
      <Text style={{color:'#8A2C2C',fontWeight:'900',fontSize:16}}>✕</Text></Pressable>:null}
  </View>;
}

// Dropdown (select): shows the chosen value, opens the list of options below it.
export function Dropdown({label,options,value,onChange}:{label:string;options:{value:string;label:string}[];value:string;onChange:(value:string)=>void}){
  const [open,setOpen]=useState(false);
  const current=options.find(o=>o.value===value)||options[0];
  return <View style={{gap:7}}>
    <Text style={[S.muted,{fontWeight:'700'}]}>{label}</Text>
    <Pressable accessibilityRole="combobox" accessibilityLabel={label} accessibilityState={{expanded:open}} onPress={()=>setOpen(o=>!o)}
      style={[S.field,{flexDirection:'row',alignItems:'center',justifyContent:'space-between'}]}>
      <Text style={{fontSize:16,color:C.ink}}>{current?.label}</Text>
      <Text style={{color:C.green,fontWeight:'900'}}>{open?'▴':'▾'}</Text>
    </Pressable>
    {open?<View style={{borderWidth:1,borderColor:C.line,borderRadius:14,backgroundColor:C.white,overflow:'hidden'}}>
      {options.map((o,i)=><Pressable key={o.value} accessibilityRole="menuitem" accessibilityState={{selected:o.value===value}}
        onPress={()=>{onChange(o.value);setOpen(false);}}
        style={{paddingVertical:13,paddingHorizontal:16,borderTopWidth:i?1:0,borderTopColor:C.line,
          backgroundColor:o.value===value?C.softGreen:C.white,flexDirection:'row',justifyContent:'space-between'}}>
        <Text style={{fontSize:16,color:C.ink,fontWeight:o.value===value?'800':'500'}}>{o.label}</Text>
        {o.value===value?<Text style={{color:C.green,fontWeight:'900'}}>✓</Text>:null}
      </Pressable>)}
    </View>:null}
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
export function Loading(){return <View style={{padding:24}}><ActivityIndicator color={C.green}/><Text style={[S.muted,{textAlign:'center',marginTop:8}]}>{t('Loading…')}</Text></View>;}
export const readError=(e:unknown)=>e instanceof Error?e.message:String(e);

// App language: English / Français / Kreol Morisien (forms, screens and reports).
export function LanguagePicker(){
  const {lang,setLanguage}=useApp();
  return <View style={{gap:7}}>
    <Text style={[S.muted,{fontWeight:'700'}]}>{t('App language')}</Text>
    <View style={S.choiceRow}>{LANGS.map(l=><Pressable key={l.code} accessibilityRole="button" accessibilityState={{selected:lang===l.code}}
      onPress={()=>void setLanguage(l.code)} style={[S.choice,lang===l.code&&S.choiceSelected]}>
      <Text style={[S.choiceText,lang===l.code&&S.choiceTextSelected]}>{l.label}</Text></Pressable>)}</View>
  </View>;
}

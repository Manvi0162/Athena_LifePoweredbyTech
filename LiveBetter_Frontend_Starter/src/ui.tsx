import React from 'react';
import {ActivityIndicator,KeyboardTypeOptions,Pressable,ScrollView,Text,TextInput,View} from 'react-native';
import {C,S} from './theme';
import {useApp} from './context';
export function Page({title,subtitle,children}:{title:string;subtitle?:string;children:React.ReactNode}){
  const {demo,error,clearError}=useApp();
  return <ScrollView style={S.screen} contentContainerStyle={S.content} keyboardShouldPersistTaps="handled">
    <Text style={S.h1}>{title}</Text>{subtitle?<Text style={S.muted}>{subtitle}</Text>:null}
    <View style={[S.tag,{backgroundColor:demo?C.amber:C.mint}]}><Text style={[S.tagText,{color:demo?'#875500':C.green}]}>{demo?'DEMO MODE · fictional local data':'LIVE API MODE'}</Text></View>
    {error?<Pressable onPress={clearError}><Text style={S.error}>{error}  · Tap to dismiss</Text></Pressable>:null}
    {children}
  </ScrollView>;
}
export function Card({children}:{children:React.ReactNode}){return <View style={S.card}>{children}</View>;}
export function Label({children}:{children:React.ReactNode}){return <Text style={S.title}>{children}</Text>;}
export function Body({children}:{children:React.ReactNode}){return <Text style={S.body}>{children}</Text>;}
export function Note({children}:{children:React.ReactNode}){return <Text style={S.muted}>{children}</Text>;}
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
    placeholder={placeholder} placeholderTextColor="#9AA9A4" keyboardType={keyboardType} multiline={multiline} secureTextEntry={secureTextEntry} autoCapitalize="sentences"/>
  </View>;
}
export function Loading(){return <View style={{padding:24}}><ActivityIndicator color={C.green}/><Text style={[S.muted,{textAlign:'center',marginTop:8}]}>Loading…</Text></View>;}
export const readError=(e:unknown)=>e instanceof Error?e.message:String(e);

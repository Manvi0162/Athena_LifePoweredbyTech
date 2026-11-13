import React from 'react';
import {Tabs} from 'expo-router';
import {Text,View} from 'react-native';
import {C,S} from '../../src/theme';

export default function TabLayout(){return <Tabs screenOptions={{headerShown:false,tabBarActiveTintColor:C.green,
  tabBarInactiveTintColor:C.muted,tabBarStyle:{width:'100%',maxWidth:480,alignSelf:'center',height:70,paddingBottom:6,paddingTop:7,
    backgroundColor:C.white,borderTopColor:C.line,borderTopWidth:1,elevation:8},
  tabBarLabelStyle:{fontSize:10,fontWeight:'700'}}}>
  <Tabs.Screen name="home" options={{title:'Home',tabBarIcon:({focused})=><View style={[S.tabIcon,focused&&{backgroundColor:C.mint}]}><Text style={[S.tabIconText,{color:focused?C.green:C.muted}]}>⌂</Text></View>}}/>
  <Tabs.Screen name="utilities" options={{title:'Utilities',tabBarIcon:({focused})=><View style={[S.tabIcon,focused&&{backgroundColor:C.mint}]}><Text style={[S.tabIconText,{color:focused?C.green:C.muted}]}>◉</Text></View>}}/>
  <Tabs.Screen name="pantry" options={{title:'Pantry',tabBarIcon:({focused})=><View style={[S.tabIcon,focused&&{backgroundColor:C.mint}]}><Text style={[S.tabIconText,{color:focused?C.green:C.muted}]}>▤</Text></View>}}/>
  <Tabs.Screen name="coach" options={{title:'Coach',tabBarIcon:({focused})=><View style={[S.tabIcon,focused&&{backgroundColor:C.mint}]}><Text style={[S.tabIconText,{color:focused?C.green:C.muted}]}>✦</Text></View>}}/>
</Tabs>;}

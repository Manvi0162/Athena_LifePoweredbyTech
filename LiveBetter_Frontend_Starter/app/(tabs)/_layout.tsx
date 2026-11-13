import React from 'react';
import {Tabs} from 'expo-router';
import {Text} from 'react-native';
import {C} from '../../src/theme';
export default function TabLayout(){return <Tabs screenOptions={{headerShown:false,tabBarActiveTintColor:C.green,
  tabBarInactiveTintColor:C.muted,tabBarStyle:{height:64,paddingBottom:6,paddingTop:6,backgroundColor:C.white},
  tabBarLabelStyle:{fontSize:11,fontWeight:'700'}}}>
  <Tabs.Screen name="home" options={{title:'Home',tabBarIcon:()=> <Text>🏠</Text>}}/>
  <Tabs.Screen name="utilities" options={{title:'Utilities',tabBarIcon:()=> <Text>💧</Text>}}/>
  <Tabs.Screen name="pantry" options={{title:'Pantry',tabBarIcon:()=> <Text>🥕</Text>}}/>
  <Tabs.Screen name="coach" options={{title:'AI Coach',tabBarIcon:()=> <Text>🧠</Text>}}/>
</Tabs>;}

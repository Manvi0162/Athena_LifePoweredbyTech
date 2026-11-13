import React from 'react';
import {Stack} from 'expo-router';
import {StatusBar} from 'expo-status-bar';
import {AppProvider} from '../src/context';
import {C} from '../src/theme';
export default function RootLayout(){return <AppProvider><StatusBar style="dark"/>
  <Stack screenOptions={{headerStyle:{backgroundColor:C.white},headerTintColor:C.green,contentStyle:{backgroundColor:C.bg}}}>
    <Stack.Screen name="index" options={{headerShown:false}}/>
    <Stack.Screen name="login" options={{headerShown:false}}/>
    <Stack.Screen name="onboarding" options={{headerShown:false}}/>
    <Stack.Screen name="(tabs)" options={{headerShown:false}}/>
    <Stack.Screen name="bill" options={{title:'Add utility bill'}}/>
    <Stack.Screen name="receipt" options={{title:'Receipt review'}}/>
    <Stack.Screen name="activity" options={{title:'Household activity'}}/>
  </Stack>
</AppProvider>;}

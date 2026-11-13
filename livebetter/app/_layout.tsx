import React from 'react';
import {Stack} from 'expo-router';
import {StatusBar} from 'expo-status-bar';
import {AppProvider} from '../src/context';
import {C} from '../src/theme';
export default function RootLayout(){return <AppProvider><StatusBar style="dark"/>
  <Stack screenOptions={{headerShown:false,contentStyle:{backgroundColor:C.bg},animation:'slide_from_right'}}>
    <Stack.Screen name="index" options={{headerShown:false}}/>
    <Stack.Screen name="welcome" options={{headerShown:false}}/>
    <Stack.Screen name="login" options={{headerShown:false}}/>
    <Stack.Screen name="onboarding" options={{headerShown:false}}/>
  </Stack>
</AppProvider>;}

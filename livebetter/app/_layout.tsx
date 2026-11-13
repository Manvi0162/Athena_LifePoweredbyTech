import '../src/web-alert';
import React from 'react';
import {Stack} from 'expo-router';
import {StatusBar} from 'expo-status-bar';
import {AppProvider,useApp} from '../src/context';
import {C} from '../src/theme';
// Re-mount the screens when the language changes so every text is shown in the new language.
function Screens({children}:{children:React.ReactNode}){const {lang}=useApp();return <React.Fragment key={lang}>{children}</React.Fragment>;}
export default function RootLayout(){return <AppProvider><StatusBar style="dark"/>
  <Screens><Stack screenOptions={{headerShown:false,contentStyle:{backgroundColor:C.bg},animation:'slide_from_right'}}>
    <Stack.Screen name="index" options={{headerShown:false}}/>
    <Stack.Screen name="welcome" options={{headerShown:false}}/>
    <Stack.Screen name="login" options={{headerShown:false}}/>
    <Stack.Screen name="register" options={{headerShown:false}}/>
    <Stack.Screen name="security" options={{headerShown:false}}/>
    <Stack.Screen name="onboarding" options={{headerShown:false}}/>
  </Stack></Screens>
</AppProvider>;}

import React from 'react';
import {Redirect} from 'expo-router';
import {useApp} from '../src/context';
// Signed in with a household -> Home; signed in without one -> onboarding; otherwise Welcome.
export default function Index(){
  const {signedIn,state,demo}=useApp();
  if(demo)return <Redirect href="/welcome"/>;
  if(signedIn)return <Redirect href={state.household?'/(tabs)/home':'/onboarding'}/>;
  return <Redirect href="/welcome"/>;
}

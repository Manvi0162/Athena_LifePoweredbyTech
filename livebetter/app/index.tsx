import React from 'react';
import {Redirect} from 'expo-router';
import {View} from 'react-native';
import {Loading} from '../src/ui';
import {useApp} from '../src/context';
export default function Index(){const {ready,state}=useApp();if(!ready)return <View style={{flex:1,justifyContent:'center'}}><Loading/></View>;
  return <Redirect href={state.household?'/(tabs)/home':'/welcome'}/>;}

import React from 'react';
import {Stack} from 'expo-router';
import {C} from '../../src/theme';

export default function AppPagesLayout(){return <Stack screenOptions={{
  headerShown:false,contentStyle:{backgroundColor:C.bg},animation:'slide_from_right',
}}/>;}

import React from 'react';
import {Text} from 'react-native';
import {useApp} from '../../src/context';
import {Card,Label,Note,Page} from '../../src/ui';
import {S} from '../../src/theme';
export default function Activity(){const {state}=useApp();return <Page back title="Household activity" subtitle="Bills, receipts and pantry updates.">
  {state.activity.length?state.activity.map(item=><Card key={item.id}><Label>{item.kind.toUpperCase()}</Label>
    <Text style={S.body}>{item.message}</Text><Note>{new Date(item.at).toLocaleString()}</Note></Card>):
    <Card><Note>No activity yet.</Note></Card>}
  <Note>Demo events are local. A production activity log must be read from the backend.</Note>
</Page>;}

import React,{useEffect,useState} from 'react';
import {Pressable,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {Recipe} from '../../src/types';
import {money,S,C} from '../../src/theme';
import {Card,Label,Loading,Note,Page} from '../../src/ui';

// Same pattern as Utilities: one card per feature, "View details" opens it.
export default function Pantry(){
  const {state,recipes,demo,refreshPantry,insights}=useApp();
  const [list,setList]=useState<Recipe[]|null>(null);
  const [spent,setSpent]=useState<number|null>(null);
  const available=state.pantry.filter(item=>item.available&&item.quantity>0);
  useEffect(()=>{if(!demo)refreshPantry().catch(()=>undefined);},[demo,refreshPantry]);
  useEffect(()=>{
    let active=true;
    recipes().then(v=>{if(active)setList(v);}).catch(()=>{if(active)setList([]);});
    insights().then(v=>{if(active)setSpent(v.groceries_recorded);}).catch(()=>undefined);
    return()=>{active=false;};
  },[recipes,insights,state]);
  const ready=(list||[]).filter(r=>r.cook_now);

  return <Page title="Your smart pantry" subtitle="What you have, what you can cook, and what to do with it." showSettings>
    <Pressable accessibilityRole="button" onPress={()=>router.push('/stock')}
      style={{padding:16,borderRadius:18,backgroundColor:C.softGreen,gap:8}}>
      <View style={S.between}><Text style={S.title}>▤  Groceries and stock</Text>
        <Text style={[S.muted,{color:C.green,fontWeight:'700'}]}>VIEW DETAILS  ›</Text></View>
      <Text style={[S.amount,{color:C.ink,fontSize:23}]}>{available.length} item{available.length===1?'':'s'} available</Text>
      <Note>{spent!=null?`${money(spent)} of groceries confirmed this month · `:''}scan a receipt to add what you bought</Note>
    </Pressable>

    <Pressable accessibilityRole="button" onPress={()=>router.push('/cook-now')}
      style={{padding:16,borderRadius:18,backgroundColor:C.softAmber,gap:8}}>
      <View style={S.between}><Text style={S.title}>📷  Cook with something now</Text>
        <Text style={[S.muted,{color:C.green,fontWeight:'700'}]}>VIEW DETAILS  ›</Text></View>
      <Text style={[S.amount,{color:C.ink,fontSize:20}]}>Scan an ingredient</Text>
      <Note>We tell you what it is, find recipes that use it, or create one with AI.</Note>
    </Pressable>

    <Card>
      <View style={S.between}><Label>Recipes you can cook now</Label><Text style={S.muted}>{ready.length} ready</Text></View>
      {list===null?<Loading/>:(ready.length?ready:(list||[]).slice(0,4)).slice(0,6).map(recipe=><Pressable key={recipe.id}
        accessibilityRole="button" onPress={()=>router.push({pathname:'/recipe/[id]',params:{id:recipe.id}})}
        style={{paddingVertical:11,borderTopWidth:1,borderTopColor:C.line}}>
        <View style={S.between}><Text style={[S.title,{flex:1}]}>{recipe.name}</Text><Text style={{color:C.green,fontSize:19}}>›</Text></View>
        <Note>{recipe.ai_generated?'AI-generated · ':''}{Math.round(recipe.coverage*100)}% in your pantry{recipe.missing.length?` · missing ${recipe.missing.slice(0,3).join(', ')}`:' · ready to cook'}</Note>
      </Pressable>)}
      {list&&!list.length?<Note>No recipes yet. Scan a receipt or an ingredient to get suggestions.</Note>:null}
      <Pressable accessibilityRole="button" onPress={()=>router.push('/my-recipes')} style={{paddingTop:10,borderTopWidth:1,borderTopColor:C.line}}>
        <Text style={{color:C.green,fontWeight:'800'}}>📖 View my recipes and all recipes  ›</Text></Pressable>
    </Card>
  </Page>;
}

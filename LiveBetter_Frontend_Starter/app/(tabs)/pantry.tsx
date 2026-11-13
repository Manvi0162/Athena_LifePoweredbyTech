import React,{useEffect,useState} from 'react';
import {Alert,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {PantryItem,Recipe} from '../../src/types';
import {S,C} from '../../src/theme';
import {Btn,Card,Field,Label,Loading,Note,Page} from '../../src/ui';
export default function Pantry(){const {state,addItem,recipes,cook,demo,refreshPantry}=useApp();
  const [list,setList]=useState<Recipe[]>([]),[loading,setLoading]=useState(true),[editing,setEditing]=useState<string|null>(null);
  const [name,setName]=useState(''),[qty,setQty]=useState('1'),[unit,setUnit]=useState('piece'),[expiry,setExpiry]=useState('');
  useEffect(()=>{let active=true;setLoading(true);recipes().then(v=>{if(active)setList(v);})
    .catch(()=>{}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[state]);
  useEffect(()=>{if(!demo)refreshPantry().catch(()=>{});},[]);
  function edit(p:PantryItem){setEditing(p.id);setName(p.name);setQty(String(p.quantity));setUnit(p.unit);setExpiry(p.expiry||'');}
  function clear(){setEditing(null);setName('');setQty('1');setUnit('piece');setExpiry('');}
  async function save(){const n=Number(qty);if(!name.trim()||!unit.trim()||!Number.isFinite(n)||n<0||
    (expiry&&!/^\d{4}-\d{2}-\d{2}$/.test(expiry)))return Alert.alert('Check item','Valid name, unit, non-negative quantity and optional YYYY-MM-DD expiry are required.');
    try{await addItem({id:editing||undefined,name:name.trim(),quantity:n,unit:unit.trim(),expiry:expiry||undefined,available:n>0});clear();}
    catch(e){Alert.alert('Inventory save failed',String(e));}}
  async function toggle(item:PantryItem){try{await addItem({...item,available:!item.available});}
    catch(e){Alert.alert('Could not update',String(e));}}
  function confirmCook(recipe:Recipe){if(recipe.missing.length)return Alert.alert('Missing ingredients','Add or correct the required inventory first.');
    Alert.alert('Confirm cooking',`Deduct ingredients for ${recipe.name}? This does not create a new expense.`,[
      {text:'Cancel',style:'cancel'},
      {text:'Cooked',onPress:async()=>{try{await cook(recipe.id,`cook-${Date.now()}-${Math.random()}`);}
        catch(e){Alert.alert('Cooking failed',String(e));}}}
    ]);
  }
  return <Page title="Smart pantry" subtitle="Your actual inventory is the basis for recipe suggestions.">
    <Btn title="📷 Import groceries / receipt" onPress={()=>router.push('/receipt')}/>
    <Card><Label>Available ingredients ({state.pantry.filter(x=>x.available&&x.quantity>0).length})</Label>
      {!state.pantry.length?<Note>No stock yet. Add items manually or confirm a receipt.</Note>:null}
      {state.pantry.map(item=><View key={item.id} style={{gap:5,paddingBottom:10,borderBottomColor:C.line,borderBottomWidth:1}}>
        <View style={S.between}><Text style={S.title}>{item.name}</Text><Text style={S.body}>{item.quantity} {item.unit}</Text></View>
        <Note>{item.available?'Available':'Marked unavailable'}{item.expiry?` · Expiry ${item.expiry}`:''}</Note>
        <Btn title="Edit quantity / expiry" outline onPress={()=>edit(item)}/>
        <Btn title={item.available?'Mark unavailable':'Mark available'} outline onPress={()=>toggle(item)}/>
      </View>)}
    </Card>
    <Card><Label>{editing?'Edit ingredient':'Add an ingredient'}</Label>
      <Field label="Ingredient name" value={name} onChangeText={setName}/>
      <Field label="Quantity" value={qty} onChangeText={setQty} keyboardType="decimal-pad"/>
      <Field label="Unit (kg, piece, L...)" value={unit} onChangeText={setUnit}/>
      <Field label="Expiry date (optional YYYY-MM-DD)" value={expiry} onChangeText={setExpiry}/>
      <Btn title={editing?'Save change':'Add ingredient'} onPress={save}/>
      {editing?<Btn title="Cancel editing" outline onPress={clear}/>:null}
    </Card>
    <Card><Label>Recipes ranked by ingredient coverage</Label>
      {demo?<Note>DEMO RECIPE SAMPLES: Not the required authentic UniTools recipe dataset. Member 4 must connect the real dataset-powered endpoint.</Note>:null}
      {loading?<Loading/>:list.length?list.map(recipe=><View key={recipe.id} style={{gap:6,paddingBottom:14,borderBottomWidth:1,borderBottomColor:C.line}}>
        <Text style={S.title}>{recipe.name} · {Math.round(recipe.coverage*100)}% covered</Text>
        <Note>Requires: {recipe.ingredients.map(i=>`${i.quantity} ${i.unit} ${i.name}`).join(', ')}</Note>
        <Note>{recipe.missing.length?`Missing: ${recipe.missing.join(', ')}`:'All listed ingredients available'}</Note>
        <Note>{recipe.instructions}</Note><Note>Source: {recipe.source}</Note>
        <Btn title={recipe.missing.length?'Missing ingredients':'✓ I cooked this — deduct stock'} disabled={!!recipe.missing.length} onPress={()=>confirmCook(recipe)}/>
      </View>):<Note>No recipes returned. Check backend availability or add inventory.</Note>}
    </Card>
  </Page>;
}

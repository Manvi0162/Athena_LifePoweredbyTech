import React,{useEffect,useState} from 'react';
import {Alert,Pressable,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {PantryItem,Recipe} from '../../src/types';
import {S,C} from '../../src/theme';
import {ActionRow,Btn,Card,Field,Label,Loading,Note,Page} from '../../src/ui';

export default function Pantry(){
  const {state,addItem,recipes,demo,refreshPantry}=useApp();
  const [list,setList]=useState<Recipe[]|null>(null);
  const [editing,setEditing]=useState<string|null>(null);
  const [formOpen,setFormOpen]=useState(false);
  const [search,setSearch]=useState('');
  const [name,setName]=useState('');
  const [qty,setQty]=useState('1');
  const [unit,setUnit]=useState('piece');
  const [expiry,setExpiry]=useState('');
  const available=state.pantry.filter(item=>item.available&&item.quantity>0);
  const filteredRecipes=(list||[]).filter(recipe=>recipe.name.toLowerCase().includes(search.trim().toLowerCase()));

  useEffect(()=>{
    let active=true;
    recipes().then(value=>{if(active)setList(value);})
      .catch(error=>{if(active){setList([]);Alert.alert('Recipes unavailable',String(error));}});
    return()=>{active=false;};
  },[recipes,state]);

  useEffect(()=>{if(!demo)refreshPantry().catch(error=>Alert.alert('Pantry unavailable',String(error)));},[demo,refreshPantry]);

  function edit(item:PantryItem){
    setEditing(item.id);setName(item.name);setQty(String(item.quantity));setUnit(item.unit);
    setExpiry(item.expiry||'');setFormOpen(true);
  }
  function clear(){
    setEditing(null);setName('');setQty('1');setUnit('piece');setExpiry('');setFormOpen(false);
  }
  async function save(){
    const quantity=Number(qty);
    if(!name.trim()||!unit.trim()||!Number.isFinite(quantity)||quantity<0||
      (expiry&&!/^\d{4}-\d{2}-\d{2}$/.test(expiry)))
      return Alert.alert('Check item','Enter a name, unit, non-negative quantity and optional YYYY-MM-DD expiry.');
    try{
      await addItem({id:editing||undefined,name:name.trim(),quantity,unit:unit.trim(),
        expiry:expiry||undefined,available:quantity>0});
      clear();
    }catch(error){Alert.alert('Inventory save failed',String(error));}
  }
  async function toggle(item:PantryItem){
    try{await addItem({...item,available:!item.available});}
    catch(error){Alert.alert('Could not update item',String(error));}
  }

  return <Page title="Your smart pantry" subtitle="Know what is in your kitchen and use it well." showSettings>
    <View style={[S.card,{backgroundColor:C.softGreen,borderColor:C.softGreen}]}>
      <View style={S.between}>
        <View><Text style={S.statLabel}>AVAILABLE INGREDIENTS</Text><Text style={[S.amount,{fontSize:27}]}>{available.length} items</Text></View>
        <Text style={{fontSize:28}}>▤</Text>
      </View>
      <Note>Use what you already have before your next shop.</Note>
    </View>

    <Card>
      <Label>Your ingredients</Label>
      <View style={S.row}>
        <View style={{flex:1}}><Btn title="Scan receipt" onPress={()=>router.push('/receipt')}/></View>
        <View style={{flex:1}}><Btn title="+ Add item" outline onPress={()=>{setFormOpen(true);setEditing(null);}}/></View>
      </View>
      {state.pantry.length?state.pantry.map(item=><View key={item.id} style={{paddingVertical:10,borderBottomWidth:1,borderBottomColor:C.line,gap:7}}>
        <View style={S.between}>
          <View style={{flex:1,gap:2}}>
            <Text style={S.title}>{capitalize(item.name)}</Text>
            <Note>{item.quantity} {item.unit}{item.expiry?` · Expires ${item.expiry}`:''}</Note>
          </View>
          <Text style={[S.muted,{color:item.available&&item.quantity>0?C.green:C.muted,fontWeight:'700'}]}>
            {item.available&&item.quantity>0?'AVAILABLE':'UNAVAILABLE'}
          </Text>
        </View>
        <View style={S.row}>
          <Pressable accessibilityRole="button" onPress={()=>edit(item)} style={{paddingVertical:6,paddingRight:12}}>
            <Text style={{color:C.green,fontWeight:'700'}}>Edit</Text>
          </Pressable>
          <Pressable accessibilityRole="button" onPress={()=>void toggle(item)} style={{paddingVertical:6,paddingHorizontal:8}}>
            <Text style={S.muted}>{item.available?'Mark unavailable':'Restore item'}</Text>
          </Pressable>
        </View>
      </View>):<Note>Your pantry is empty. Add an item or confirm a grocery receipt.</Note>}
    </Card>

    {formOpen?<Card>
      <Label>{editing?'Update ingredient':'Add an ingredient'}</Label>
      <Field label="Ingredient name" value={name} onChangeText={setName}/>
      <View style={S.row}>
        <View style={{flex:1}}><Field label="Quantity" value={qty} onChangeText={setQty} keyboardType="decimal-pad"/></View>
        <View style={{flex:1}}><Field label="Unit" value={unit} onChangeText={setUnit} placeholder="kg, piece, L"/></View>
      </View>
      <Field label="Expiry date (optional · YYYY-MM-DD)" value={expiry} onChangeText={setExpiry}/>
      <Btn title={editing?'Save changes':'Add to pantry'} onPress={()=>void save()}/>
      <Btn title="Cancel" outline onPress={clear}/>
    </Card>:null}

    <Card>
      <View style={S.between}><Label>Find recipes from your pantry</Label><Text style={S.muted}>{filteredRecipes.length} recipes</Text></View>
      <Field label="Search recipes" value={search} onChangeText={setSearch} placeholder="Search recipe names"/>
      {list===null?<Loading/>:filteredRecipes.length?filteredRecipes.map(recipe=><Pressable key={recipe.id}
        accessibilityRole="button" onPress={()=>router.push({pathname:'/recipe/[id]',params:{id:recipe.id}})}
        style={{paddingVertical:12,borderBottomWidth:1,borderBottomColor:C.line}}>
        <View style={S.between}>
          <Text style={[S.title,{flex:1}]}>{recipe.name}</Text>
          <Text style={{color:C.green,fontSize:19}}>›</Text>
        </View>
        <Note>{Math.round(recipe.coverage*100)}% available · {recipe.missing.length?`Missing ${recipe.missing.join(', ')}`:'Ready to cook'}</Note>
      </Pressable>):<Note>No matching recipes. Try another search or add more pantry ingredients.</Note>}
    </Card>

    <Card>
      <ActionRow icon="◷" title="Household activity" subtitle="See pantry and grocery updates"
        onPress={()=>router.push('/activity')}/>
    </Card>
  </Page>;
}

function capitalize(value:string){return value.charAt(0).toUpperCase()+value.slice(1);}

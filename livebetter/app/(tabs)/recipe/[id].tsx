import React,{useEffect,useState} from 'react';
import {ActivityIndicator,Alert,Text,View} from 'react-native';
import {router,useLocalSearchParams} from 'expo-router';
import {useApp} from '../../../src/context';
import {Recipe} from '../../../src/types';
import {S,C} from '../../../src/theme';
import {Btn,Card,Label,Note,Page} from '../../../src/ui';

export default function RecipeDetail(){
  const {id}=useLocalSearchParams<{id:string}>();
  const {recipes,cook}=useApp();
  const [recipe,setRecipe]=useState<Recipe|null>(null);
  const [loading,setLoading]=useState(true);
  const [confirming,setConfirming]=useState(false);

  useEffect(()=>{
    let active=true;
    recipes().then(list=>{
      if(active)setRecipe(list.find(item=>item.id===id)||null);
    }).catch(error=>{
      if(active)Alert.alert('Recipe unavailable',String(error));
    }).finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[id,recipes]);

  function confirm(){
    if(!recipe)return;
    if(recipe.missing.length)return Alert.alert('Missing ingredients',`Add or correct: ${recipe.missing.join(', ')}`);
    setConfirming(true);
  }
  async function saveCooking(){
    if(!recipe)return;
    try{
      await cook(recipe.id,`cook-${Date.now()}-${Math.random()}`);
      router.replace('/pantry-updated');
    }catch(error){Alert.alert('Could not update pantry',String(error));}
  }

  return <Page back title={recipe?.name||'Recipe details'} subtitle="A recipe from the ingredients you have available.">
    {loading?<ActivityIndicator color={C.green}/>:recipe?<>
      <View style={[S.heroCard,{backgroundColor:'#A8904F',alignItems:'center',paddingVertical:28}]}>
        <Text style={{fontSize:42}}>🍲</Text>
        <Text style={S.heroEyebrow}>{Math.round(recipe.coverage*100)}% INGREDIENTS AVAILABLE</Text>
        <Text style={S.heroFootnote}>{recipe.missing.length?`Missing: ${recipe.missing.join(', ')}`:'Ready to cook with your pantry.'}</Text>
      </View>
      <Card>
        <View style={S.between}><Label>Ingredients needed</Label><Note>Pantry checked</Note></View>
        {recipe.ingredients.map(item=>{
          const missing=recipe.missing.some(value=>value.startsWith(item.name));
          return <View key={`${item.name}-${item.unit}`} style={S.between}>
            <Text style={S.body}>{item.name}</Text>
            <Text style={[S.title,{color:missing?C.muted:C.green}]}>{item.quantity} {item.unit}</Text>
          </View>;
        })}
      </Card>
      <Card>
        <Label>How to make it</Label>
        <Text style={S.body}>{recipe.instructions}</Text>
        <Note>Source: {recipe.source}</Note>
      </Card>
      <Card>
        <Note>Cooking reduces inventory only. It does not create a grocery expense.</Note>
        {confirming?<View style={{gap:9,backgroundColor:C.softGreen,borderRadius:14,padding:13}}>
          <Label>Confirm the meal</Label>
          <Note>Deduct these ingredients from your pantry? This does not add a new grocery expense.</Note>
          <Btn title="Confirm and update pantry  →" onPress={()=>void saveCooking()}/>
          <Btn title="Cancel" outline onPress={()=>setConfirming(false)}/>
        </View>:<Btn title={recipe.missing.length?'Add missing ingredients first':'I cooked this meal  ✓'}
          disabled={recipe.missing.length>0} onPress={confirm}/>}
        <Btn title="Cancel" outline onPress={()=>router.back()}/>
      </Card>
    </>:<Card><Label>Recipe not found</Label><Note>It may have changed or is no longer available.</Note>
      <Btn title="Back to pantry" onPress={()=>router.replace('/(tabs)/pantry')}/></Card>}
  </Page>;
}

import React,{useEffect,useState} from 'react';
import {t} from '../../../src/i18n';
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
      if(active)Alert.alert(t('Recipe unavailable'),String(error));
    }).finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[id,recipes]);

  function confirm(){if(recipe)setConfirming(true);}
  async function saveCooking(){
    if(!recipe)return;
    try{
      await cook(recipe.id,'new');
      router.replace('/pantry-updated');
    }catch(error){Alert.alert(t('Could not update pantry'),String(error));}
  }

  return <Page back title={recipe?.name||'Recipe details'} subtitle={t('A recipe from the ingredients you have available.')}>
    {loading?<ActivityIndicator color={C.green}/>:recipe?<>
      {recipe.ai_generated?<View style={{backgroundColor:C.amber,borderRadius:12,padding:11}}>
        <Text style={[S.title,{color:'#8A5A00'}]}>{t('⚠ AI-generated recipe')}</Text>
        <Text style={[S.muted,{color:'#8A5A00'}]}>{t('Not checked by a cook. Check ingredients, allergies and cooking times.')}</Text>
      </View>:null}
      <View style={[S.heroCard,{backgroundColor:'#A8904F',alignItems:'center',paddingVertical:28}]}>
        <Text style={{fontSize:42}}>🍲</Text>
        <Text style={S.heroEyebrow}>{Math.round(recipe.coverage*100)}% INGREDIENTS AVAILABLE</Text>
        <Text style={S.heroFootnote}>{recipe.missing.length?`Missing: ${recipe.missing.join(', ')}`:t('Ready to cook with your pantry.')}</Text>
      </View>
      <Card>
        <View style={S.between}><Label>{t('Ingredients needed')}</Label><Note>{t('Pantry checked')}</Note></View>
        {recipe.ingredients.map(item=>{
          const missing=recipe.missing.some(value=>value.startsWith(item.name));
          return <View key={`${item.name}-${item.unit}`} style={S.between}>
            <Text style={S.body}>{item.name}</Text>
            <Text style={[S.title,{color:missing?C.muted:C.green}]}>{item.quantity} {item.unit}</Text>
          </View>;
        })}
      </Card>
      <Card>
        <Label>{t('How to make it')}</Label>
        {recipe.steps&&recipe.steps.length>1?recipe.steps.map((t,k)=><Text key={k} style={S.body}>{k+1}. {t}</Text>):
          <Text style={S.body}>{recipe.instructions}</Text>}
        <Note>Source: {recipe.source}</Note>
      </Card>
      <Card>
        <Note>{t('Cooking reduces inventory only. It does not create a grocery expense.')}</Note>
        {confirming?<View style={{gap:9,backgroundColor:C.softGreen,borderRadius:14,padding:13}}>
          <Label>{t('Confirm the meal')}</Label>
          <Note>{t('Deduct these ingredients from your pantry? This does not add a new grocery expense.')}</Note>
          {recipe.missing.length?<Note>Not in your pantry, so nothing is deducted for: {recipe.missing.join(', ')}.</Note>:null}
          <Btn title={t('Confirm and update pantry  →')} onPress={()=>void saveCooking()}/>
          <Btn title={t('Cancel')} outline onPress={()=>setConfirming(false)}/>
        </View>:<Btn title={t('I cooked this meal  ✓')} onPress={confirm}/>}
        <Btn title={t('Cancel')} outline onPress={()=>router.back()}/>
      </Card>
    </>:<Card><Label>{t('Recipe not found')}</Label><Note>{t('It may have changed or is no longer available.')}</Note>
      <Btn title={t('Back to pantry')} onPress={()=>router.replace('/(tabs)/pantry')}/></Card>}
  </Page>;
}

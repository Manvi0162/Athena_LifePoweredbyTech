// My recipes: the recipes this household saved (AI-generated ones are private to the household) and every recipe
// in the database. Opening one shows the steps and "I cooked this meal" (stock goes down).
import React,{useEffect,useState} from 'react';
import {t} from '../../src/i18n';
import {Pressable,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {Recipe} from '../../src/types';
import {C,S} from '../../src/theme';
import {Card,ChoiceChips,Field,Loading,Note,Page} from '../../src/ui';

export default function MyRecipes(){
  const {recipes,state}=useApp();
  const [list,setList]=useState<Recipe[]|null>(null);
  const [tab,setTab]=useState(t('Saved by me'));
  const [q,setQ]=useState('');
  useEffect(()=>{let a=true;recipes().then(v=>{if(a)setList(v);}).catch(()=>{if(a)setList([]);});return()=>{a=false;};},[recipes,state]);
  const shown=(list||[]).filter(r=>(tab===t('Saved by me')?r.ai_generated:true)&&r.name.toLowerCase().includes(q.trim().toLowerCase()));
  return <Page back title={t('My recipes')} subtitle={t('Recipes you saved and every recipe in the database.')}>
    <ChoiceChips label={t('Show')} options={[t('Saved by me'),t('All recipes')]} value={tab} onChange={setTab}/>
    <Field label={t('Search')} value={q} onChangeText={setQ} placeholder={t('Recipe name')}/>
    <Card>
      {list===null?<Loading/>:shown.length?shown.map((r,i)=><Pressable key={r.id} accessibilityRole="button"
        onPress={()=>router.push({pathname:'/recipe/[id]',params:{id:r.id}})}
        style={{paddingVertical:11,borderTopWidth:i?1:0,borderTopColor:C.line,gap:3}}>
        <View style={S.between}><Text style={[S.title,{flex:1}]}>{r.name}</Text><Text style={{color:C.green,fontSize:19}}>›</Text></View>
        <View style={S.row}>
          {r.ai_generated?<View style={[S.tag,{backgroundColor:C.amber}]}><Text style={[S.tagText,{color:'#8A5A00'}]}>{t('AI-GENERATED')}</Text></View>:
            <View style={S.tag}><Text style={S.tagText}>{t('DATABASE')}</Text></View>}
          <Note>{Math.round(r.coverage*100)}% in your pantry{r.cook_now?' · ready to cook':''}</Note>
        </View>
      </Pressable>):<Note>{tab===t('Saved by me')?t('No saved recipes yet. Scan an ingredient in "Cook with something now" and save an AI recipe.'):t('No recipe matches.')}</Note>}
    </Card>
  </Page>;
}

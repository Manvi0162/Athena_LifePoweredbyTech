// Cook with something now: scan an ingredient -> what it is -> recipes in the database that use it
// -> none? AI creates one (clearly labelled) -> save it -> choose a recipe -> confirm cooking -> stock goes down.
// Backend: /food/recognize, /food/describe, /recipes/search, /recipes/generate, /recipes/drafts, /recipes/{id}/cook.
import React,{useState} from 'react';
import {ActivityIndicator,Alert,Image,Pressable,Text,View} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {AIRecipe,RecipeMatch,RecognisedItem} from '../../src/types';
import {C,S} from '../../src/theme';
import {Btn,Card,Field,Label,Note,Page,readError} from '../../src/ui';

export default function CookNow(){
  const app=useApp();
  const [photo,setPhoto]=useState<string|null>(null);
  const [items,setItems]=useState<RecognisedItem[]>([]);
  const [name,setName]=useState('');
  const [about,setAbout]=useState<string|null>(null);
  const [matches,setMatches]=useState<RecipeMatch[]|null>(null);
  const [ai,setAi]=useState<AIRecipe|null>(null);
  const [savedId,setSavedId]=useState<string|null>(null);
  const [step,setStep]=useState<string|null>(null);
  const [msg,setMsg]=useState<{text:string;bad?:boolean}|null>(null);

  function resetAfter(){setMatches(null);setAi(null);setSavedId(null);setMsg(null);}
  async function pick(camera:boolean){
    try{
      if(camera){const p=await ImagePicker.requestCameraPermissionsAsync();if(!p.granted)return Alert.alert('Permission','Allow camera access.');}
      const r=camera?await ImagePicker.launchCameraAsync({mediaTypes:['images'],quality:.6}):
        await ImagePicker.launchImageLibraryAsync({mediaTypes:['images'],quality:.6});
      if(r.canceled)return;
      setPhoto(r.assets[0].uri);setItems([]);setName('');setAbout(null);resetAfter();
      if(app.demo){setMsg({text:'Demo mode: type the ingredient name below.'});return;}
      setStep('Recognising your ingredient…');
      const out=await app.recognizeFood(r.assets[0].uri);
      setItems(out.items);
      if(out.items.length)await choose(out.items[0]);
      else setMsg({text:out.message||'Nothing recognised. Type the ingredient name below.',bad:true});
    }catch(e){setMsg({text:`${readError(e)} Type the ingredient name below instead.`,bad:true});}
    finally{setStep(null);}
  }
  async function choose(item:RecognisedItem){
    setName(item.name);resetAfter();setAbout(null);
    try{setAbout(await app.describeFood(item));}catch{setAbout(null);}
  }
  async function find(){
    if(!name.trim())return setMsg({text:'Scan or type the ingredient first.',bad:true});
    resetAfter();setStep('Searching all recipes…');
    try{setMatches(await app.searchRecipes([name.trim()]));}
    catch(e){setMsg({text:readError(e),bad:true});}
    finally{setStep(null);}
  }
  async function create(){
    setAi(null);setSavedId(null);setStep('AI is writing a recipe…');setMsg(null);
    try{setAi(await app.generateRecipe([name.trim()]));}
    catch(e){setMsg({text:readError(e),bad:true});}
    finally{setStep(null);}
  }
  async function save(){
    if(!ai)return;
    try{const id=await app.saveRecipe(ai.recipe);setSavedId(id);
      setMsg({text:'Saved to your recipes (private, marked AI-generated). You can cook it now.'});}
    catch(e){setMsg({text:readError(e),bad:true});}
  }
  const open=(id:string)=>router.push({pathname:'/recipe/[id]',params:{id}});

  return <Page back title="Cook with something now" subtitle="Scan the ingredient you want to use. We find a recipe for it.">
    <Card>
      <Label>1 · Scan the ingredient</Label>
      <View style={S.row}>
        <View style={{flex:1}}><Btn title="📷 Camera" onPress={()=>void pick(true)}/></View>
        <View style={{flex:1}}><Btn title="Upload photo" outline onPress={()=>void pick(false)}/></View>
      </View>
      {photo?<Image source={{uri:photo}} style={{height:160,borderRadius:12}} resizeMode="contain"/>:null}
      {items.length>1?<View style={S.choiceRow}>{items.map(i=><Pressable key={i.name} accessibilityRole="button" onPress={()=>void choose(i)}
        style={[S.choice,name===i.name&&S.choiceSelected]}><Text style={[S.choiceText,name===i.name&&S.choiceTextSelected]}>
          {i.name} · {Math.round(i.confidence*100)}%</Text></Pressable>)}</View>:null}
      <Field label="Ingredient (correct it if needed)" value={name} onChangeText={v=>{setName(v);setAbout(null);resetAfter();}} placeholder="e.g. tomato"/>
      {about?<View style={{backgroundColor:C.softBlue,borderRadius:12,padding:11,gap:3}}>
        <Text style={S.title}>What it is</Text><Text style={S.body}>{about}</Text>
        {items[0]?.low_confidence?<Note>Not fully sure: please check the name.</Note>:null}
      </View>:null}
      <Btn title="2 · Find recipes with it" onPress={()=>void find()} disabled={!name.trim()}/>
    </Card>

    {step?<View style={S.row}><ActivityIndicator color={C.green}/><Note>{step}</Note></View>:null}
    {msg?<Text style={msg.bad?S.error:[S.card,{color:C.green,fontWeight:'700'}]}>{msg.text}</Text>:null}

    {matches?<Card>
      <Label>Recipes in our database that use {name.trim()}</Label>
      {matches.length?matches.map(m=><Pressable key={m.recipe_id} accessibilityRole="button" onPress={()=>open(m.recipe_id)}
        style={{paddingVertical:10,borderTopWidth:1,borderTopColor:C.line,gap:2}}>
        <View style={S.between}><Text style={[S.title,{flex:1}]}>{m.name}</Text><Text style={{color:C.green,fontSize:19}}>›</Text></View>
        <Note>{m.verification_status==='pending'?'AI-generated · ':''}{m.already_in_pantry.length?`You have: ${m.already_in_pantry.join(', ')}. `:''}
          {m.still_to_buy.length?`Not in your pantry: ${m.still_to_buy.join(', ')}.`:'Everything else is in your pantry.'}</Note>
      </Pressable>):<Note>No recipe in the database uses it yet.</Note>}
      <Btn title={matches.length?'Or create a new recipe with AI':'Create a recipe with AI'} outline={matches.length>0} onPress={()=>void create()}/>
    </Card>:null}

    {ai?<Card>
      <View style={{backgroundColor:C.amber,borderRadius:12,padding:11,gap:3}}>
        <Text style={[S.title,{color:'#8A5A00'}]}>⚠ AI-generated recipe</Text>
        <Text style={[S.muted,{color:'#8A5A00'}]}>{ai.warning}</Text>
      </View>
      <Text style={S.h2}>{ai.recipe.name}</Text>
      {ai.recipe.description?<Text style={S.body}>{ai.recipe.description}</Text>:null}
      <Note>{ai.recipe.servings?`${ai.recipe.servings} servings · `:''}{ai.recipe.prep_minutes!=null?`${ai.recipe.prep_minutes} min prep · `:''}{ai.recipe.cook_minutes!=null?`${ai.recipe.cook_minutes} min cooking`:''}</Note>
      <Text style={S.title}>Ingredients</Text>
      {ai.recipe.ingredients.map((i,k)=><View key={k} style={S.between}>
        <Text style={S.body}>{i.ingredient_name}{i.optional?' (optional)':''}</Text>
        <Text style={[S.title,{color:ai.missing.some(m=>m.startsWith(i.ingredient_name))?C.muted:C.green}]}>{i.quantity??''} {i.unit??''}</Text></View>)}
      {ai.missing.length?<Note>Not in your pantry: {ai.missing.join(', ')}</Note>:null}
      <Text style={S.title}>Steps</Text>
      {ai.recipe.instructions.map((t,k)=><Text key={k} style={S.body}>{k+1}. {t}</Text>)}
      {savedId?<Btn title="Cook this recipe  →" onPress={()=>open(savedId)}/>:<>
        <Btn title="Save to my recipes" onPress={()=>void save()}/>
        <Btn title="Try another recipe" outline onPress={()=>void create()}/>
      </>}
    </Card>:null}
  </Page>;
}

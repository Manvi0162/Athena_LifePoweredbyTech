import React,{useState} from 'react';
import {t} from '../../src/i18n';
import {ActivityIndicator,Alert,Image,Text,View} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import {router,useLocalSearchParams} from 'expo-router';
import {useApp} from '../../src/context';
import {UtilityKind} from '../../src/types';
import {C,S} from '../../src/theme';
import {ActionRow,Btn,Card,ChoiceChips,ErrorBox,Field,Label,Note,Page,readError} from '../../src/ui';
import {ApiError} from '../../src/api';

// One form per utility: opened from Water it is a water bill, from Electricity an electricity bill.
// From Home ("Add a bill") the user first picks which one.
export default function BillEntry(){
  const params=useLocalSearchParams<{kind?:string}>();
  const kind:UtilityKind|null=params.kind==='water'||params.kind==='electricity'?params.kind:null;
  if(!kind)return <Page back title={t('Add a bill')} subtitle={t('Which bill do you want to add?')}>
    <Card>
      <ActionRow icon="◉" title={t('Water bill (CWA)')} subtitle={t('m³ and amount from your water bill')}
        onPress={()=>router.replace({pathname:'/bill',params:{kind:'water'}})}/>
      <ActionRow icon="ϟ" title={t('Electricity bill (CEB)')} subtitle={t('kWh and amount from your electricity bill')}
        onPress={()=>router.replace({pathname:'/bill',params:{kind:'electricity'}})}/>
    </Card>
  </Page>;
  return <BillForm kind={kind}/>;
}

function BillForm({kind}:{kind:UtilityKind}){
  const {addBill,parseBill,demo,clearError}=useApp();
  const [saveError,setSaveError]=useState<{text:string;overlap?:boolean}|null>(null);
  const isWater=kind==='water';
  const [start,setStart]=useState(''),[end,setEnd]=useState('');
  const [units,setUnits]=useState(''),[amount,setAmount]=useState('');
  const [tariff,setTariff]=useState(isWater?'Domestic':'140');
  const [photo,setPhoto]=useState<string|null>(null);
  const [reading,setReading]=useState(false);
  const [note,setNote]=useState<{text:string;bad?:boolean}|null>(null);

  async function take(camera:boolean){
    try{
      if(camera){const p=await ImagePicker.requestCameraPermissionsAsync();if(!p.granted)return Alert.alert(t('Permission'),t('Allow camera access to take a photo.'));}
      const result=camera?await ImagePicker.launchCameraAsync({mediaTypes:['images'],quality:.7}):
        await ImagePicker.launchImageLibraryAsync({mediaTypes:['images'],quality:.7});
      if(result.canceled)return;
      const uri=result.assets[0].uri;setPhoto(uri);
      if(demo){setNote({text:t('Demo mode: type the values from your bill.')});return;}
      setReading(true);setNote(null);
      const r=await parseBill(kind,uri);
      if(r.period_start)setStart(r.period_start);
      if(r.period_end)setEnd(r.period_end);
      if(r.units!=null)setUnits(String(r.units));
      if(r.amount!=null)setAmount(String(r.amount));
      if(!isWater&&r.tariff&&['110','120','140'].includes(r.tariff))setTariff(r.tariff);
      setNote({text:t('Filled in from your photo. Check every value against the bill before saving.')+
        (r.uncertain.length?` Not sure about: ${r.uncertain.join(', ')}.`:'')});
    }catch(e){setNote({text:`${t('We could not read this photo.')} ${readError(e)} ${t('You can type the values from the bill instead.')}`,bad:true});}
    finally{setReading(false);}
  }

  async function save(){
    const u=Number(units.replace(',','.')),a=amount.trim()?Number(amount.replace(',','.')):undefined;
    if(!/^\d{4}-\d{2}-\d{2}$/.test(start)||!/^\d{4}-\d{2}-\d{2}$/.test(end)||start>=end)
      return Alert.alert(t('Check the dates'),t('Use YYYY-MM-DD, and the end date must be after the start date.'));
    if(!units.trim()||!Number.isFinite(u)||u<=0)
      return Alert.alert(t('Consumption missing'),`Enter the ${isWater?'m³':'kWh'} shown on the bill.`);
    if(a!==undefined&&(!Number.isFinite(a)||a<=0))return Alert.alert(t('Check the amount'),t('Enter the bill amount in rupees, or leave it empty.'));
    setSaveError(null);
    try{await addBill({kind,period_start:start,period_end:end,units:u,amount:a as number,tariff});
      router.replace(isWater?'/water':'/electricity');}
    catch(e){clearError();          // shown here, next to the button, instead of a pop-up plus a banner
      setSaveError({text:readError(e),overlap:e instanceof ApiError&&e.code==='overlap'});}
  }

  return <Page back title={isWater?t('Add a water bill'):t('Add an electricity bill')}
    subtitle={isWater?t('From your CWA bill. Upload a photo and we fill the form for you.'):t('From your CEB bill. Upload a photo and we fill the form for you.')}>
    <Card>
      <Label>1 · Bill photo (optional)</Label>
      <View style={S.row}>
        <View style={{flex:1}}><Btn title={t('📷 Camera')} outline onPress={()=>void take(true)}/></View>
        <View style={{flex:1}}><Btn title={t('Upload photo')} outline onPress={()=>void take(false)}/></View>
      </View>
      {photo?<Image source={{uri:photo}} style={{height:170,borderRadius:12}} resizeMode="contain"/>:null}
      {reading?<View style={S.row}><ActivityIndicator color={C.green}/><Note>{t('Reading your bill…')}</Note></View>:null}
      {note?(note.bad?<ErrorBox text={note.text} onClose={()=>setNote(null)}/>:<Text style={[S.muted,{color:C.green,fontWeight:'700'}]}>{note.text}</Text>):null}
    </Card>
    <Card>
      <Label>{t('2 · Check the values')}</Label>
      <Field label={t('Billing period start (YYYY-MM-DD)')} value={start} onChangeText={setStart} placeholder="2026-09-13"/>
      <Field label={t('Billing period end (YYYY-MM-DD)')} value={end} onChangeText={setEnd} placeholder="2026-10-13"/>
      <Field label={isWater?t('Water used (m³)'):t('Electricity used (kWh)')} value={units} onChangeText={setUnits} keyboardType="decimal-pad"/>
      <Field label={t('Bill amount (Rs), optional')} value={amount} onChangeText={setAmount} keyboardType="decimal-pad"/>
      {isWater?null:<ChoiceChips label={t('CEB tariff on the bill')} options={['110','120','140']} value={tariff} onChange={setTariff}/>}
      <Note>Leave the amount empty and it is calculated with the official {isWater?'CWA':'CEB'} tariff. If you enter it, LiveBetter checks it against the tariff.</Note>
      {saveError?<ErrorBox text={saveError.text} onClose={()=>setSaveError(null)}
        action={saveError.overlap?{title:t('See my bills'),onPress:()=>router.push(isWater?'/water':'/electricity')}:undefined}/>:null}
      <Btn title={t('Save confirmed bill')} onPress={()=>void save()}/>
    </Card>
  </Page>;
}

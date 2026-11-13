import React,{useState} from 'react';
import {Alert,Image,Text} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import {router,useLocalSearchParams} from 'expo-router';
import {useApp} from '../../src/context';
import {UtilityKind} from '../../src/types';
import {Btn,Card,ChoiceChips,Field,Note,Page} from '../../src/ui';
export default function BillEntry(){const {addBill}=useApp();const params=useLocalSearchParams<{kind?:string}>();
  const [kind,setKind]=useState<UtilityKind>(params.kind==='electricity'?'electricity':'water');
  const [start,setStart]=useState('2026-10-01'),[end,setEnd]=useState('2026-10-31');
  const [units,setUnits]=useState(''),[amount,setAmount]=useState('');const [tariff,setTariff]=useState('Domestic');
  const [photo,setPhoto]=useState<string|null>(null);
  async function take(camera:boolean){if(camera){const p=await ImagePicker.requestCameraPermissionsAsync();if(!p.granted)return Alert.alert('Permission','Allow camera access to take a photo.');}
    const result=camera?await ImagePicker.launchCameraAsync({mediaTypes:['images'],quality:.7}):
      await ImagePicker.launchImageLibraryAsync({mediaTypes:['images'],quality:.7});
    if(!result.canceled)setPhoto(result.assets[0].uri);
  }
  async function save(){const u=Number(units),a=Number(amount);
    if(!/^\d{4}-\d{2}-\d{2}$/.test(start)||!/^\d{4}-\d{2}-\d{2}$/.test(end)||
       !Number.isFinite(Date.parse(start))||!Number.isFinite(Date.parse(end))||start>end||!Number.isFinite(u)||u<0||!Number.isFinite(a)||a<0)
      return Alert.alert('Invalid bill','Check date range, non-negative units and amount.');
    try{await addBill({kind,period_start:start,period_end:end,units:u,amount:a,tariff});router.replace('/(tabs)/utilities');}
    catch(e){Alert.alert('Save failed',String(e));}
  }
  return <Page back title={kind==='water'?'Add a water bill':'Add an electricity bill'}
    subtitle="Enter the values shown on your bill and confirm before saving.">
    <Card><Text style={{fontWeight:'800'}}>Bill type</Text>
      <ChoiceChips label="Utility" options={['Water','Electricity']} value={kind==='water'?'Water':'Electricity'}
        onChange={value=>setKind(value==='Water'?'water':'electricity')}/>
      <Field label="Billing period start (YYYY-MM-DD)" value={start} onChangeText={setStart}/>
      <Field label="Billing period end (YYYY-MM-DD)" value={end} onChangeText={setEnd}/>
      <Field label={kind==='water'?'Consumption (m³)':'Consumption (kWh)'} value={units} onChangeText={setUnits} keyboardType="decimal-pad"/>
      <Field label="Bill amount (MUR)" value={amount} onChangeText={setAmount} keyboardType="decimal-pad"/>
      <Field label="Tariff category" value={tariff} onChangeText={setTariff}/>
      <Text style={{fontWeight:'800',marginTop:4}}>Optional bill photo</Text>
      <Btn title="Open camera" outline onPress={()=>take(true)}/>
      <Btn title="Choose from gallery" outline onPress={()=>take(false)}/>
      {photo?<Image source={{uri:photo}} style={{height:180,borderRadius:12}} resizeMode="contain"/>:null}
      <Note>Photo preview is local only in this starter. Bill fields are entered manually; no OCR is claimed. Confirm values against the actual bill before saving.</Note>
      <Btn title="Save confirmed bill" onPress={save}/>
    </Card>
  </Page>;
}

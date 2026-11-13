import React,{useState} from 'react';
import {Alert,Image,Text,View} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import {router} from 'expo-router';
import {useApp} from '../../src/context';
import {ReceiptItem} from '../../src/types';
import {money,S} from '../../src/theme';
import {Btn,Card,Field,Note,Page} from '../../src/ui';
export default function Receipt(){const {demo,parseReceipt,confirmReceipt}=useApp();
  const [image,setImage]=useState<string|null>(null);const [items,setItems]=useState<ReceiptItem[]>([]);
  const [receiptId,setReceiptId]=useState<string|undefined>();
  const [message,setMessage]=useState('No items extracted. Add your purchased items below.');
  async function choose(camera:boolean){try{
    if(camera){const permission=await ImagePicker.requestCameraPermissionsAsync();if(!permission.granted)
      return Alert.alert('Permission needed','Camera access is required to photograph a receipt.');}
    const result=camera?await ImagePicker.launchCameraAsync({mediaTypes:['images'],quality:.6}):
      await ImagePicker.launchImageLibraryAsync({mediaTypes:['images'],quality:.6});
    if(result.canceled)return;
    const uri=result.assets[0].uri;setImage(uri);
    if(demo){setMessage('Photo added. Automatic item extraction is unavailable; enter items manually.');return;}
    const parsed=await parseReceipt(uri);
    setItems(parsed.items||[]);setReceiptId(parsed.receipt_id);
    setMessage('OCR suggestions: inspect and correct every item before saving.');
  }catch(e){Alert.alert('Photo/parse problem',String(e));setMessage('Image processing failed. You can still enter items manually.');}}
  const update=(i:number,patch:Partial<ReceiptItem>)=>setItems(old=>old.map((v,j)=>i===j?{...v,...patch}:v));
  async function save(){if(!items.length)return Alert.alert('No items','Add at least one grocery item.');
    if(items.some(x=>!x.name.trim()||!Number.isFinite(x.quantity)||x.quantity<=0||!Number.isFinite(x.price)||x.price<0||!x.unit.trim()))
      return Alert.alert('Check items','Names and units are required. Quantity must be positive and line price cannot be negative.');
    try{await confirmReceipt(items,receiptId);router.replace('/(tabs)/pantry');}
    catch(e){Alert.alert('Could not save receipt',String(e));}}
  return <Page back title="Add your groceries" subtitle="Scan, review and correct each item before you save.">
    <Card><Btn title="📷 Take receipt photo" onPress={()=>choose(true)}/>
      <Btn title="Choose image from gallery" outline onPress={()=>choose(false)}/>
      {image?<Image source={{uri:image}} style={{height:190,borderRadius:10}} resizeMode="contain"/>:null}
      <Note>{message}</Note>
    </Card>
    <Card><Text style={S.h2}>Review purchased items</Text>
      {items.map((item,i)=><View key={i} style={{gap:6,borderBottomWidth:1,borderBottomColor:'#DDE8E3',paddingBottom:12}}>
        <Field label={`Item ${i+1} — name`} value={item.name} onChangeText={v=>update(i,{name:v})}/>
        <Field label="Quantity" value={String(item.quantity)} keyboardType="decimal-pad" onChangeText={v=>update(i,{quantity:Number(v)})}/>
        <Field label="Unit (kg, piece, L, etc.)" value={item.unit} onChangeText={v=>update(i,{unit:v})}/>
        <Field label="Line total (MUR)" value={String(item.price)} keyboardType="decimal-pad" onChangeText={v=>update(i,{price:Number(v)})}/>
        <Btn title="Remove item" outline onPress={()=>setItems(old=>old.filter((_,j)=>j!==i))}/>
      </View>)}
      <Btn title="+ Add item manually" outline onPress={()=>setItems(old=>[...old,{name:'',quantity:1,unit:'piece',price:0}])}/>
      <Text style={S.title}>Confirmed grocery expense: {money(items.reduce((t,i)=>t+i.price,0))}</Text>
      <Note>Confirm once only. Purchasing adds expense and inventory. Cooking later reduces inventory, not expense.</Note>
      <Btn title="Confirm purchase & update pantry" onPress={save}/>
    </Card>
  </Page>;
}

import React,{useState} from 'react';
import {Alert,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../src/context';
import {Btn,Card,Field,Note,Page} from '../src/ui';
export default function Onboarding(){
  const {onboard,state}=useApp();const h=state.household;
  const [name,setName]=useState(h?.name||'Demo household');
  const [members,setMembers]=useState(String(h?.members||4));
  const [type,setType]=useState(h?.home_type||'House');
  const [water,setWater]=useState(h?.water_tariff||'Domestic — confirm tariff class');
  const [electricity,setElectricity]=useState(h?.electricity_tariff||'Domestic — confirm tariff class');
  const [budget,setBudget]=useState(String(h?.monthly_target||15000));
  const [diet,setDiet]=useState(h?.diet||'No preference');const [allergies,setAllergies]=useState(h?.allergies||'');
  const [waterHabit,setWaterHabit]=useState(h?.water_habit||'');const [appliances,setAppliances]=useState(h?.appliance_notes||'');
  async function save(){if(!name.trim()||!Number.isInteger(Number(members))||Number(members)<1||Number(budget)<0)
    return Alert.alert('Check details','Enter a valid household name, members and budget.');
    try{await onboard({name,members:Number(members),home_type:type,water_tariff:water,
      electricity_tariff:electricity,monthly_target:Number(budget),diet,allergies,water_habit:waterHabit,appliance_notes:appliances});
      router.replace('/(tabs)/home');}catch(e){Alert.alert('Could not save',String(e));}
  }
  return <Page title="Welcome to LiveBetter" subtitle="One household, smarter spending and less waste.">
    <Card><Text style={{fontSize:16,fontWeight:'800'}}>Household assessment</Text>
      <Field label="Household name" value={name} onChangeText={setName}/>
      <Field label="Number of members" value={members} onChangeText={setMembers} keyboardType="number-pad"/>
      <Field label="Home type" value={type} onChangeText={setType}/>
      <Field label="Water tariff class" value={water} onChangeText={setWater}/>
      <Field label="Electricity tariff class" value={electricity} onChangeText={setElectricity}/>
      <Field label="Monthly expense target (MUR)" value={budget} onChangeText={setBudget} keyboardType="decimal-pad"/>
      <Field label="Dietary preference" value={diet} onChangeText={setDiet}/>
      <Field label="Allergies — optional" value={allergies} onChangeText={setAllergies}/>
      <Field label="Water habits — optional" value={waterHabit} onChangeText={setWaterHabit}/>
      <Field label="Major appliances and usage — optional" value={appliances} onChangeText={setAppliances}/>
      <Note>Use fictional details for the hackathon demo. Sensitive household data must not enter a public repository.</Note>
      <Btn title={h?'Update assessment':'Start LiveBetter'} onPress={save}/>
    </Card>
  </Page>;
}

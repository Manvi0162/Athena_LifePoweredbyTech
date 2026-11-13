import React,{useState} from 'react';
import {Alert,Text,View} from 'react-native';
import {router} from 'expo-router';
import {useApp} from '../src/context';
import {usePattern} from '../src/pattern';
import {Btn,Card,ChoiceChips,Field,Label,Note,Page,readError} from '../src/ui';
import {C,S} from '../src/theme';

const steps=['Household','Daily life','Priorities','Review'];
const titles=['First, your household','Tell us about daily life','Set your household priorities','Review your answers'];

export default function Onboarding(){
  const {onboard,state,demo}=useApp();
  const h=state.household;
  const guard=usePattern();          // changing an existing household needs the security pattern
  const [step,setStep]=useState(0);
  const [name,setName]=useState(h?.name||'My household');
  const [members,setMembers]=useState(String(h?.members||4));
  const [type,setType]=useState(h?.home_type||'House');
  const [water,setWater]=useState(h?.water_tariff||'Domestic');
  const [electricity,setElectricity]=useState(h?.electricity_tariff||'Domestic');
  const [budget,setBudget]=useState(String(h?.monthly_target||15000));
  const [diet,setDiet]=useState(h?.diet||'No preference');
  const [allergies,setAllergies]=useState(h?.allergies||'');
  const [waterHabit,setWaterHabit]=useState(h?.water_habit||'');
  const [appliances,setAppliances]=useState(h?.appliance_notes||'');

  function next(){
    if(step===0&&(!name.trim()||!Number.isInteger(Number(members))||Number(members)<1))
      return Alert.alert('Check your household','Enter a name and a whole number of household members.');
    if(step<steps.length-1)setStep(step+1);
    else void save();
  }
  async function save(){
    const target=Number(budget);
    if(!Number.isFinite(target)||target<0||!water.trim()||!electricity.trim())
      return Alert.alert('Check your priorities','Enter a valid monthly target and both tariff categories.');
    const send=async(stepUp?:string)=>{
      try{
        await onboard({name:name.trim(),members:Number(members),home_type:type,water_tariff:water,
          electricity_tariff:electricity,monthly_target:target,diet,allergies,water_habit:waterHabit,appliance_notes:appliances},stepUp);
        router.replace('/(tabs)/home');
      }catch(error){Alert.alert('Could not save household',readError(error));}
    };
    if(h&&!demo)guard.ask('edit_household',send); else await send();
  }

  return <Page showTabs={false} back title={titles[step]}
    subtitle="A few quick answers help make your household picture more useful.">
    {guard.prompt}
    <View style={{gap:8}}>
      <View style={S.between}><Text style={S.muted}>STEP {step+1} OF {steps.length}</Text><Text style={S.muted}>{steps[step]}</Text></View>
      <View style={S.progressTrack}><View style={[S.progressFill,{width:`${((step+1)/steps.length)*100}%`}]}/></View>
    </View>

    {step===0?<Card>
      <Label>About your home</Label>
      <Field label="Household name" value={name} onChangeText={setName} placeholder="e.g. Our home"/>
      <Field label="How many people live here?" value={members} onChangeText={setMembers} keyboardType="number-pad"/>
      <ChoiceChips label="What type of home do you live in?" options={['House','Apartment','Shared home','Other']}
        value={type} onChange={setType}/>
      <Note>Only share details you are comfortable storing with the app.</Note>
    </Card>:null}

    {step===1?<Card>
      <Label>Your daily life</Label>
      <Note>These optional details help explain household patterns. You can skip them.</Note>
      <Field label="Water habits" value={waterHabit} onChangeText={setWaterHabit}
        placeholder="e.g. Showers, laundry, garden watering" multiline/>
      <Field label="Major appliances and usage" value={appliances} onChangeText={setAppliances}
        placeholder="e.g. Air conditioner, washing machine" multiline/>
    </Card>:null}

    {step===2?<Card>
      <Label>What matters to your household?</Label>
      <Field label="Monthly expense target (MUR)" value={budget} onChangeText={setBudget} keyboardType="decimal-pad"/>
      <ChoiceChips label="Dietary preference" options={['No preference','Vegetarian','Vegan','Other']}
        value={diet} onChange={setDiet}/>
      <Field label="Allergies or ingredients to avoid (optional)" value={allergies}
        onChangeText={setAllergies} placeholder="Add any ingredients"/>
      <Field label="Water tariff class" value={water} onChangeText={setWater}/>
      <Field label="Electricity tariff class" value={electricity} onChangeText={setElectricity}/>
      <Note>Tariff categories are household notes, not a verified tariff calculation.</Note>
    </Card>:null}

    {step===3?<Card>
      <Label>Your household is ready</Label>
      <Note>Review these details before building your baseline. You can edit them later.</Note>
      <Summary label="Household" value={`${members} people · ${type}`}/>
      <Summary label="Daily life" value={waterHabit||appliances?'Your household habits are saved':'No optional habits added'}/>
      <Summary label="Monthly target" value={`MUR ${Number(budget||0).toLocaleString('en-MU')}`}/>
      <Summary label="Food preference" value={diet}/>
      <Summary label="Water tariff note" value={water}/>
      <Summary label="Electricity tariff note" value={electricity}/>
      <View style={{backgroundColor:C.blue,borderRadius:13,padding:12}}>
        <Note>Forecasts still need real bills. These answers do not measure current utility use or verify tariff rates.</Note>
      </View>
      <Btn title="Edit answers" outline onPress={()=>setStep(0)}/>
    </Card>:null}

    <View style={S.row}>
      {step>0?<View style={{flex:1}}><Btn title="Back" outline onPress={()=>setStep(step-1)}/></View>:null}
      <View style={{flex:1}}><Btn title={step===steps.length-1?'Enter dashboard':'Continue  →'} onPress={next}/></View>
    </View>
  </Page>;
}

function Summary({label,value}:{label:string;value:string}){
  return <View style={{gap:3,paddingVertical:9,borderBottomWidth:1,borderBottomColor:C.line}}>
    <Text style={S.muted}>{label}</Text><Text style={S.body}>{value}</Text>
  </View>;
}
